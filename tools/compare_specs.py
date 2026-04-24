#!/usr/bin/env python3
"""
compare_specs.py — Compare two compiled Theseus behavioral specs.

Usage:
  python3 tools/compare_specs.py _build/zspecs/json.zspec.json _build/zspecs/simplejson.zspec.json
  python3 tools/compare_specs.py zspecs/hashlib.zspec.zsdl zspecs/_hashlib.zspec.zsdl
  python3 tools/compare_specs.py zspecs/json.zspec.zsdl zspecs/simplejson.zspec.json --json

If a .zspec.zsdl path is given the compiled .zspec.json is located in _build/zspecs/
automatically (it must already exist; run 'make compile-zsdl' first).
"""
import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BUILD_DIR = _REPO_ROOT / "_build" / "zspecs"


def _resolve_path(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    if path.suffix == ".zsdl":
        stem = path.stem  # e.g. "json.zspec"
        compiled = _BUILD_DIR / f"{stem}.json"
        if not compiled.exists():
            print(f"ERROR: compiled spec not found at {compiled}", file=sys.stderr)
            print("Run 'make compile-zsdl' first.", file=sys.stderr)
            sys.exit(1)
        return compiled
    return path


def _load(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: spec file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def _spec_name(spec: dict) -> str:
    return spec.get("identity", {}).get("canonical_name") or spec.get("spec", "?")


def _spec_backend(spec: dict) -> str:
    return spec.get("library", {}).get("backend") or spec.get("backend", "?")


def _inv_key(inv: dict) -> str:
    """Stable identity key for an invariant — prefer unique id field."""
    return inv.get("id") or str(inv)


def _inv_summary(inv: dict) -> str:
    """Human-readable one-liner for an invariant."""
    inv_id = inv.get("id", "")
    kind = inv.get("kind", "?")
    s = inv.get("spec", {})
    expected = s.get("expected", "") if isinstance(s, dict) else ""
    if expected != "":
        return f"{inv_id}  →  {str(expected)[:60]!r}  [{kind}]"
    return f"{inv_id}  [{kind}]"


def compare(spec_a: dict, spec_b: dict) -> dict:
    """Return a comparison dict between two specs."""
    inv_a = {_inv_key(i): i for i in spec_a.get("invariants", [])}
    inv_b = {_inv_key(i): i for i in spec_b.get("invariants", [])}

    keys_a = set(inv_a)
    keys_b = set(inv_b)

    common_keys = keys_a & keys_b
    only_a = keys_a - keys_b
    only_b = keys_b - keys_a

    behavioral_diffs = []
    for k in common_keys:
        ia = inv_a[k]
        ib = inv_b[k]
        sa = ia.get("spec", {}) if isinstance(ia.get("spec"), dict) else {}
        sb = ib.get("spec", {}) if isinstance(ib.get("spec"), dict) else {}
        exp_a = sa.get("expected")
        exp_b = sb.get("expected")
        if exp_a != exp_b and exp_a is not None and exp_b is not None:
            behavioral_diffs.append({
                "invariant_id": k,
                "expected_a": exp_a,
                "expected_b": exp_b,
            })

    name_a = _spec_name(spec_a)
    name_b = _spec_name(spec_b)

    return {
        "spec_a": {"name": name_a, "backend": _spec_backend(spec_a),
                   "invariant_count": len(inv_a)},
        "spec_b": {"name": name_b, "backend": _spec_backend(spec_b),
                   "invariant_count": len(inv_b)},
        "common_invariants": sorted(common_keys),
        "only_in_a": sorted([_inv_summary(inv_a[k]) for k in only_a]),
        "only_in_b": sorted([_inv_summary(inv_b[k]) for k in only_b]),
        "behavioral_differences": behavioral_diffs,
        "summary": {
            "common": len(common_keys),
            "only_in_a": len(only_a),
            "only_in_b": len(only_b),
            "behavioral_diffs": len(behavioral_diffs),
        },
    }


def _print_report(result: dict) -> None:
    a = result["spec_a"]
    b = result["spec_b"]
    s = result["summary"]

    print(f"Comparing specs:")
    print(f"  A: {a['name']}  (backend: {a['backend']}, {a['invariant_count']} invariants)")
    print(f"  B: {b['name']}  (backend: {b['backend']}, {b['invariant_count']} invariants)")
    print()
    print(f"Summary:")
    print(f"  Common invariants        : {s['common']}")
    print(f"  Only in A                : {s['only_in_a']}")
    print(f"  Only in B                : {s['only_in_b']}")
    print(f"  Behavioral differences   : {s['behavioral_diffs']}")

    if result["only_in_a"]:
        print(f"\nOnly in '{a['name']}':")
        for line in result["only_in_a"]:
            print(f"  {line}")

    if result["only_in_b"]:
        print(f"\nOnly in '{b['name']}':")
        for line in result["only_in_b"]:
            print(f"  {line}")

    if result["behavioral_differences"]:
        print(f"\nBehavioral differences (same invariant id, different expected value):")
        for d in result["behavioral_differences"]:
            print(f"  {d['invariant_id']}:")
            print(f"    A → {d['expected_a']!r}")
            print(f"    B → {d['expected_b']!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two Theseus behavioral specs")
    parser.add_argument("spec_a", help="First spec (.zspec.zsdl or .zspec.json)")
    parser.add_argument("spec_b", help="Second spec (.zspec.zsdl or .zspec.json)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    path_a = _resolve_path(args.spec_a)
    path_b = _resolve_path(args.spec_b)
    spec_a = _load(path_a)
    spec_b = _load(path_b)
    result = compare(spec_a, spec_b)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_report(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
