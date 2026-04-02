#!/usr/bin/env python3
"""
verify_all_specs.py — Run every Z-layer spec and emit a JSON results file.

Runs InvariantRunner on every *.zspec.json file in zspecs/ (or the paths
provided on the command line) and writes a single JSON document containing:
  - per-spec results with per-invariant pass/fail details
  - an aggregate summary (total specs, invariants, pass/fail/skip counts)

This output can feed --baseline comparisons and CI dashboards.

Usage:
  python3 tools/verify_all_specs.py [--out FILE] [spec ...]

  --out FILE   Write JSON to FILE (default: verify_all_specs_out.json)
  spec         One or more .zspec.json paths; defaults to zspecs/*.zspec.json

Exit codes:
  0  All invariants passed
  1  One or more invariants failed
  2  Usage error / harness error
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
ZSPECS_GLOB = "zspecs/*.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


def run_spec(spec_path: Path) -> dict:
    """Run a single spec and return a result dict."""
    result: dict = {
        "spec": str(spec_path.relative_to(REPO_ROOT) if spec_path.is_relative_to(REPO_ROOT) else spec_path),
        "canonical_name": None,
        "lib_version": None,
        "error": None,
        "invariants": [],
        "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
    }

    try:
        spec = vb.SpecLoader().load(spec_path)
    except vb.SpecError as exc:
        result["error"] = f"SpecError: {exc}"
        return result

    result["canonical_name"] = spec.get("identity", {}).get("canonical_name")

    try:
        lib = vb.LibraryLoader().load(spec["library"])
    except vb.LibraryNotFoundError as exc:
        result["error"] = f"LibraryNotFoundError: {exc}"
        return result

    lib_version = vb._get_lib_version(spec["library"], lib)
    result["lib_version"] = lib_version or None

    runner = vb.InvariantRunner()
    inv_results = runner.run_all(spec, lib, lib_version=lib_version)

    for r in inv_results:
        result["invariants"].append({
            "id": r.inv_id,
            "passed": r.passed,
            "message": r.message,
            "skip_reason": r.skip_reason,
        })

    s = result["summary"]
    s["total"]   = len(inv_results)
    s["passed"]  = sum(1 for r in inv_results if r.passed and not r.skip_reason)
    s["failed"]  = sum(1 for r in inv_results if not r.passed)
    s["skipped"] = sum(1 for r in inv_results if r.skip_reason)

    return result


def collect_specs(paths: list[str]) -> list[Path]:
    if not paths:
        return sorted(REPO_ROOT.glob(ZSPECS_GLOB))
    result = []
    for p in paths:
        fp = Path(p)
        if fp.is_dir():
            result.extend(sorted(fp.glob("*.zspec.json")))
        elif fp.is_file():
            result.append(fp)
        else:
            print(f"WARNING: {p} does not exist, skipping", file=sys.stderr)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all Z-layer specs and write results to JSON"
    )
    parser.add_argument(
        "--out", type=Path, default=Path("verify_all_specs_out.json"),
        help="Output JSON file (default: verify_all_specs_out.json)"
    )
    parser.add_argument(
        "specs", nargs="*",
        help="Spec files or directories (default: zspecs/*.zspec.json)"
    )
    args = parser.parse_args(argv)

    spec_paths = collect_specs(args.specs)
    if not spec_paths:
        print("No spec files found.", file=sys.stderr)
        return 2

    spec_results = []
    total_inv = passed_inv = failed_inv = skipped_inv = 0
    any_failed = False

    for path in spec_paths:
        print(f"  {path.name} ...", end=" ", flush=True)
        result = run_spec(path)
        spec_results.append(result)

        s = result["summary"]
        total_inv   += s["total"]
        passed_inv  += s["passed"]
        failed_inv  += s["failed"]
        skipped_inv += s["skipped"]

        if result["error"]:
            print(f"ERROR: {result['error']}")
            any_failed = True
        elif s["failed"]:
            print(f"FAIL  ({s['failed']}/{s['total']} failed)")
            any_failed = True
        else:
            print(f"OK    ({s['passed']} passed, {s['skipped']} skipped)")

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_specs":     len(spec_results),
            "specs_ok":        sum(1 for r in spec_results if not r["error"] and r["summary"]["failed"] == 0),
            "specs_failed":    sum(1 for r in spec_results if r["error"] or r["summary"]["failed"] > 0),
            "total_invariants": total_inv,
            "passed":          passed_inv,
            "failed":          failed_inv,
            "skipped":         skipped_inv,
        },
        "specs": spec_results,
    }

    args.out.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        f"\n{len(spec_results)} specs: "
        f"{output['summary']['specs_ok']} OK, "
        f"{output['summary']['specs_failed']} failed  |  "
        f"{total_inv} invariants: {passed_inv} passed, {failed_inv} failed, {skipped_inv} skipped"
    )
    print(f"Results written to {args.out}")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
