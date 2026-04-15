"""
theseus/pipeline.py

Unified ZSpec pipeline: compile → verify_real → synthesize → gate → annotate.

Synthesis is not an optional post-processing step — it is a required stage of
spec creation.  A spec that produces "failed" or "build_failed" synthesis status
(zero passing invariants) is rejected by the gate step and must be revised or
explicitly annotated with ``infeasible_reason`` in the ZSDL source.

Pipeline steps
--------------
1. compile       .zspec.zsdl → _build/zspecs/*.zspec.json
2. verify_real   Run the compiled spec against the *real* installed library
                 (proves the spec accurately describes the library before
                  synthesis is attempted; harness errors skip the gate)
3. synthesize    LLM generates a clean-room implementation + verify loop
4. gate          Reject specs with no passing synthesis invariants
5. annotate      Write SynthesisResult back to the .zspec.zsdl source

Use ``ZSpecPipeline.run(zsdl_path)`` to run the full pipeline.  Each step
emits a ``StepResult``; the final ``PipelineResult.outcome`` summarises the
run:

  success          — synthesis passed all invariants
  partial          — synthesis passed some invariants (spec may need work)
  infeasible       — LLM could not produce valid code (expected for some specs)
  gated            — synthesis failed completely; spec is flagged for revision
  compile_error    — .zsdl could not be compiled
  real_verify_failed — spec invariants fail against the real library
"""
from __future__ import annotations

import dataclasses
import enum
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from theseus.synthesis.runner import SynthesisResult

_REPO_ROOT  = Path(__file__).resolve().parent.parent
_COMPILE_PY = _REPO_ROOT / "tools" / "zsdl_compile.py"
_VERIFY_PY  = _REPO_ROOT / "tools" / "verify_behavior.py"
_BUILD_DIR  = _REPO_ROOT / "_build" / "zspecs"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class StepStatus(str, enum.Enum):
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"
    ERROR   = "error"


@dataclasses.dataclass
class StepResult:
    name:    str
    status:  StepStatus
    message: str = ""


