#!/usr/bin/env python3
"""
rank_by_deps.py

Rank packages by reverse-dependency count (fan-in): how many other packages
list each package as a dependency.  This identifies the foundational packages
worth generating specs for first — the ones that, if built and cached, unblock
the most downstream builds.

Usage:
    python3 tools/rank_by_deps.py <snapshot_dir> [<snapshot_dir2> ...] \\
        [--out <ranked.json>] [--top N] [--min-refs N]

Output is a JSON array sorted by ref_count descending:
    [{"canonical_name": "zlib", "ref_count": 4210, "ecosystems": ["freebsd_ports","nixpkgs"], ...}, ...]
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def load_records(snapshot_dirs: list[Path]):
    for snap in snapshot_dirs:
        for path in sorted(snap.rglob("*.json")):
            if path.name in ("manifest.json",):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "identity" in data:
                    yield data
            except Exception:
                continue


def main():
    ap = argparse.ArgumentParser(description="Rank packages by reverse-dep fan-in.")
    ap.add_argument("snapshots", type=Path, nargs="+", metavar="snapshot_dir",
                    help="One or more snapshot directories to analyse.")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write ranked JSON to this file (default: stdout only).")
    ap.add_argument("--top", type=int, default=0,
                    help="Print/write only the top N entries (0 = all).")
    ap.add_argument("--min-refs", type=int, default=1,
                    help="Exclude packages with fewer than N reverse deps (default: 1).")
    args = ap.parse_args()

    for d in args.snapshots:
        if not d.is_dir():
            print(f"ERROR: not a directory: {d}", file=sys.stderr)
            sys.exit(1)

    # Pass 1: collect all known canonical names and per-ecosystem presence.
    known: dict[str, set[str]] = defaultdict(set)   # canonical_name → {ecosystem,...}
    all_records: list[dict] = []
    for rec in load_records(args.snapshots):
        ident = rec.get("identity", {})
        name = ident.get("canonical_name") or ident.get("name") or ident.get("pname")
        eco = ident.get("ecosystem", "unknown")
        if name:
            known[name].add(eco)
            all_records.append(rec)

    print(f"Loaded {len(all_records)} records covering {len(known)} canonical names.",
          file=sys.stderr)

    # Pass 2: count reverse deps.
    ref_count: dict[str, int] = defaultdict(int)
    ref_by_eco: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rec in all_records:
        eco = rec.get("identity", {}).get("ecosystem", "unknown")
        deps = rec.get("dependencies", {})
        seen_in_rec: set[str] = set()
        for bucket in ("build", "host", "runtime", "test"):
            for dep in deps.get(bucket, []):
                if dep and dep not in seen_in_rec:
                    ref_count[dep] += 1
                    ref_by_eco[dep][eco] += 1
                    seen_in_rec.add(dep)

    # Build ranked output.
    ranked = []
    for name, count in ref_count.items():
        if count < args.min_refs:
            continue
        ecosystems = sorted(known.get(name, set()))
        # If name is known in our snapshot, tag it; otherwise it's an external dep name.
        in_snapshot = bool(ecosystems)
        ranked.append({
            "canonical_name": name,
            "ref_count": count,
            "ecosystems": ecosystems,
            "in_snapshot": in_snapshot,
            "refs_by_ecosystem": dict(sorted(ref_by_eco[name].items())),
        })

    ranked.sort(key=lambda x: (-x["ref_count"], x["canonical_name"]))

    top = args.top or len(ranked)
    output = ranked[:top]

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(output)} entries to {args.out}", file=sys.stderr)

    # Always print top 30 to stdout as a quick summary.
    preview = output[:30]
    for i, entry in enumerate(preview, 1):
        eco_str = ",".join(entry["ecosystems"]) if entry["ecosystems"] else "(external)"
        snap_tag = "" if entry["in_snapshot"] else " *"
        print(f"  {i:3}. {entry['canonical_name']:<40} refs={entry['ref_count']:>5}  [{eco_str}]{snap_tag}")

    total_in_snap = sum(1 for e in ranked if e["in_snapshot"])
    print(f"\nTotal unique dep names referenced: {len(ranked)}", file=sys.stderr)
    print(f"Of those, {total_in_snap} are known packages in the snapshot.", file=sys.stderr)


if __name__ == "__main__":
    main()
