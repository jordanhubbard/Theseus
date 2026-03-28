#!/usr/bin/env python3
"""
fill_nixpkgs_deps.py

Post-import pass that fills in dependency lists for nixpkgs records that were
imported without deps (the batch eval importer skips deps to avoid infinite
recursion with --strict).

Uses per-package nix-instantiate --eval (no --strict) with a timeout.

Usage:
    python3 tools/fill_nixpkgs_deps.py SNAPSHOT_DIR NIXPKGS_ROOT
                                        [--timeout SECS] [--overwrite]

Arguments:
  SNAPSHOT_DIR   Directory containing nixpkgs *.json records to update
  NIXPKGS_ROOT   Path to a nixpkgs checkout (used for nix-instantiate eval)

Options:
  --timeout      Per-package eval timeout in seconds (default: 30)
  --overwrite    Re-evaluate even for records that already have dep lists
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from theseus.importer import fill_nixpkgs_deps, _nix_instantiate_available


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fill nixpkgs dep lists via per-package nix-instantiate eval.",
    )
    parser.add_argument("snapshot_dir", help="Directory of nixpkgs *.json records")
    parser.add_argument("nixpkgs_root", help="Path to nixpkgs checkout")
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-package eval timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-evaluate even records that already have dep lists",
    )
    args = parser.parse_args(argv)

    snapshot_dir = Path(args.snapshot_dir)
    nixpkgs_root = Path(args.nixpkgs_root)

    if not snapshot_dir.is_dir():
        print(f"ERROR: snapshot_dir not found: {snapshot_dir}", file=sys.stderr)
        return 1
    if not nixpkgs_root.is_dir():
        print(f"ERROR: nixpkgs_root not found: {nixpkgs_root}", file=sys.stderr)
        return 1
    if not _nix_instantiate_available():
        print("ERROR: nix-instantiate not found in PATH", file=sys.stderr)
        return 1

    filled, skipped, failed = fill_nixpkgs_deps(
        snapshot_dir,
        nixpkgs_root,
        timeout=args.timeout,
        overwrite=args.overwrite,
    )

    print(
        f"\nDone: {filled} filled, {skipped} skipped "
        f"(already had deps or non-nixpkgs), {failed} failed"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
