#!/usr/bin/env python3
"""
spec_coverage.py — Z-spec coverage report.

Scans the extraction output directory and reports which candidates have a
behavioral_spec (a matching zspecs/*.zspec.json) and which do not.

Usage:
  python3 tools/spec_coverage.py EXTRACTION_DIR [--top N] [--json]

  EXTRACTION_DIR  directory written by extract_candidates.py (contains *.json records)
  --top N         only consider the top-N candidates by composite_score (default: all)
  --json          write machine-readable output to stdout instead of a text report

Exit codes:
  0  report generated successfully
  1  no records found / bad input
  2  usage error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parent.parent
ZSPECS_DIR   = REPO_ROOT / "_build" / "zspecs"


# PyPI package name → spec file stem (when the import name differs from the package name)
_PACKAGE_ALIASES: dict[str, str] = {
    "python-dotenv": "dotenv",
    "python_dotenv": "dotenv",
    "pillow": "pillow",          # PIL; spec file is pillow
    "tomli": "tomllib",          # tomllib spec covers both
    "dnspython": "dns",          # PyPI package name; imports as dns
    "zope.interface": "zope_interface",  # namespace package; spec file uses underscore
    "protobuf": "protobuf",             # PyPI package name; imports as google.protobuf
    "fonttools": "fontTools",           # PyPI package name; imports as fontTools
}


def _has_spec(canonical_name: str) -> bool:
    # PyPI uses dashes; Python modules use underscores — check both normalizations.
    normalized = canonical_name.replace("-", "_")
    candidates = {canonical_name, normalized}
    # Also check known aliases
    if canonical_name in _PACKAGE_ALIASES:
        candidates.add(_PACKAGE_ALIASES[canonical_name])
    if normalized in _PACKAGE_ALIASES:
        candidates.add(_PACKAGE_ALIASES[normalized])
    return any((ZSPECS_DIR / f"{c}.zspec.json").exists() for c in candidates)


def load_extraction_records(extraction_dir: Path) -> list[dict]:
    """Return all extraction records from dir, sorted by composite_score desc."""
    records = []
    for path in sorted(extraction_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        records.append(data)

    def score(rec: dict) -> float:
        analysis = rec.get("analysis", {})
        return float(analysis.get("composite_score", 0.0))

    records.sort(key=score, reverse=True)
    return records


def build_report(records: list[dict], top: int | None) -> dict:
    if top is not None:
        records = records[:top]

    covered = []
    gaps = []
    for rec in records:
        # Accept records where canonical_name lives in identity or top-level
        identity = rec.get("identity", rec)
        name = identity.get("canonical_name") or rec.get("canonical_name", "")
        if not name:
            continue
        score = float((rec.get("analysis") or {}).get("composite_score", 0.0))
        # A record is "covered" if it has a behavioral_spec field OR a matching zspec file exists
        has_bspec = bool(rec.get("behavioral_spec")) or _has_spec(name)
        entry = {"canonical_name": name, "composite_score": score, "has_spec": has_bspec}
        if has_bspec:
            covered.append(entry)
        else:
            gaps.append(entry)

    return {
        "total": len(covered) + len(gaps),
        "covered": len(covered),
        "gap_count": len(gaps),
        "covered_list": covered,
        "gap_list": gaps,
    }


def print_text_report(report: dict) -> None:
    total    = report["total"]
    covered  = report["covered"]
    gap_count = report["gap_count"]
    pct      = f"{covered / total * 100:.1f}%" if total else "N/A"

    print(f"\nZ-Spec Coverage Report")
    print(f"{'─' * 40}")
    print(f"  Total candidates : {total}")
    print(f"  Covered          : {covered}  ({pct})")
    print(f"  Gap (no spec)    : {gap_count}")

    if report["covered_list"]:
        print(f"\nCovered ({covered}):")
        for e in report["covered_list"]:
            print(f"  ✓  {e['canonical_name']:30s}  score={e['composite_score']:.3f}")

    if report["gap_list"]:
        print(f"\nGap list ({gap_count}) — sorted by score, highest priority first:")
        for e in report["gap_list"]:
            print(f"  ✗  {e['canonical_name']:30s}  score={e['composite_score']:.3f}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report which extraction candidates have a behavioral spec"
    )
    parser.add_argument("extraction_dir", type=Path, help="Extraction output directory")
    parser.add_argument("--top", type=int, default=None,
                        help="Only consider the top-N candidates by score")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Write JSON report to stdout")
    args = parser.parse_args(argv)

    if not args.extraction_dir.is_dir():
        print(f"ERROR: {args.extraction_dir} is not a directory", file=sys.stderr)
        return 2

    records = load_extraction_records(args.extraction_dir)
    if not records:
        print(f"ERROR: no extraction records found in {args.extraction_dir}", file=sys.stderr)
        return 1

    report = build_report(records, top=args.top)

    if args.json_out:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
