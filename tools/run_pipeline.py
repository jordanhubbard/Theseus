#!/usr/bin/env python3
"""
run_pipeline.py — Unified ZSpec pipeline: compile → verify_real → synthesize → gate → annotate.

This is the primary tool for spec authoring.  Synthesis is step 3 of the
pipeline, not an optional post-processing task.  A spec that cannot produce
any passing invariants under synthesis is flagged by the gate (step 4) and
must be revised or explicitly annotated with ``infeasible_reason`` in the
ZSDL source.

Pipeline steps
--------------
  1. compile       .zspec.zsdl → _build/zspecs/*.zspec.json
  2. verify_real   Confirm spec accurately describes the real installed library
  3. synthesize    LLM generates a clean-room implementation + verify loop
  4. gate          Reject specs with no passing synthesis invariants
  5. annotate      Write outcome back to the .zspec.zsdl source file

Usage
-----
  python3 tools/run_pipeline.py zspecs/zlib.zspec.zsdl
  python3 tools/run_pipeline.py zspecs/*.zspec.zsdl --jobs 4
  python3 tools/run_pipeline.py --all
  python3 tools/run_pipeline.py zspecs/zlib.zspec.zsdl --dry-run
  python3 tools/run_pipeline.py zspecs/zlib.zspec.zsdl --skip-real-verify
  python3 tools/run_pipeline.py zspecs/zlib.zspec.zsdl --no-gate

Exit codes
----------
  0   All specs acceptable (success / partial / infeasible)
  1   One or more specs failed the gate or had real-library verify failures
  2   Setup error (no specs found, missing tools, bad arguments)
  3   LLM not configured and synthesis was required
"""
from __future__ import annotations

import argparse
import concurrent.futures
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import theseus.agent as agent_mod
import theseus.config as config_mod
from theseus.pipeline import PipelineResult, StepStatus, ZSpecPipeline
from theseus.synthesis.audit import AuditReportGenerator

_ZSPECS_DIR = _REPO_ROOT / "zspecs"
_DEFAULT_AUDIT_OUT = _REPO_ROOT / "reports" / "synthesis" / "pipeline_audit.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ZSpec pipeline: compile → verify_real → synthesize → gate → annotate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "zsdl_files",
        nargs="*",
        type=Path,
        metavar="ZSDL",
        help="One or more .zspec.zsdl source files.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every .zspec.zsdl file in zspecs/.",
    )
    parser.add_argument(
        "--max-iterations", type=int, default=3, metavar="N",
        help="Maximum LLM synthesis + verify iterations per spec (default: 3).",
    )
    parser.add_argument(
        "--work-dir", type=Path, default=None, metavar="PATH",
        help="Base directory for synthesis artefacts (default: system temp).",
    )
    parser.add_argument(
        "--skip-real-verify", action="store_true",
        help="Skip step 2.  Use when the target library is not installed locally.",
    )
    parser.add_argument(
        "--no-gate", action="store_true",
        help="Disable the gate (step 4).  Specs proceed regardless of synthesis outcome.",
    )
    parser.add_argument(
        "--no-annotate", action="store_true",
        help="Skip writing synthesis results back to .zspec.zsdl files.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compile only; print the initial synthesis prompt and exit.",
    )
    parser.add_argument(
        "--jobs", type=int, default=1, metavar="N",
        help="Parallel pipeline workers (default: 1; LLM rate limits apply).",
    )
    parser.add_argument(
        "--timeout", type=int, default=0, metavar="SECONDS",
        help="LLM request timeout in seconds (0 = provider default).",
    )
    parser.add_argument(
        "--out", type=Path, default=None, metavar="PATH",
        help=f"Audit report output path (default: {_DEFAULT_AUDIT_OUT}).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Stream subprocess output to stdout.",
    )
    parser.add_argument(
        "--config", type=Path, default=None, metavar="PATH",
        help="Path to config.yaml (site overrides loaded from config.site.yaml alongside it).",
    )
    args = parser.parse_args(argv)

    # --- Collect .zsdl paths ---
    if args.all:
        if not _ZSPECS_DIR.is_dir():
            print(f"error: zspecs/ directory not found: {_ZSPECS_DIR}", file=sys.stderr)
            return 2
        zsdl_files = sorted(_ZSPECS_DIR.glob("*.zspec.zsdl"))
    elif args.zsdl_files:
        zsdl_files = list(args.zsdl_files)
    else:
        parser.print_help()
        return 2

    if not zsdl_files:
        print("error: no .zspec.zsdl files found.", file=sys.stderr)
        return 2

    for p in zsdl_files:
        if not p.exists():
            print(f"error: file not found: {p}", file=sys.stderr)
            return 2

    # --- Load config and check LLM ---
    cfg    = config_mod.load(args.config)
    ai_cfg = cfg.get("ai", {})

    if not args.dry_run and not agent_mod.available(ai_cfg):
        print(
            "error: no LLM provider configured. Install the claude CLI or set "
            "ai.openai_base_url in config.yaml / config.site.yaml.",
            file=sys.stderr,
        )
        return 3

    # --- Build pipeline instance ---
    pipeline = ZSpecPipeline(
        max_iterations    = args.max_iterations,
        work_dir          = args.work_dir,
        annotate          = not args.no_annotate,
        skip_real_verify  = args.skip_real_verify,
        gate_on_synthesis = not args.no_gate,
        ai_cfg            = ai_cfg,
        verbose           = args.verbose,
        dry_run           = args.dry_run,
        llm_timeout       = args.timeout,
    )

    print(f"Pipeline: {len(zsdl_files)} spec(s)  workers={args.jobs}  "
          f"max_iter={args.max_iterations}  gate={'on' if not args.no_gate else 'off'}")

    # --- Execute ---
    results = _run_all(zsdl_files, pipeline, jobs=args.jobs)

    # --- Report ---
    _print_report(results)

    # --- Audit JSON (synthesis results only) ---
    if not args.dry_run:
        synth_results = [
            r.synthesis_result for r in results if r.synthesis_result is not None
        ]
        if synth_results:
            audit_out = args.out or _DEFAULT_AUDIT_OUT
            AuditReportGenerator().generate(
                synth_results, audit_out, human_readable=True
            )
            print(f"Audit report: {audit_out}")

    any_flagged = any(not r.acceptable for r in results)
    return 1 if any_flagged else 0


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def _run_one(zsdl_path: Path, pipeline: ZSpecPipeline) -> PipelineResult:
    return pipeline.run(zsdl_path)


