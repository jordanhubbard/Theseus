"""
theseus/synthesis/runner.py

Orchestrates the full synthesis loop for a single behavioral spec:

  1. Determine synthesis language from spec backend
  2. Build initial LLM prompt → call agent → extract source files
  3. Compile/stage source via SynthesisBuildDriver
  4. Run verify_behavior.py harness (with appropriate env overrides)
  5. If failures remain and iterations < max_iterations, build revision prompt → repeat
  6. Return SynthesisResult with final status and per-invariant details
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import theseus.agent as agent_mod
from theseus.synthesis.build import SynthesisBuildDriver, SynthesisBuildResult, backend_lang_for_spec
from theseus.synthesis.prompt import PromptBuilder

# Path to verify_behavior.py relative to this file's repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_VERIFY_PY = _REPO_ROOT / "tools" / "verify_behavior.py"


@dataclass
class SynthesisAttempt:
    """Record of a single synthesis + build + verify iteration."""

    iteration: int
    source_files: dict[str, str]
    build_result: SynthesisBuildResult
    verify_results: list[dict] = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0


@dataclass
class SynthesisResult:
    """Aggregated outcome of the entire synthesis loop for one spec."""

    canonical_name: str
    backend_lang: str
    # "success" | "partial" | "failed" | "build_failed" | "infeasible"
    status: str
    model: str
    attempted_at: str          # ISO-8601
    iterations: int
    attempts: list[SynthesisAttempt] = field(default_factory=list)
    final_pass_count: int = 0
    final_fail_count: int = 0
    total_invariants: int = 0
    notes: str = ""
    infeasible_reason: str | None = None
    # inv_id → {"status": "failed", "reason": <message>}
    failed_invariant_details: dict = field(default_factory=dict)


class SynthesisRunner:
    """
    Runs the synthesis loop for a single compiled .zspec.json.

    Args:
        cfg: AI config dict (e.g. ``theseus.config.load()["ai"]``).
        max_iterations: maximum number of LLM synthesis + verify cycles.
        verbose: if True, print verify_behavior.py output to stdout.
    """

    def __init__(
        self,
        cfg: dict,
        *,
        max_iterations: int = 3,
        verbose: bool = False,
        llm_timeout: int = 0,
    ) -> None:
        self._cfg = cfg
        self._max_iterations = max_iterations
        self._verbose = verbose
        self._llm_timeout = llm_timeout
        self._prompt_builder = PromptBuilder()
        self._build_driver = SynthesisBuildDriver()

    def run(
        self,
        spec: dict,
        spec_json_path: Path,
        work_base: Path,
    ) -> SynthesisResult:
        """
        Execute the full synthesis loop.

        Args:
            spec: parsed .zspec.json dict.
            spec_json_path: path to the .zspec.json file (for harness invocation).
            work_base: base temp directory; sub-directories will be created here.

        Returns:
            SynthesisResult describing the final outcome.
        """
        canonical_name = spec.get("identity", {}).get("canonical_name", "unknown")
        lib_spec = spec.get("library", {})
        backend_lang = backend_lang_for_spec(lib_spec)
        total_invariants = len(spec.get("invariants", []))
        attempted_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        model = _detect_model(self._cfg)

        attempts: list[SynthesisAttempt] = []
        previous_source: dict[str, str] = {}
        failed_invariants: list[dict] = []
        final_status = "failed"

        for iteration in range(1, self._max_iterations + 1):
            work_dir = work_base / canonical_name / f"attempt_{iteration}"
            work_dir.mkdir(parents=True, exist_ok=True)

            # --- Build prompt ---
            if iteration == 1:
                system_prompt, user_prompt = self._prompt_builder.initial_prompt(
                    spec, backend_lang
                )
            else:
                system_prompt, user_prompt = self._prompt_builder.revision_prompt(
                    spec,
                    backend_lang,
                    previous_source,
                    failed_invariants,
                    iteration,
                )

            # --- Call LLM ---
            try:
                llm_response = agent_mod.run_prompt(
                    user_prompt, self._cfg, system=system_prompt,
                    timeout=self._llm_timeout,
                )
            except RuntimeError as exc:
                return SynthesisResult(
                    canonical_name=canonical_name,
                    backend_lang=backend_lang,
                    status="infeasible",
                    model=model,
                    attempted_at=attempted_at,
                    iterations=iteration,
                    attempts=attempts,
                    total_invariants=total_invariants,
                    notes=f"LLM unavailable: {exc}",
                    infeasible_reason="llm_unavailable",
                )

            # --- Extract source files from response ---
            try:
                source_files = PromptBuilder.extract_source_files(llm_response)
            except ValueError as exc:
                attempt = SynthesisAttempt(
                    iteration=iteration,
                    source_files={},
                    build_result=SynthesisBuildResult(
                        success=False,
                        artifact_path="",
                        backend_lang=backend_lang,
                        build_log=f"LLM response parse error: {exc}",
                        returncode=1,
                        work_dir=str(work_dir),
                    ),
                )
                attempts.append(attempt)
                # Try again on next iteration with the failed response as context
                failed_invariants = [
                    {"id": inv.get("id", "?"), "message": "no source produced"}
                    for inv in spec.get("invariants", [])
                ]
                previous_source = {"(no files produced)": llm_response[:500]}
                continue

            previous_source = source_files

            # --- Build ---
            build_result = self._build_driver.build(
                source_files, backend_lang, canonical_name, work_dir
            )
            attempt = SynthesisAttempt(
                iteration=iteration,
                source_files=source_files,
                build_result=build_result,
            )

            if not build_result.success:
                attempts.append(attempt)
                # Feed build error back as the "failure" for revision
                failed_invariants = [
                    {
                        "id": "(build)",
                        "message": f"Build failed:\n{build_result.build_log}",
                    }
                ]
                final_status = "build_failed"
                continue

            # --- Verify ---
            verify_results = self._invoke_verify_harness(
                spec_json_path, build_result, lib_spec, spec.get("invariants", [])
            )
            pass_count = sum(1 for r in verify_results if r.get("passed") and not r.get("skip_reason"))
            skip_count = sum(1 for r in verify_results if r.get("skip_reason"))
            fail_count = sum(1 for r in verify_results if not r.get("passed") and not r.get("skip_reason"))

            attempt.verify_results = verify_results
            attempt.pass_count = pass_count
            attempt.fail_count = fail_count
            attempt.skip_count = skip_count
            attempts.append(attempt)

            if fail_count == 0 and pass_count > 0:
                final_status = "success"
                break

            # All invariants were skipped — synthesis can't improve further.
            if fail_count == 0 and pass_count == 0:
                final_status = "infeasible"
                break

            # Prepare for revision
            failed_invariants = [
                {"id": r["id"], "message": r.get("message", "")}
                for r in verify_results
                if not r.get("passed") and not r.get("skip_reason")
            ]
            if fail_count < total_invariants:
                final_status = "partial"
            else:
                final_status = "failed"

        # --- Collect final metrics ---
        if attempts:
            last = attempts[-1]
            final_pass = last.pass_count
            final_fail = last.fail_count
            final_details: dict = {}
            for r in last.verify_results:
                if not r.get("passed") and not r.get("skip_reason"):
                    final_details[r["id"]] = {
                        "status": "failed",
                        "reason": r.get("message", ""),
                    }
        else:
            final_pass = 0
            final_fail = 0
            final_details = {}

        notes = _summarise_notes(final_status, attempts)

        return SynthesisResult(
            canonical_name=canonical_name,
            backend_lang=backend_lang,
            status=final_status,
            model=model,
            attempted_at=attempted_at,
            iterations=len(attempts),
            attempts=attempts,
            final_pass_count=final_pass,
            final_fail_count=final_fail,
            total_invariants=total_invariants,
            notes=notes,
            failed_invariant_details=final_details,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _invoke_verify_harness(
        self,
        spec_json_path: Path,
        build_result: SynthesisBuildResult,
        lib_spec: dict,
        invariants: list[dict] | None = None,
    ) -> list[dict]:
        """
        Run verify_behavior.py as a subprocess with synthesised library overrides.

        Returns the parsed list of invariant result dicts from --json-out.
        """
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            json_out_path = Path(tmp.name)

        try:
            cmd = [
                sys.executable,
                str(_VERIFY_PY),
                str(spec_json_path),
                "--json-out",
                str(json_out_path),
            ]

            env = dict(os.environ)
            backend_lang = build_result.backend_lang
            artifact = build_result.artifact_path
            work_dir = build_result.work_dir

            if backend_lang in ("python", "rust"):
                # Prepend staging dir so our synthesised module shadows any installed one.
                # For Rust, artifact_path points to the lib/ dir containing the .so.
                env["PYTHONPATH"] = artifact + os.pathsep + env.get("PYTHONPATH", "")

            elif backend_lang == "c":
                # Point ctypes library search at the work dir.
                cmd += ["--lib-dir", work_dir]
                env["LD_LIBRARY_PATH"] = (
                    work_dir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
                )
                env["DYLD_LIBRARY_PATH"] = (
                    work_dir + os.pathsep + env.get("DYLD_LIBRARY_PATH", "")
                )

            elif backend_lang == "javascript":
                env["NODE_PATH"] = artifact + os.pathsep + env.get("NODE_PATH", "")

            result = subprocess.run(
                cmd,
                capture_output=not self._verbose,
                text=True,
                env=env,
                timeout=180,
            )

            if self._verbose and result.returncode not in (0, 1):
                print(
                    f"[synthesis] verify_behavior exit {result.returncode}",
                    file=sys.stderr,
                )

            if json_out_path.exists() and json_out_path.stat().st_size > 0:
                return json.loads(json_out_path.read_text(encoding="utf-8"))

            # Harness crashed before writing output — treat all as failed.
            stderr = getattr(result, "stderr", "") or ""
            stdout = getattr(result, "stdout", "") or ""
            detail = (stderr or stdout).strip()[:500]
            if not detail:
                detail = "no output"
            invs = invariants or [{"id": "(harness)"}]
            return [
                {
                    "id": inv.get("id", "?"),
                    "passed": False,
                    "message": f"Harness error (exit {result.returncode}): {detail}",
                    "skip_reason": None,
                }
                for inv in invs
            ]

        except subprocess.TimeoutExpired:
            return [
                {
                    "id": "(timeout)",
                    "passed": False,
                    "message": "verify_behavior.py timed out after 180s",
                    "skip_reason": None,
                }
            ]
        finally:
            try:
                json_out_path.unlink(missing_ok=True)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _detect_model(cfg: dict) -> str:
    """Return a best-guess model identifier from the AI config."""
    provider = cfg.get("provider", "auto")
    if provider in ("claude", "auto"):
        import shutil
        if shutil.which("claude"):
            return "claude-cli"
    return cfg.get("openai_model", "unknown")


def _summarise_notes(status: str, attempts: list[SynthesisAttempt]) -> str:
    """Build a short human-readable notes string describing the synthesis outcome."""
    if not attempts:
        return "No synthesis attempts completed."
    last = attempts[-1]
    iters = len(attempts)
    if status == "success":
        return (
            f"Synthesis succeeded in {iters} iteration(s). "
            f"{last.pass_count} invariants passing."
        )
    if status == "build_failed":
        return (
            f"Build failed after {iters} iteration(s). "
            f"Last build log: {last.build_result.build_log[:200]}"
        )
    if status == "partial":
        return (
            f"Partial synthesis after {iters} iteration(s): "
            f"{last.pass_count} passing, {last.fail_count} failing."
        )
    return (
        f"Synthesis failed after {iters} iteration(s). "
        f"{last.fail_count} invariants still failing."
    )
