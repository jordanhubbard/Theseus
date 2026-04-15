#!/usr/bin/env python3
"""
synthesize_spec.py — Clean-room source synthesis for a single behavioral spec.

Given a compiled .zspec.json, uses an LLM to generate source code, builds it,
verifies it against the same behavioral invariants, and annotates the ZSDL
source file with the outcome.

Usage:
    python3 tools/synthesize_spec.py _build/zspecs/zlib.zspec.json
    python3 tools/synthesize_spec.py _build/zspecs/zlib.zspec.json --max-iterations 5
    python3 tools/synthesize_spec.py _build/zspecs/zlib.zspec.json --dry-run
    python3 tools/synthesize_spec.py _build/zspecs/zlib.zspec.json --no-annotate
    python3 tools/synthesize_spec.py _build/zspecs/zlib.zspec.json --json-out result.json

Exit codes:
    0   All invariants passed (synthesis success)
    1   Partial success or some invariants failed
    2   Build error, missing spec, or harness setup failure
    3   LLM not configured or unavailable
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path when run directly.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import theseus.agent as agent_mod
import theseus.config as config_mod
from theseus.synthesis.annotate import SynthesisAnnotator, zsdl_path_for_spec_json
from theseus.synthesis.prompt import PromptBuilder
from theseus.synthesis.runner import SynthesisResult, SynthesisRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthesise a clean-room implementation from a ZSDL behavioral spec.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "spec",
        type=Path,
        help="Path to a compiled .zspec.json file.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        metavar="N",
        help="Maximum LLM synthesis + verify iterations (default: 3).",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "theseus-synthesis",
        metavar="PATH",
        help="Base directory for synthesis artefacts (default: /tmp/theseus-synthesis).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the initial LLM prompt and exit without calling the model.",
    )
    parser.add_argument(
        "--no-annotate",
        action="store_true",
        help="Skip writing the synthesis result back to the .zspec.zsdl source file.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write the SynthesisResult as JSON to this file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream verify_behavior.py output to stdout.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        metavar="SECONDS",
        help="LLM request timeout in seconds (default: 300 for claude, 120 for OpenAI).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to config.yaml (site overrides loaded from config.site.yaml alongside it).",
    )
    args = parser.parse_args(argv)

    # --- Load spec ---
    if not args.spec.exists():
        print(f"error: spec not found: {args.spec}", file=sys.stderr)
        return 2

    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"error: cannot read spec: {exc}", file=sys.stderr)
        return 2

    # --- Load config ---
    cfg = config_mod.load(args.config)
    ai_cfg = cfg.get("ai", {})

    # --- Dry-run mode ---
    if args.dry_run:
        from theseus.synthesis.build import backend_lang_for_spec
        lib_spec = spec.get("library", {})
        backend_lang = backend_lang_for_spec(lib_spec)
        pb = PromptBuilder()
        system_prompt, user_prompt = pb.initial_prompt(spec, backend_lang)
        print("=== SYSTEM PROMPT ===")
        print(system_prompt)
        print()
        print("=== USER PROMPT ===")
        print(user_prompt)
        return 0

    # --- Check LLM availability ---
    if not agent_mod.available(ai_cfg):
        print(
            "error: no LLM provider configured. Install the claude CLI or set "
            "ai.openai_base_url in config.yaml / config.site.yaml.",
            file=sys.stderr,
        )
        return 3

    # --- Run synthesis ---
    canonical_name = spec.get("identity", {}).get("canonical_name", args.spec.stem)
    print(f"Synthesising: {canonical_name}  (max {args.max_iterations} iteration(s))")

    runner = SynthesisRunner(
        ai_cfg,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
        llm_timeout=args.timeout,
    )
    args.work_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = runner.run(spec, args.spec, args.work_dir)
    except Exception as exc:
        print(f"error: synthesis runner failed: {exc}", file=sys.stderr)
        return 2

    # --- Print summary ---
    _print_summary(result)

    # --- Write JSON output ---
    if args.json_out:
        _write_json_out(result, args.json_out)

    # --- Annotate ZSDL source ---
    if not args.no_annotate:
        _annotate(result, args.spec)

    # --- Exit code ---
    if result.status == "success":
        return 0
    if result.status in ("partial", "failed"):
        return 1
    return 2  # build_failed, infeasible, etc.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_summary(result: SynthesisResult) -> None:
    print(f"\nResult: {result.status.upper()}")
    print(f"  Iterations:  {result.iterations}")
    print(f"  Invariants:  {result.final_pass_count} passed / "
          f"{result.final_fail_count} failed / "
          f"{result.total_invariants} total")
    if result.notes:
        print(f"  Notes:       {result.notes}")
    if result.failed_invariant_details:
        print(f"  Failed ({len(result.failed_invariant_details)}):")
        for inv_id, detail in list(result.failed_invariant_details.items())[:10]:
            reason = detail.get("reason", "")[:80]
            print(f"    - {inv_id}: {reason}")
        if len(result.failed_invariant_details) > 10:
            print(f"    ... and {len(result.failed_invariant_details) - 10} more")


def _write_json_out(result: SynthesisResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "canonical_name": result.canonical_name,
        "backend_lang": result.backend_lang,
        "status": result.status,
        "model": result.model,
        "attempted_at": result.attempted_at,
        "iterations": result.iterations,
        "final_pass_count": result.final_pass_count,
        "final_fail_count": result.final_fail_count,
        "total_invariants": result.total_invariants,
        "notes": result.notes,
        "infeasible_reason": result.infeasible_reason,
        "failed_invariant_details": result.failed_invariant_details,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"JSON result written to: {path}")


def _annotate(result: SynthesisResult, spec_json_path: Path) -> None:
    try:
        zsdl_path = zsdl_path_for_spec_json(spec_json_path)
        if not zsdl_path.exists():
            print(
                f"warning: ZSDL source not found at {zsdl_path} — skipping annotation.",
                file=sys.stderr,
            )
            return
        SynthesisAnnotator().annotate(zsdl_path, result, overwrite_existing=True)
        print(f"Annotated: {zsdl_path}")
    except Exception as exc:
        print(f"warning: annotation failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