def _run_all(
    zsdl_files: list[Path],
    pipeline: ZSpecPipeline,
    jobs: int,
) -> list[PipelineResult]:
    total   = len(zsdl_files)
    results: list[PipelineResult] = []

    if jobs <= 1:
        for i, zsdl_path in enumerate(zsdl_files, 1):
            print(f"[{i}/{total}] {zsdl_path.name} …", end="  ", flush=True)
            result = _run_one(zsdl_path, pipeline)
            _print_inline_status(result)
            results.append(result)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            future_to_path = {
                executor.submit(_run_one, p, pipeline): p for p in zsdl_files
            }
            done = 0
            for future in concurrent.futures.as_completed(future_to_path):
                done += 1
                zsdl_path = future_to_path[future]
                try:
                    result = future.result()
                except Exception as exc:
                    from theseus.pipeline import PipelineResult, StepResult
                    result = PipelineResult(
                        zsdl_path=zsdl_path,
                        steps=[StepResult("compile", StepStatus.ERROR, str(exc))],
                        outcome="compile_error",
                    )
                print(f"[{done}/{total}] {zsdl_path.name}  outcome={result.outcome}")
                results.append(result)

    return results


def _print_inline_status(result: PipelineResult) -> None:
    _ICON = {
        "passed":  "✓",
        "failed":  "✗",
        "skipped": "·",
        "error":   "!",
    }
    step_tags = " ".join(
        f"{_ICON.get(s.status.value, '?')}{s.name}" for s in result.steps
    )
    print(f"[{step_tags}]  {result.outcome}")


def _print_report(results: list[PipelineResult]) -> None:
    by_outcome: dict[str, list[str]] = {}
    for r in results:
        by_outcome.setdefault(r.outcome, []).append(r.zsdl_path.name)

    total      = len(results)
    acceptable = sum(1 for r in results if r.acceptable)
    flagged    = total - acceptable

    print(f"\n{'=' * 60}")
    print(
        f"Pipeline complete: {total} spec(s)  "
        f"acceptable={acceptable}  flagged={flagged}"
    )
    for outcome in sorted(by_outcome):
        names = by_outcome[outcome]
        mark  = "" if outcome in ("success", "partial", "infeasible") else "  ← ACTION REQUIRED"
        print(f"\n  {outcome.upper()} ({len(names)}){mark}:")
        for n in names[:30]:
            print(f"    {n}")
        if len(names) > 30:
            print(f"    … and {len(names) - 30} more")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
