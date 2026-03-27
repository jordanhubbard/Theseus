#!/usr/bin/env python3
"""
diff_snapshots.py

Compare two snapshot directories and report what changed between them.
Useful for tracking ecosystem drift over time or validating bootstrap runs.

Usage:
    python3 tools/diff_snapshots.py --before <dir> --after <dir> [--out <file>]

Output categories:
  added            - packages in after but not in before
  removed          - packages in before but not in after
  version_changed  - same package, different version in at least one ecosystem
  ecosystem_changed - same package, different set of ecosystems present
  unchanged        - same package, same versions, same ecosystems
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Snapshot loading
# ---------------------------------------------------------------------------


def load_snapshot(snapshot_dir: Path) -> dict[str, list[dict]]:
    """
    Load all canonical records from a snapshot directory.
    Returns {canonical_name: [record, ...]} grouped by canonical name.
    Skips manifest.json and non-canonical files.
    """
    groups: dict[str, list[dict]] = {}
    for path in snapshot_dir.rglob("*.json"):
        if path.name == "manifest.json":
            continue
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(rec, dict) or "identity" not in rec:
            continue
        name = rec["identity"].get("canonical_name", "")
        if not name:
            continue
        groups.setdefault(name, []).append(rec)
    return groups


def _summarize(records: list[dict]) -> dict:
    """Produce a compact per-package snapshot entry for diffing."""
    ecosystems = sorted({r["identity"].get("ecosystem", "") for r in records})
    versions = {
        r["identity"].get("ecosystem", ""): r["identity"].get("version", "")
        for r in records
    }
    return {"ecosystems": ecosystems, "versions": versions}


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------


def diff_snapshots(before_dir: Path, after_dir: Path) -> dict:
    """
    Compare two snapshot directories. Returns a structured diff report dict.
    """
    before = load_snapshot(before_dir)
    after = load_snapshot(after_dir)

    all_names = set(before) | set(after)

    added: list[str] = []
    removed: list[str] = []
    version_changed: list[dict] = []
    ecosystem_changed: list[dict] = []
    unchanged: list[str] = []

    for name in sorted(all_names):
        in_before = name in before
        in_after = name in after

        if in_after and not in_before:
            added.append(name)
            continue

        if in_before and not in_after:
            removed.append(name)
            continue

        b = _summarize(before[name])
        a = _summarize(after[name])

        eco_changed = b["ecosystems"] != a["ecosystems"]
        # Compare versions only for ecosystems present in both snapshots.
        # A new ecosystem appearing is eco_changed, not ver_changed.
        common_ecos = set(b["ecosystems"]) & set(a["ecosystems"])
        ver_changed = any(
            b["versions"].get(eco) != a["versions"].get(eco)
            for eco in common_ecos
        )

        if ver_changed:
            version_changed.append({"canonical_name": name, "before": b, "after": a})
        elif eco_changed:
            ecosystem_changed.append({"canonical_name": name, "before": b, "after": a})
        else:
            unchanged.append(name)

    return {
        "before": str(before_dir),
        "after": str(after_dir),
        "summary": {
            "total_before": len(before),
            "total_after": len(after),
            "added_count": len(added),
            "removed_count": len(removed),
            "version_changed_count": len(version_changed),
            "ecosystem_changed_count": len(ecosystem_changed),
            "unchanged_count": len(unchanged),
        },
        "added": added,
        "removed": removed,
        "version_changed": version_changed,
        "ecosystem_changed": ecosystem_changed,
        "unchanged": unchanged,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compare two Theseus snapshots and report what changed."
    )
    ap.add_argument("--before", type=Path, required=True, metavar="DIR",
                    help="Older snapshot directory")
    ap.add_argument("--after", type=Path, required=True, metavar="DIR",
                    help="Newer snapshot directory")
    ap.add_argument("--out", type=Path, metavar="FILE",
                    help="Write JSON diff report to this file (default: stdout only)")
    args = ap.parse_args()

    for path, name in [(args.before, "--before"), (args.after, "--after")]:
        if not path.is_dir():
            print(f"Error: {name} path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

    report = diff_snapshots(args.before, args.after)
    s = report["summary"]

    print(
        f"Snapshot diff: {args.before} → {args.after}\n"
        f"  Before:            {s['total_before']} package(s)\n"
        f"  After:             {s['total_after']} package(s)\n"
        f"  Added:             {s['added_count']}\n"
        f"  Removed:           {s['removed_count']}\n"
        f"  Version changed:   {s['version_changed_count']}\n"
        f"  Ecosystem changed: {s['ecosystem_changed_count']}\n"
        f"  Unchanged:         {s['unchanged_count']}"
    )

    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"\nDiff report written to {args.out}")
    else:
        print(f"\n{output}")


if __name__ == "__main__":
    main()