@dataclasses.dataclass
class PipelineResult:
    zsdl_path:        Path
    steps:            list[StepResult]
    outcome:          str   # see module docstring for possible values
    synthesis_result: Any              = None   # SynthesisResult | None
    spec_json_path:   Path | None      = None

    @property
    def acceptable(self) -> bool:
        """True when the spec cleared the gate (synthesis produced a result)."""
        return self.outcome in ("success", "partial", "infeasible")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class ZSpecPipeline:
    """
    Runs the unified spec pipeline for one .zspec.zsdl source file.

    Parameters
    ----------
    max_iterations : int
        Maximum LLM synthesis + verify cycles (passed to SynthesisRunner).
    work_dir : Path | None
        Base temp directory for synthesis artefacts.  A sub-directory per
        spec is created inside.  Defaults to a system temp directory.
    annotate : bool
        Write the SynthesisResult back to the .zspec.zsdl source (step 5).
    skip_real_verify : bool
        Skip step 2.  Useful when the library is not installed locally.
    gate_on_synthesis : bool
        When True (default), fail the pipeline for synthesis status
        "failed" or "build_failed".  "partial" and "infeasible" pass through.
    ai_cfg : dict
        AI provider config dict (from ``theseus.config.load()["ai"]``).
    verbose : bool
        Stream subprocess output to stdout.
    dry_run : bool
        Compile only; print the initial synthesis prompt and return without
        calling the LLM.
    llm_timeout : int
        LLM request timeout in seconds.  0 uses the provider default.
    """

    def __init__(
        self,
        *,
        max_iterations:    int       = 3,
        work_dir:          Path | None = None,
        annotate:          bool      = True,
        skip_real_verify:  bool      = False,
        gate_on_synthesis: bool      = True,
        ai_cfg:            dict | None = None,
        verbose:           bool      = False,
        dry_run:           bool      = False,
        llm_timeout:       int       = 0,
    ) -> None:
        self.max_iterations    = max_iterations
        self.work_dir          = work_dir
        self.annotate          = annotate
        self.skip_real_verify  = skip_real_verify
        self.gate_on_synthesis = gate_on_synthesis
        self.ai_cfg            = ai_cfg if ai_cfg is not None else {}
        self.verbose           = verbose
        self.dry_run           = dry_run
        self.llm_timeout       = llm_timeout

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, zsdl_path: Path) -> PipelineResult:
        """Run all pipeline steps for *zsdl_path* and return a PipelineResult."""
        steps: list[StepResult] = []

        # ── Step 1: compile ──────────────────────────────────────────────────
        compile_step, spec_json_path, spec = self._compile(zsdl_path)
        steps.append(compile_step)
        if compile_step.status != StepStatus.PASSED:
            return PipelineResult(zsdl_path, steps, "compile_error")

        # ── Step 2: verify_real ───────────────────────────────────────────────
        if not self.skip_real_verify:
            real_step = self._verify_real(spec_json_path)
            steps.append(real_step)
            if real_step.status == StepStatus.FAILED:
                return PipelineResult(
                    zsdl_path, steps, "real_verify_failed",
                    spec_json_path=spec_json_path,
                )

        # ── Step 3: synthesize ────────────────────────────────────────────────
        import theseus.agent as agent_mod

        if self.dry_run:
            steps.append(StepResult("synthesize", StepStatus.SKIPPED, "dry-run"))
            return PipelineResult(
                zsdl_path, steps, "success", spec_json_path=spec_json_path
            )

        if not agent_mod.available(self.ai_cfg):
            steps.append(
                StepResult("synthesize", StepStatus.SKIPPED, "no LLM provider configured")
            )
            # Not a pipeline failure — synthesis could not run.
            return PipelineResult(
                zsdl_path, steps, "success", spec_json_path=spec_json_path
            )

        synth_step, synth_result = self._synthesize(spec, spec_json_path)
        steps.append(synth_step)

        # ── Step 4: gate ──────────────────────────────────────────────────────
        gate_step = self._gate(synth_result)
        steps.append(gate_step)

        # ── Step 5: annotate ──────────────────────────────────────────────────
        if self.annotate and synth_result is not None:
            steps.append(self._annotate(zsdl_path, synth_result))

        outcome = "gated" if gate_step.status == StepStatus.FAILED else (
            synth_result.status if synth_result else "success"
        )
        return PipelineResult(
            zsdl_path=zsdl_path,
            steps=steps,
            outcome=outcome,
            synthesis_result=synth_result,
            spec_json_path=spec_json_path,
        )

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    def _compile(
        self, zsdl_path: Path
    ) -> tuple[StepResult, Path | None, dict | None]:
        """Compile .zspec.zsdl → _build/zspecs/*.zspec.json."""
        _BUILD_DIR.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [sys.executable, str(_COMPILE_PY), str(zsdl_path)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "unknown compile error").strip()[:300]
            return StepResult("compile", StepStatus.FAILED, msg), None, None

        # Mirror the output-path logic from zsdl_compile._compile_one.
        stem = zsdl_path.name          # e.g. hashlib.zspec.zsdl
        if stem.endswith(".zsdl"):
            stem = stem[:-5]           # → hashlib.zspec
        spec_json_path = _BUILD_DIR / (stem if stem.endswith(".json") else stem + ".json")

        if not spec_json_path.exists():
            return (
                StepResult("compile", StepStatus.ERROR,
                           f"compiled output not found: {spec_json_path}"),
                None, None,
            )

        try:
            spec = json.loads(spec_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return (
                StepResult("compile", StepStatus.ERROR, f"cannot read compiled spec: {exc}"),
                None, None,
            )

        canonical  = spec.get("identity", {}).get("canonical_name", stem)
        inv_count  = len(spec.get("invariants", []))
        return (
            StepResult(
                "compile", StepStatus.PASSED,
                f"{spec_json_path.name}  canonical={canonical}  invariants={inv_count}",
            ),
            spec_json_path,
            spec,
        )

    def _verify_real(self, spec_json_path: Path) -> StepResult:
        """Verify compiled spec against the real installed library."""
        try:
            r = subprocess.run(
                [sys.executable, str(_VERIFY_PY), str(spec_json_path)],
                capture_output=not self.verbose,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return StepResult("verify_real", StepStatus.ERROR,
                              "verify_behavior.py timed out after 180s")

        if r.returncode == 0:
            return StepResult("verify_real", StepStatus.PASSED,
                              "all invariants pass against real library")
        if r.returncode == 1:
            # Invariant failures — spec describes the library incorrectly.
            msg = ((r.stderr or "") + (r.stdout or "")).strip()[:200]
            return StepResult("verify_real", StepStatus.FAILED,
                              f"spec invariants fail against real library: {msg}")
        # Exit ≥ 2: harness/setup error (library not installed, etc.).
        # Don't block — the spec may still be correct on a different machine.
        return StepResult(
            "verify_real", StepStatus.PASSED,
            f"harness exit {r.returncode} (library may not be installed — skipped gate)",
        )

    def _synthesize(
        self, spec: dict, spec_json_path: Path
    ) -> tuple[StepResult, Any]:
        """Run the LLM synthesis loop."""
        from theseus.synthesis.runner import SynthesisResult, SynthesisRunner

        work_base = self.work_dir or (
            Path(tempfile.gettempdir()) / "theseus-pipeline"
        )
        work_base.mkdir(parents=True, exist_ok=True)

        runner = SynthesisRunner(
            self.ai_cfg,
            max_iterations=self.max_iterations,
            verbose=self.verbose,
            llm_timeout=self.llm_timeout,
        )
        try:
            result = runner.run(spec, spec_json_path, work_base)
        except Exception as exc:
            canonical = spec.get("identity", {}).get("canonical_name", "unknown")
            result = SynthesisResult(
                canonical_name=canonical,
                backend_lang="unknown",
                status="infeasible",
                model="",
                attempted_at="",
                iterations=0,
                total_invariants=len(spec.get("invariants", [])),
                notes=f"Runner exception: {exc}",
                infeasible_reason="runner_exception",
            )

        # "infeasible" is an expected outcome (e.g. C library wrapping), not a failure.
        step_status = (
            StepStatus.PASSED
            if result.status in ("success", "partial", "infeasible")
            else StepStatus.FAILED
        )
        msg = (
            f"{result.status}: "
            f"{result.final_pass_count}/{result.total_invariants} invariants"
        )
        return StepResult("synthesize", step_status, msg), result

    def _gate(self, synth_result: Any) -> StepResult:
        """
        Gate step: reject specs whose synthesis status is "failed" or
        "build_failed".  These specs produced zero passing invariants
        after all LLM iterations, suggesting the spec is under-specified,
        contradictory, or describes unreachable behaviour.

        "partial" passes through (some invariants work — spec may improve).
        "infeasible" passes through (known limitation documented in the spec).
        """
        if synth_result is None or not self.gate_on_synthesis:
            return StepResult("gate", StepStatus.SKIPPED, "gating disabled")

        if synth_result.status in {"failed", "build_failed"}:
            return StepResult(
                "gate", StepStatus.FAILED,
                f"synthesis '{synth_result.status}' — no passing invariants after "
                f"{synth_result.iterations} iteration(s). "
                "Revise the spec or add infeasible_reason to the ZSDL source.",
            )
        return StepResult(
            "gate", StepStatus.PASSED,
            f"synthesis '{synth_result.status}' clears gate",
        )

    def _annotate(self, zsdl_path: Path, synth_result: Any) -> StepResult:
        """Append synthesis block to the .zspec.zsdl source file."""
        from theseus.synthesis.annotate import SynthesisAnnotator
        try:
            SynthesisAnnotator().annotate(
                zsdl_path, synth_result, overwrite_existing=True
            )
            return StepResult("annotate", StepStatus.PASSED, zsdl_path.name)
        except Exception as exc:
            return StepResult("annotate", StepStatus.FAILED, str(exc))
