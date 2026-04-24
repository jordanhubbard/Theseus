#!/usr/bin/env python3
"""
search_specs.py — Search Theseus behavioral specs and clean-room registry.

Usage:
  python3 tools/search_specs.py json
  python3 tools/search_specs.py zlib --backend ctypes
  python3 tools/search_specs.py --backend python_cleanroom
  python3 tools/search_specs.py --verified
  python3 tools/search_specs.py --list
  python3 tools/search_specs.py json --json

Searches spec filenames and inline metadata (spec: name, docs:, backend:).
"""
import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ZSPECS_DIR = _REPO_ROOT / "zspecs"
_REGISTRY_PATH = _REPO_ROOT / "theseus_registry.json"
_CLEANROOM_PYTHON = _REPO_ROOT / "cleanroom" / "python"
_CLEANROOM_NODE = _REPO_ROOT / "cleanroom" / "node"


def _load_registry() -> dict:
    if not _REGISTRY_PATH.exists():
        return {"packages": {}}
    return json.loads(_REGISTRY_PATH.read_text())


def _sniff_spec(path: Path) -> dict:
    """Extract key fields from a .zspec.zsdl file without a full YAML parse."""
    text = path.read_text(errors="replace")
    result = {"file": str(path.relative_to(_REPO_ROOT)), "name": path.stem.replace(".zspec", "")}

    m = re.search(r"^spec:\s*(.+)$", text, re.MULTILINE)
    if m:
        result["name"] = m.group(1).strip()

    m = re.search(r"^backend:\s*(.+)$", text, re.MULTILINE)
    if m:
        raw = m.group(1).strip()
        result["backend_raw"] = raw
        m2 = re.match(r"(\w+)\(", raw)
        result["backend"] = m2.group(1) if m2 else raw

    m = re.search(r"^docs:\s*(.+)$", text, re.MULTILINE)
    if m:
        result["docs"] = m.group(1).strip()

    m = re.search(r"^version:\s*(.+)$", text, re.MULTILINE)
    if m:
        result["version"] = m.group(1).strip().strip('"')

    # Count invariants: explicit `function:` entries plus table rows (each table row
    # becomes one invariant when compiled; count non-header, non-empty rows in tables).
    fn_count = len(re.findall(r"^\s{2,}function:\s", text, re.MULTILINE))
    # Count table row lines: indented "- [..." patterns inside a `rows:` block
    row_count = len(re.findall(r"^\s{4,}-\s+\[", text, re.MULTILINE))
    result["invariant_count"] = fn_count + row_count

    return result


def search(
    query: str | None = None,
    backend: str | None = None,
    verified_only: bool = False,
) -> list[dict]:
    """Return matching spec entries as dicts."""
    registry = _load_registry()
    verified_names = {
        name for name, info in registry["packages"].items()
        if info.get("status") == "verified"
    }

    results = []
    for zsdl in sorted(_ZSPECS_DIR.glob("*.zspec.zsdl")):
        spec = _sniff_spec(zsdl)
        name = spec["name"]

        if query:
            needle = query.lower()
            hit = (
                needle in name.lower()
                or needle in zsdl.name.lower()
                or needle in spec.get("docs", "").lower()
                or needle in spec.get("backend_raw", "").lower()
            )
            if not hit:
                continue

        if backend:
            if spec.get("backend", "").lower() != backend.lower():
                continue

        if verified_only and name not in verified_names:
            continue

        spec["verified"] = name in verified_names
        if spec["verified"] and name in registry["packages"]:
            spec["cleanroom_path"] = registry["packages"][name].get("cleanroom_path", "")
        results.append(spec)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Theseus behavioral specs and registry")
    parser.add_argument("query", nargs="?", help="Name or keyword to search for")
    parser.add_argument("--backend", help="Filter by backend type (e.g. ctypes, python_cleanroom, python_module)")
    parser.add_argument("--verified", action="store_true", help="Only show verified clean-room packages")
    parser.add_argument("--list", action="store_true", help="List all specs (no query required)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if not args.query and not args.list and not args.backend and not args.verified:
        parser.print_help()
        return 2

    results = search(
        query=args.query,
        backend=args.backend,
        verified_only=args.verified,
    )

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    if not results:
        print("No matching specs found.")
        return 1

    fmt = "{verified:1}  {backend:<20}  {inv:>4} inv  {name}"
    header = "V  {:20}  {:>4}      {}".format("backend", "inv", "spec name")
    print(header)
    print("-" * len(header))
    for r in results:
        v = "✓" if r.get("verified") else " "
        b = r.get("backend", "?")
        print(fmt.format(
            verified=v,
            backend=b,
            inv=r.get("invariant_count", 0),
            name=r["name"],
        ))

    print(f"\n{len(results)} spec(s) found.  ✓ = verified clean-room implementation in registry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
