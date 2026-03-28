#!/usr/bin/env python3
"""
generate_stub.py

Reads every canonical record from SNAPSHOT, groups by canonical_name,
merges per-ecosystem data into a single stub record (stub: true), and
writes to OUT (default: ./stubs/).

If --driver is given (freebsd_ports, nixpkgs, or both), also runs the
driver on each stub and writes output files alongside the stub JSON.

Usage:
    python3 tools/generate_stub.py SNAPSHOT [--out DIR] [--driver DRIVER]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from theseus.importer import SCHEMA_VERSION
from theseus.drivers import DRIVERS


def _load_snapshot(snapshot_path: Path) -> list[dict]:
    """Load all JSON records from a snapshot directory."""
    records = []
    for p in sorted(snapshot_path.rglob("*.json")):
        if p.name == "manifest.json":
            continue
        try:
            records.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return records


def _merge_stubs(group: list[dict]) -> dict:
    """
    Merge a group of records (same canonical_name, different ecosystems)
    into a single stub record.
    """
    # Sort by confidence descending; use highest-confidence as base
    def _conf(r: dict) -> float:
        return r.get("provenance", {}).get("confidence", 0.0)

    sorted_group = sorted(group, key=_conf, reverse=True)
    base = json.loads(json.dumps(sorted_group[0]))  # deep copy

    # Merge maintainers (union, order-preserving)
    seen_m: set[str] = set()
    merged_maintainers = []
    for r in sorted_group:
        for m in r.get("descriptive", {}).get("maintainers", []):
            if m not in seen_m:
                seen_m.add(m)
                merged_maintainers.append(m)
    base.setdefault("descriptive", {})["maintainers"] = merged_maintainers

    # Merge conflicts (union)
    seen_c: set[str] = set()
    merged_conflicts = []
    for r in sorted_group:
        for c in r.get("conflicts", []):
            if c not in seen_c:
                seen_c.add(c)
                merged_conflicts.append(c)
    base["conflicts"] = merged_conflicts

    # Merge platforms include/exclude (union)
    seen_inc: set[str] = set()
    seen_exc: set[str] = set()
    merged_inc = []
    merged_exc = []
    for r in sorted_group:
        plat = r.get("platforms", {})
        for p in plat.get("include", []):
            if p not in seen_inc:
                seen_inc.add(p)
                merged_inc.append(p)
        for p in plat.get("exclude", []):
            if p not in seen_exc:
                seen_exc.add(p)
                merged_exc.append(p)
    base.setdefault("platforms", {})["include"] = merged_inc
    base["platforms"]["exclude"] = merged_exc

    # Mark as stub
    base["stub"] = True
    base["schema_version"] = SCHEMA_VERSION

    # Add provenance warning
    prov = base.setdefault("provenance", {})
    warnings = prov.setdefault("warnings", [])
    stub_warning = "generated stub — verify sources, checksums, and dependencies before use"
    if stub_warning not in warnings:
        warnings.append(stub_warning)

    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate stub records from a snapshot.",
    )
    parser.add_argument("snapshot", help="Path to snapshot directory")
    parser.add_argument("--out", default="stubs", help="Output directory (default: stubs/)")
    parser.add_argument(
        "--driver",
        choices=["freebsd_ports", "nixpkgs", "both"],
        help="Also run driver(s) and write output files",
    )
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.is_dir():
        print(f"ERROR: {snapshot_path} is not a directory", file=sys.stderr)
        return 1

    out_dir = Path(args.out)

    records = _load_snapshot(snapshot_path)
    if not records:
        print("No records found in snapshot.", file=sys.stderr)
        return 0

    # Group by canonical_name
    groups: dict[str, list[dict]] = {}
    for rec in records:
        name = rec.get("identity", {}).get("canonical_name", "unknown")
        groups.setdefault(name, []).append(rec)

    # Determine which drivers to run
    drivers_to_run: list[str] = []
    if args.driver == "both":
        drivers_to_run = ["freebsd_ports", "nixpkgs"]
    elif args.driver:
        drivers_to_run = [args.driver]

    stub_count = 0
    driver_output_count = 0

    for name, group in sorted(groups.items()):
        stub = _merge_stubs(group)

        # Write stub JSON
        stub_file = out_dir / f"{name}.json"
        stub_file.parent.mkdir(parents=True, exist_ok=True)
        stub_file.write_text(json.dumps(stub, indent=2), encoding="utf-8")
        stub_count += 1

        # Run drivers
        for driver_name in drivers_to_run:
            driver_fn = DRIVERS[driver_name]
            output = driver_fn(stub)
            driver_out = Path("output") / driver_name / name
            driver_out.mkdir(parents=True, exist_ok=True)
            for filename, content in output.items():
                (driver_out / filename).write_text(content, encoding="utf-8")
            driver_output_count += len(output)

    print(f"{stub_count} stubs written to {out_dir}/")
    if drivers_to_run:
        print(f"{driver_output_count} driver output files generated in output/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
