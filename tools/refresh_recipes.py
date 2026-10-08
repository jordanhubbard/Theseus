#!/usr/bin/env python3
"""Refresh committed specs/ recipes from live upstreams, then optionally ingest.

This is the supported restock path. It does not require a prior snapshots/
directory. The package list is the committed corpus.

Usage:
    python3 tools/refresh_recipes.py
    python3 tools/refresh_recipes.py --nixpkgs /path/to/nixpkgs --ports /path/to/ports
    python3 tools/refresh_recipes.py --dry-run --json
    python3 tools/refresh_recipes.py --no-remote   # local trees only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from theseus.refresh import (  # noqa: E402
    DEFAULT_NIXPKGS_REF,
    DEFAULT_PORTS_REF,
    refresh_recipes,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Refresh specs/ from PyPI, npm, Nixpkgs, and FreeBSD Ports. "
            "Registry APIs are always live. Tree ecosystems use a local "
            "checkout when given, otherwise GitHub raw."
        )
    )
    ap.add_argument(
        "--specs",
        type=Path,
        default=_REPO_ROOT / "specs",
        help="Committed recipe directory (default: specs/)",
    )
    ap.add_argument("--nixpkgs", type=Path, metavar="PATH", help="Nixpkgs checkout")
    ap.add_argument("--ports", type=Path, metavar="PATH", help="FreeBSD Ports checkout")
    ap.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds")
    ap.add_argument("--jobs", type=int, default=8, help="Parallel workers (1=serial)")
    ap.add_argument(
        "--ecosystems",
        default="",
        help="Comma-separated subset: pypi,npm,nixpkgs,freebsd_ports",
    )
    ap.add_argument("--nixpkgs-ref", default=DEFAULT_NIXPKGS_REF, help="GitHub ref for Nixpkgs raw")
    ap.add_argument("--ports-ref", default=DEFAULT_PORTS_REF, help="GitHub ref for Ports raw")
    ap.add_argument("--no-remote", action="store_true", help="Do not fetch GitHub raw for trees")
    ap.add_argument("--dry-run", action="store_true", help="Fetch and report, do not write specs/")
    ap.add_argument("--json", action="store_true", help="Print the full report as JSON")
    args = ap.parse_args(argv)

    if not args.specs.is_dir():
        print("Error: specs directory does not exist: %s" % args.specs, file=sys.stderr)
        return 2
    if args.nixpkgs is not None and not args.nixpkgs.is_dir():
        print("Error: --nixpkgs is not a directory: %s" % args.nixpkgs, file=sys.stderr)
        return 2
    if args.ports is not None and not args.ports.is_dir():
        print("Error: --ports is not a directory: %s" % args.ports, file=sys.stderr)
        return 2

    ecosystems = [e.strip() for e in args.ecosystems.split(",") if e.strip()] or None
    report = refresh_recipes(
        args.specs,
        nixpkgs_root=args.nixpkgs,
        ports_root=args.ports,
        allow_remote=not args.no_remote,
        timeout=args.timeout,
        jobs=args.jobs,
        dry_run=args.dry_run,
        ecosystems=ecosystems,
        nixpkgs_ref=args.nixpkgs_ref,
        ports_ref=args.ports_ref,
    )
    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        summary = report["summary"]
        print(
            "Refresh %s: %d recipes, jobs=%d%s"
            % (
                report["specs_dir"],
                report["count"],
                report["jobs"],
                " (dry-run)" if report["dry_run"] else "",
            )
        )
        print(
            "  refreshed=%d partial=%d failed=%d unchanged=%d error=%d"
            % (
                summary.get("refreshed", 0),
                summary.get("partial", 0),
                summary.get("failed", 0),
                summary.get("unchanged", 0),
                summary.get("error", 0),
            )
        )
        if report.get("nixpkgs_root"):
            print("  nixpkgs tree: %s" % report["nixpkgs_root"])
        elif report.get("allow_remote"):
            print("  nixpkgs: GitHub raw (%s)" % args.nixpkgs_ref)
        if report.get("ports_root"):
            print("  ports tree: %s" % report["ports_root"])
        elif report.get("allow_remote"):
            print("  ports: GitHub raw (%s)" % args.ports_ref)
        failed = [r for r in report["recipes"] if r["status"] in ("failed", "error")]
        partial = [r for r in report["recipes"] if r["status"] == "partial"]
        if partial:
            print("  partial (%d):" % len(partial))
            for row in partial[:20]:
                print("    %s  updated=%s failed=%s" % (row["name"], row["updated"], row["failed"]))
            if len(partial) > 20:
                print("    ...")
        if failed:
            print("  failed (%d):" % len(failed))
            for row in failed[:20]:
                print("    %s  failed=%s" % (row["name"], row.get("failed") or row.get("error")))
            if len(failed) > 20:
                print("    ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
