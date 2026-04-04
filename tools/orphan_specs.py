#!/usr/bin/env python3
"""
orphan_specs.py — Find Z-specs with no matching extraction record.

Scans _build/zspecs/*.zspec.json and reports which specs have a canonical_name
that does not appear in any extraction record in the given directory.

This is the reverse of spec_coverage.py: instead of finding candidates with no
spec, this finds specs with no corresponding candidate.

Usage:
  python3 tools/orphan_specs.py EXTRACTION_DIR [--json]

  EXTRACTION_DIR  directory written by extract_candidates.py (contains *.json records)
  --json          write machine-readable output to stdout instead of a text report

Exit codes:
  0  no orphan specs found
  1  one or more orphan specs found
  2  usage error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent
ZSPECS_DIR = REPO_ROOT / "_build" / "zspecs"


def load_spec_names() -> list[str]:
    """Return a sorted list of canonical_name values from all compiled zspecs."""
    names = []
    for path in sorted(ZSPECS_DIR.glob("*.zspec.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("identity", {}).get("canonical_name", "")
        if name:
            names.append(name)
    return names


def load_extraction_canonical_names(extraction_dir: Path) -> set[str]:
    """Return the set of all canonical_names found in extraction records."""
    names: set[str] = set()
    for path in sorted(extraction_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        # Accept canonical_name in identity or at the top level
        identity = data.get("identity", data)
        name = identity.get("canonical_name") or data.get("canonical_name", "")
        if name:
            names.add(name)
    return names


def build_report(spec_names: list[str], extraction_names: set[str]) -> dict:
    orphans = []
    matched = []
    for name in spec_names:
        if name in extraction_names:
            matched.append(name)
        else:
            orphans.append(name)

    return {
        "total_specs": len(spec_names),
        "matched": len(matched),
        "orphan_count": len(orphans),
        "matched_list": matched,
        "orphan_list": orphans,
    }


def print_text_report(report: dict) -> None:
    total   = report["total_specs"]
    matched = report["matched"]
    orphans = report["orphan_count"]
    pct     = f"{matched / total * 100:.1f}%" if total else "N/A"

    print(f"\nOrphan Spec Report")
    print(f"{'─' * 40}")
    print(f"  Total specs       : {total}")
    print(f"  Matched           : {matched}  ({pct})")
    print(f"  Orphan (no record): {orphans}")

    if report["matched_list"]:
        print(f"\nMatched ({matched}):")
        for name in report["matched_list"]:
            print(f"  ✓  {name}")

    if report["orphan_list"]:
        print(f"\nOrphan specs ({orphans}) — no extraction record found:")
        for name in report["orphan_list"]:
            print(f"  ✗  {name}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Find Z-specs whose canonical_name has no matching extraction record"
    )
    parser.add_argument("extraction_dir", type=Path, help="Extraction output directory")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Write JSON report to stdout")
    args = parser.parse_args(argv)

    if not ZSPECS_DIR.is_dir():
        print(
            f"ERROR: {ZSPECS_DIR} does not exist. Run 'make compile-zsdl' first.",
            file=sys.stderr,
        )
        return 2

    if not args.extraction_dir.is_dir():
        print(f"ERROR: {args.extraction_dir} is not a directory", file=sys.stderr)
        return 2

    spec_names = load_spec_names()
    if not spec_names:
        print(f"ERROR: no compiled specs found in {ZSPECS_DIR}", file=sys.stderr)
        return 1

    extraction_names = load_extraction_canonical_names(args.extraction_dir)

    report = build_report(spec_names, extraction_names)

    if args.json_out:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print_text_report(report)

    return 1 if report["orphan_count"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
