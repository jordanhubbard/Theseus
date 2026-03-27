#!/usr/bin/env python3
"""
overlap_report.py

Scan a snapshot directory produced by bootstrap_canonical_recipes.py and generate
ecosystem overlap/divergence reports based on canonical_name.
"""

from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

def load_records(snapshot_root: Path):
    for path in snapshot_root.rglob("*.json"):
        if path.name == "manifest.json" or "reports" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "identity" in data:
                yield path, data
        except Exception:
            continue

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    by_name = defaultdict(list)
    for path, rec in load_records(args.snapshot):
        ident = rec.get("identity", {})
        by_name[ident.get("canonical_name", "unknown")].append({
            "ecosystem": ident.get("ecosystem"),
            "version": ident.get("version"),
            "ecosystem_id": ident.get("ecosystem_id"),
            "path": str(path),
        })

    overlap = {}
    only_nix = {}
    only_ports = {}
    version_skew = {}

    for name, entries in sorted(by_name.items()):
        ecosystems = {e["ecosystem"] for e in entries}
        versions = sorted({e["version"] for e in entries if e.get("version")})
        if {"nixpkgs", "freebsd_ports"} <= ecosystems:
            overlap[name] = entries
            if len(versions) > 1:
                version_skew[name] = entries
        elif ecosystems == {"nixpkgs"}:
            only_nix[name] = entries
        elif ecosystems == {"freebsd_ports"}:
            only_ports[name] = entries

    summary = {
        "packages_total": len(by_name),
        "overlap_count": len(overlap),
        "only_nix_count": len(only_nix),
        "only_ports_count": len(only_ports),
        "version_skew_count": len(version_skew),
    }

    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "overlap.json").write_text(json.dumps(overlap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "only_nix.json").write_text(json.dumps(only_nix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "only_ports.json").write_text(json.dumps(only_ports, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "version_skew.json").write_text(json.dumps(version_skew, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
