#!/usr/bin/env python3
"""
spec_vector_coverage.py — Test vector coverage report for Z-layer behavioral specs.

Reads compiled spec JSON files and produces a per-spec, per-category coverage
report showing how many invariants each category has and what fraction have
description fields set.  Useful for auditing spec completeness before a
compliance review.

Usage:
  python3 tools/spec_vector_coverage.py [--json] [--min-score N] [specs ...]

  specs          Compiled spec JSON files (default: _build/zspecs/*.zspec.json)
  --json         Output machine-readable JSON instead of a text table
  --min-score N  Only show specs below N% description coverage (default: show all)

Exit codes:
  0  always (this is a reporting tool, not a gating tool)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent
DEFAULT_GLOB = "_build/zspecs/*.zspec.json"

DIVIDER = "\u2500" * 40  # ────────────────────────────


def _is_described(inv: dict) -> bool:
    """Return True if the invariant has a non-empty description."""
    return bool(inv.get("description", "").strip())


def analyse_spec(path: Path) -> dict:
    """Parse one compiled spec file and return a coverage record."""
    data = json.loads(path.read_text(encoding="utf-8"))
    invariants = data.get("invariants", [])

    # Determine spec name from the identity block or filename.
    name = data.get("identity", {}).get("canonical_name") or path.stem.replace(".zspec", "")

    # Group invariants by category (fall back to empty string if missing).
    by_cat: dict[str, list[dict]] = {}
    for inv in invariants:
        cat = inv.get("category", "")
        by_cat.setdefault(cat, []).append(inv)

    categories = []
    for cat in sorted(by_cat):
        group = by_cat[cat]
        described = sum(1 for i in group if _is_described(i))
        score = round(100.0 * described / len(group), 1) if group else 0.0
        categories.append({
            "name": cat,
            "total": len(group),
            "described": described,
            "score": score,
        })

    total = len(invariants)
    described = sum(1 for i in invariants if _is_described(i))
    score = round(100.0 * described / total, 1) if total else 0.0

    return {
        "spec": name,
        "total": total,
        "described": described,
        "score": score,
        "categories": categories,
    }


def load_specs(paths: list[str]) -> list[dict]:
    """Load and sort spec coverage records from the given file paths."""
    records = []
    for p in sorted(Path(f) for f in paths):
        try:
            records.append(analyse_spec(p))
        except Exception as exc:
            print(f"warning: skipping {p}: {exc}", file=sys.stderr)
    records.sort(key=lambda r: r["spec"])
    return records


def resolve_spec_paths(positional: list[str]) -> list[str]:
    """Return explicit paths or expand the default glob."""
    if positional:
        return positional
    # Glob relative to repo root.
    matches = sorted(str(p) for p in REPO_ROOT.glob(DEFAULT_GLOB))
    if not matches:
        # Fall back to CWD.
        matches = sorted(str(p) for p in Path.cwd().glob(DEFAULT_GLOB))
    return matches


def print_text_report(records: list[dict]) -> None:
    """Print a human-readable coverage table."""
    print("Test Vector Coverage Report")
    print(DIVIDER)

    for rec in records:
        score_str = f"{rec['score']:.0f}%"
        print(f"spec: {rec['spec']}  ({rec['total']} invariants, {score_str} described)")
        for cat in rec["categories"]:
            cat_score = f"({cat['score']:.0f}%)"
            print(
                f"  {cat['name']:<16}: {cat['total']:>3} invariants, "
                f"{cat['described']:>3} described  {cat_score}"
            )
        print()

    # Summary line.
    total_specs    = len(records)
    total_invs     = sum(r["total"] for r in records)
    total_desc     = sum(r["described"] for r in records)
    overall_score  = round(100.0 * total_desc / total_invs, 0) if total_invs else 0.0

    print(DIVIDER)
    print(
        f"Summary: {total_specs} specs, {total_invs} invariants, "
        f"{total_desc} described ({overall_score:.0f}%)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spec_vector_coverage.py",
        description="Test vector coverage report for Z-layer behavioral specs.",
    )
    parser.add_argument(
        "specs",
        nargs="*",
        metavar="specs",
        help=f"Compiled spec JSON files (default: {DEFAULT_GLOB})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of a text table",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        metavar="N",
        help="Only show specs below N%% description coverage (default: show all)",
    )

    args = parser.parse_args(argv)

    paths = resolve_spec_paths(args.specs)
    if not paths:
        print("error: no spec files found", file=sys.stderr)
        return 0  # still exit 0 per spec

    records = load_specs(paths)

    # Apply --min-score filter.
    if args.min_score is not None:
        records = [r for r in records if r["score"] < args.min_score]

    if args.json:
        print(json.dumps(records, indent=2))
    else:
        print_text_report(records)

    return 0


if __name__ == "__main__":
    sys.exit(main())
