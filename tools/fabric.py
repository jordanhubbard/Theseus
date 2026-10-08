#!/usr/bin/env python3
"""
fabric.py — query and ingest the git-backed OSS knowledge fabric.

The committed tree under fabric/packages/ is the database. Historical
queries use git revisions (`--rev`). Reverse dependencies are derived
from outbound edges at query time.

Usage:
  python3 tools/fabric.py ingest [DIR ...]
  python3 tools/fabric.py show zlib
  python3 tools/fabric.py deps requests
  python3 tools/fabric.py rdeps urllib3
  python3 tools/fabric.py query --license MIT
  python3 tools/fabric.py stats
  python3 tools/fabric.py validate
  python3 tools/fabric.py history zlib
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from theseus.fabric import (  # noqa: E402
    ingest,
    load_store,
    repo_root_from,
)


def _print_json(data, raw: bool) -> None:
    if raw:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _summary_line(rec: dict) -> str:
    ident = rec.get("identity") or {}
    name = ident.get("canonical_name") or "?"
    lic = rec.get("license") or {}
    spdx = ",".join(lic.get("spdx") or []) or "-"
    repo = (rec.get("repository") or {}).get("url") or "-"
    ecos = ",".join(sorted({e.get("ecosystem") or "" for e in rec.get("ecosystems") or []} - {""})) or "-"
    return "%-28s  %-16s  %-12s  %s" % (name, ecos, spdx, repo)


def cmd_ingest(args: argparse.Namespace) -> int:
    root = repo_root_from(_REPO_ROOT)
    dirs = [Path(p) for p in args.dirs] if args.dirs else [root / "specs", root / "examples"]
    result = ingest(
        root,
        dirs,
        out_dir=Path(args.out) if args.out else None,
        jobs=args.jobs,
    )
    if args.json:
        _print_json(result, True)
    else:
        print(
            "Wrote %d fingerprints from %d recipes to %s "
            "(skipped %d, jobs=%d)."
            % (
                result["written"],
                result.get("recipes", 0),
                result["out_dir"],
                result["skipped"],
                result.get("jobs", 1),
            )
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT, rev=args.rev)
    rec = store.get(args.name)
    if rec is None:
        print("ERROR: no fingerprint for %r" % args.name, file=sys.stderr)
        return 1
    _print_json(rec, True)
    return 0


def cmd_deps(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT, rev=args.rev)
    try:
        items = store.deps(args.name, scope=args.scope)
    except KeyError:
        print("ERROR: no fingerprint for %r" % args.name, file=sys.stderr)
        return 1
    if args.json:
        _print_json(items, True)
        return 0
    if not items:
        print("%s depends on nothing recorded." % args.name)
        return 0
    print("%s depends on:" % args.name)
    for dep in items:
        eco = dep.get("ecosystem") or ""
        extra = " [%s]" % eco if eco else ""
        print("  %-8s  %s%s" % (dep.get("scope"), dep.get("name"), extra))
    return 0


def cmd_rdeps(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT, rev=args.rev)
    items = store.rdeps(args.name, scope=args.scope)
    if args.json:
        _print_json(items, True)
        return 0
    if not items:
        print("Nothing recorded depends on %s." % args.name)
        return 0
    print("Packages that depend on %s:" % args.name)
    for dep in items:
        eco = dep.get("ecosystem") or ""
        extra = " [%s]" % eco if eco else ""
        print("  %-8s  %s%s" % (dep.get("scope"), dep.get("name"), extra))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT, rev=args.rev)
    has_repo = None
    if args.has_repo:
        has_repo = True
    if args.missing_repo:
        has_repo = False
    matches = store.query(
        name=args.name,
        license=args.license,
        repo=args.repo,
        ecosystem=args.ecosystem,
        has_repo=has_repo,
        missing_license=args.missing_license,
    )
    if args.json:
        _print_json(matches, True)
        return 0
    print("%-28s  %-16s  %-12s  %s" % ("name", "ecosystems", "license", "repository"))
    print("-" * 90)
    for rec in matches:
        print(_summary_line(rec))
    print("%d package(s)" % len(matches))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT, rev=args.rev)
    stats = store.stats()
    if args.json:
        _print_json(stats, True)
        return 0
    total = stats["packages"]
    print("OSS knowledge fabric%s" % (" @ %s" % args.rev if args.rev else " (working tree)"))
    print("  packages:              %d" % total)
    print("  with repository:       %d" % stats["with_repository"])
    print("  with license:          %d" % stats["with_license"])
    print("  with depends_on:       %d" % stats["with_depends_on"])
    print("  with dependents:       %d" % stats["with_dependents"])
    print("  with behavioral spec:  %d" % stats["with_behavioral_spec"])
    print("  with source commit:    %d" % stats.get("with_source_commit", 0))
    print("  with maintainers:      %d" % stats.get("with_maintainers", 0))
    print("  with distributions:    %d" % stats.get("with_distributions", 0))
    print("  dep edges resolved:    %d / %d" % (
        stats.get("dep_resolved", 0), stats.get("dep_edges", 0),
    ))
    print("  dep edges dangling:    %d" % stats.get("dep_dangling", 0))
    print("  dropped dep tokens:    %d" % stats.get("dropped_dependencies", 0))
    print("  missing repository:    %d" % stats["missing_repository"])
    print("  missing license:       %d" % stats["missing_license"])
    print("  ecosystems:")
    for eco, count in stats["ecosystems"].items():
        print("    %-16s %d" % (eco, count))
    print("  licenses (top 10):")
    for i, (lic, count) in enumerate(stats["licenses"].items()):
        if i >= 10:
            break
        print("    %-16s %d" % (lic, count))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT, rev=args.rev)
    errors = store.validate()
    if args.json:
        _print_json({"ok": not errors, "errors": errors, "packages": len(store)}, True)
        return 1 if errors else 0
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print("%d error(s) in %d fingerprint(s)" % (len(errors), len(store)), file=sys.stderr)
        return 1
    print("OK: %d fingerprint(s)" % len(store))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    store = load_store(_REPO_ROOT)
    try:
        entries = store.history(args.name)
    except RuntimeError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if args.json:
        _print_json(entries, True)
        return 0
    if not entries:
        print("No git history for %s (file may be uncommitted)." % args.name)
        return 0
    for entry in entries:
        print("%s  %s  %s" % (entry["commit"][:12], entry["date"], entry["subject"]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--rev", default=None, help="Git revision to query (default: working tree).")
    common.add_argument("--json", action="store_true", help="Machine-readable JSON output.")

    ap = argparse.ArgumentParser(
        description="Git-backed OSS knowledge fabric: provenance, repository, license, dependencies.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Build fingerprints from package-recipe records.", parents=[common])
    p_ingest.add_argument("dirs", nargs="*", help="Recipe directories (default: specs examples).")
    p_ingest.add_argument("--out", default=None, help="Output directory (default: fabric/packages).")
    p_ingest.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Parallel recipe workers (0 = auto, 1 = serial).",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_show = sub.add_parser("show", help="Print one fingerprint.", parents=[common])
    p_show.add_argument("name")
    p_show.set_defaults(func=cmd_show)

    p_deps = sub.add_parser("deps", help="Outbound dependencies.", parents=[common])
    p_deps.add_argument("name")
    p_deps.add_argument("--scope", choices=["runtime", "build", "host", "test"])
    p_deps.set_defaults(func=cmd_deps)

    p_rdeps = sub.add_parser("rdeps", help="Who depends on this package.", parents=[common])
    p_rdeps.add_argument("name")
    p_rdeps.add_argument("--scope", choices=["runtime", "build", "host", "test"])
    p_rdeps.set_defaults(func=cmd_rdeps)

    p_query = sub.add_parser("query", help="Filter fingerprints.", parents=[common])
    p_query.add_argument("--name")
    p_query.add_argument("--license")
    p_query.add_argument("--repo")
    p_query.add_argument("--ecosystem")
    p_query.add_argument("--has-repo", action="store_true")
    p_query.add_argument("--missing-repo", action="store_true")
    p_query.add_argument("--missing-license", action="store_true")
    p_query.set_defaults(func=cmd_query)

    p_stats = sub.add_parser("stats", help="Coverage of the committed fabric.", parents=[common])
    p_stats.set_defaults(func=cmd_stats)

    p_validate = sub.add_parser("validate", help="Validate committed fingerprints.", parents=[common])
    p_validate.set_defaults(func=cmd_validate)

    p_hist = sub.add_parser("history", help="Git log for a fingerprint (the database audit trail).", parents=[common])
    p_hist.add_argument("name")
    p_hist.set_defaults(func=cmd_history)

    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
