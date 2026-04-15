#!/usr/bin/env python3
"""
synthesize_all_specs.py — Bulk clean-room synthesis for all (or selected) ZSDL specs.

Iterates over compiled .zspec.json files, synthesises each one, and writes an
aggregate audit report to reports/synthesis/audit.json.

Usage:
    python3 tools/synthesize_all_specs.py
    python3 tools/synthesize_all_specs.py --filter-backend python_module
    python3 tools/synthesize_all_specs.py --top 5
    python3 tools/synthesize_all_specs.py _build/zspecs/zlib.zspec.json _build/zspecs/_bisect.zspec.json
    python3 tools/synthesize_all_specs.py --dry-run

Exit codes:
    0   All specs succeeded
    1   At least one spec had partial or full failure
    2   Setup error (no specs found, LLM unavailable, etc.)
    3   LLM not configured
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import theseus.agent as agent_mod
import theseus.config as config_mod
from theseus.pipeline import ZSpecPipeline
from theseus.synthesis.annotate import zsdl_path_for_spec_json
from theseus.synthesis.audit import AuditReportGenerator
from theseus.synthesis.runner import SynthesisResult, SynthesisRunner

_BUILD_ZSPECS = _REPO_ROOT / "_build" / "zspecs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthesise clean-room implementations for all ZSDL specs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "specs",
        nargs="*",
        type=Path,
        help="Specific .zspec.json paths (default: all in _build/zspecs/).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / "reports" / "synthesis" / "audit.json",
        metavar="PATH",
        help="Audit report output path (default: reports/synthesis/audit.json).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        metavar="N",
        help="Max LLM iterations per spec (default: 3).",
    )
    parser.add_argument(
        "--filter-backend",
        metavar="BACKEND",
        default=None,
        help="Only synthesise specs with this library.backend value "
             "(e.g. python_module, ctypes, cli).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Only synthesise the first N specs.",
    )
    parser.add_argument(
        "--no-annotate",
        action="store_true",
        help="Skip writing results back to .zspec.zsdl files.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Parallel synthesis workers (default: 1; LLM rate limits apply).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which specs would be synthesised and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream verify_behavior.py output for each spec.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to config.yaml (site overrides loaded from config.site.yaml alongside it).",
    )
    args = parser.parse_args(argv)

    # --- Load config and check LLM ---
    cfg = config_mod.load(args.config)
    ai_cfg = cfg.get("ai", {})

    if not args.dry_run and not agent_mod.available(ai_cfg):
        print(
            "error: no LLM provider configured. Install the claude CLI or set "
            "ai.openai_base_url in config.yaml / config.site.yaml.",
            file=sys.stderr,
        )
        return 3

    # --- Collect spec paths ---
    if args.specs:
        spec_paths = list(args.specs)
    else:
        if not _BUILD_ZSPECS.is_dir():
            print(
                f"error: compiled spec directory not found: {_BUILD_ZSPECS}\n"
                "Run 'make compile-zsdl' first.",
                file=sys.stderr,
            )
            return 2
        spec_paths = sorted(_BUILD_ZSPECS.glob("*.zspec.json"))

    if not spec_paths:
        print("error: no spec files found.", file=sys.stderr)
        return 2

    # --- Filter by backend ---
    if args.filter_backend:
        spec_paths = _filter_by_backend(spec_paths, args.filter_backend)
        if not spec_paths:
            print(
                f"error: no specs match --filter-backend {args.filter_backend!r}.",
                file=sys.stderr,
            )
            return 2

    # --- Limit to top N ---
    if args.top is not None:
        spec_paths = spec_paths[: args.top]

    # --- Dry-run mode ---
    if args.dry_run:
        print(f"Would synthesise {len(spec_paths)} spec(s):")
        for p in spec_paths:
            print(f"  {p}")
        return 0

    # --- Build pipeline ---
    work_base = Path(tempfile.gettempdir()) / "theseus-synthesis"
    work_base.mkdir(parents=True, exist_ok=True)

    pipeline = ZSpecPipeline(
        max_iterations=args.max_iterations,
        work_dir=work_base,
        annotate=not args.no_annotate,
        # Real-library verification is skipped in bulk mode — the library may
        # not be installed on every machine that runs synthesize-all.
        skip_real_verify=True,
        gate_on_synthesis=True,
        ai_cfg=ai_cfg,
        verbose=args.verbose,
    )

    print(f"Pipeline: {len(spec_paths)} spec(s)  workers={args.jobs}  "
          f"max_iter={args.max_iterations}")

    results = _run_all(
        spec_paths=spec_paths,
        pipeline=pipeline,
        jobs=args.jobs,
    )

    # --- Generate audit report ---
    AuditReportGenerator().generate(results, args.out, human_readable=True)
    print(f"\nAudit report written to: {args.out}")
    _print_final_summary(results)

    any_not_success = any(r.status != "success" for r in results)
    return 1 if any_not_success else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_by_backend(spec_paths: list[Path], backend: str) -> list[Path]:
    """Return only specs whose library.backend matches *backend*."""
    filtered = []
    for p in spec_paths:
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
            if spec.get("library", {}).get("backend", "") == backend:
                filtered.append(p)
        except Exception:
            pass
    return filtered


def _pipeline_one(spec_path: Path, pipeline: ZSpecPipeline) -> SynthesisResult:
    """
    Run the full pipeline for *spec_path* (.zspec.json).

    Derives the .zspec.zsdl source so the pipeline can re-compile and then
    synthesise in one shot.  Falls back to synthesis-only when the source
    file is absent (e.g. hand-imported or generated specs without a .zsdl).
    """
    name = spec_path.stem.replace(".zspec", "")

    zsdl_path = zsdl_path_for_spec_json(spec_path)
    if zsdl_path.exists():
        pr = pipeline.run(zsdl_path)
        if pr.synthesis_result is not None:
            return pr.synthesis_result
        # Pipeline stopped before synthesis (compile error, real-verify failure).
        return SynthesisResult(
            canonical_name=name,
            backend_lang="unknown",
            status="infeasible",
            model="",
            attempted_at="",
            iterations=0,
            notes=f"Pipeline stopped: {pr.outcome}",
            infeasible_reason="pipeline_error",
        )

    # No .zsdl source — run synthesis-only via the runner directly.
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return SynthesisResult(
            canonical_name=name,
            backend_lang="unknown",
            status="infeasible",
            model="",
            attempted_at="",
            iterations=0,
            notes=f"Cannot read spec: {exc}",
            infeasible_reason="read_error",
        )

    runner = SynthesisRunner(
        pipeline.ai_cfg,
        max_iterations=pipeline.max_iterations,
        verbose=pipeline.verbose,
    )
    work_base = pipeline.work_dir or (Path(tempfile.gettempdir()) / "theseus-synthesis")
    work_base.mkdir(parents=True, exist_ok=True)
    return runner.run(spec, spec_path, work_base)


def _run_all(
    spec_paths: list[Path],
    pipeline: ZSpecPipeline,
    jobs: int,
) -> list[SynthesisResult]:
    total   = len(spec_paths)
    results: list[SynthesisResult] = []

    if jobs <= 1:
        for i, spec_path in enumerate(spec_paths, 1):
            name = spec_path.stem.replace(".zspec", "")
            print(f"[{i}/{total}] {name} …", end=" ", flush=True)
            result = _pipeline_one(spec_path, pipeline)
            print(result.status)
            results.append(result)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(_pipeline_one, p, pipeline): p for p in spec_paths
            }
            done_count = 0
            for future in concurrent.futures.as_completed(futures):
                done_count += 1
                spec_path = futures[future]
                name = spec_path.stem.replace(".zspec", "")
                try:
                    result = future.result()
                    print(f"[{done_count}/{total}] {name}: {result.status}")
                except Exception as exc:
                    result = SynthesisResult(
                        canonical_name=name,
                        backend_lang="unknown",
                        status="infeasible",
                        model="",
                        attempted_at="",
                        iterations=0,
                        notes=f"Runner exception: {exc}",
                        infeasible_reason="runner_exception",
                    )
                    print(f"[{done_count}/{total}] {name}: ERROR — {exc}")
                results.append(result)

    return results


def _print_final_summary(results: list[SynthesisResult]) -> None:
    total = len(results)
    success = sum(1 for r in results if r.status == "success")
    partial = sum(1 for r in results if r.status == "partial")
    failed = sum(1 for r in results if r.status == "failed")
    build_failed = sum(1 for r in results if r.status == "build_failed")
    infeasible = sum(1 for r in results if r.status == "infeasible")
    rate = success / total if total else 0.0
    print(
        f"\n{total} specs | "
        f"success={success} partial={partial} failed={failed} "
        f"build_failed={build_failed} infeasible={infeasible} | "
        f"rate={rate:.1%}"
    )


if __name__ == "__main__":
    sys.exit(main())
