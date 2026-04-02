#!/usr/bin/env python3
"""
validate_record.py

Validate canonical package recipe records against the schema rules.
Prints structured error messages. Exits non-zero if any record is invalid.

Usage:
    python3 tools/validate_record.py record.json [record.json ...]
    python3 tools/validate_record.py snapshot_dir/
    python3 tools/validate_record.py --strict examples/

Options:
    --strict    Also report warnings and non-empty unmapped/warnings fields.
    --quiet     Suppress OK lines; only print issues.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Schema rules (derived from schema/package-recipe.schema.json)
# ---------------------------------------------------------------------------

REQUIRED_TOP = [
    "schema_version", "identity", "descriptive", "sources",
    "dependencies", "build", "features", "platforms", "conflicts",
    "patches", "tests", "provenance", "extensions",
]

REQUIRED_IDENTITY = [
    "canonical_name", "canonical_id", "version", "ecosystem", "ecosystem_id",
]

REQUIRED_DEPS = ["build", "host", "runtime", "test"]

KNOWN_ECOSYSTEMS = {"nixpkgs", "freebsd_ports"}

KNOWN_BUILD_SYSTEMS = {
    "autotools", "cmake", "meson", "waf", "perl", "python", "go",
    "cargo", "freebsd_ports_make", "nix_derivation", "unknown",
}

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_record(rec: dict, filename: str, strict: bool = False) -> list[str]:
    """
    Validate a single canonical record dict.
    Returns a list of issue strings (empty list = valid).
    Each string is prefixed with ERROR or WARN.
    """
    issues: list[str] = []

    def e(field: str, msg: str) -> None:
        issues.append(f"  ERROR  {filename}:{field}: {msg}")

    def w(field: str, msg: str) -> None:
        issues.append(f"  WARN   {filename}:{field}: {msg}")

    # top-level required fields
    for field in REQUIRED_TOP:
        if field not in rec:
            e(field, "required field missing")

    sv = rec.get("schema_version")
    if not isinstance(sv, str) or not sv:
        e("schema_version", "must be a non-empty string")

    # identity
    identity = rec.get("identity", {})
    if not isinstance(identity, dict):
        e("identity", "must be an object")
    else:
        for field in REQUIRED_IDENTITY:
            if not identity.get(field):
                e(f"identity.{field}", "required and must be non-empty")
        eco = identity.get("ecosystem", "")
        if eco and eco not in KNOWN_ECOSYSTEMS:
            w("identity.ecosystem", f"unknown ecosystem '{eco}' (known: {sorted(KNOWN_ECOSYSTEMS)})")

    # descriptive
    desc = rec.get("descriptive", {})
    if not isinstance(desc, dict):
        e("descriptive", "must be an object")
    else:
        for arr_field in ("license", "categories", "maintainers"):
            if arr_field in desc and not isinstance(desc[arr_field], list):
                e(f"descriptive.{arr_field}", "must be an array")
        if "deprecated" in desc and not isinstance(desc["deprecated"], bool):
            e("descriptive.deprecated", "must be a boolean")
        if "expiration_date" in desc and not isinstance(desc["expiration_date"], str):
            e("descriptive.expiration_date", "must be a string")
        if strict and not desc.get("summary"):
            w("descriptive.summary", "empty — consider adding a description")
        if strict and not desc.get("homepage"):
            w("descriptive.homepage", "empty — consider adding a homepage URL")

    # conflicts
    conflicts = rec.get("conflicts", [])
    if not isinstance(conflicts, list):
        e("conflicts", "must be an array")
    else:
        for i, c in enumerate(conflicts):
            if not isinstance(c, str):
                e(f"conflicts[{i}]", f"must be a string, got {type(c).__name__}")

    # sources
    sources = rec.get("sources", [])
    if not isinstance(sources, list):
        e("sources", "must be an array")
    else:
        for i, src in enumerate(sources):
            if not isinstance(src, dict):
                e(f"sources[{i}]", "must be an object")
            elif "type" not in src:
                e(f"sources[{i}]", "missing required field 'type'")

    # dependencies
    deps = rec.get("dependencies", {})
    if not isinstance(deps, dict):
        e("dependencies", "must be an object")
    else:
        for key in REQUIRED_DEPS:
            if key not in deps:
                e(f"dependencies.{key}", "required field missing")
            elif not isinstance(deps[key], list):
                e(f"dependencies.{key}", "must be an array")
            else:
                for i, dep in enumerate(deps[key]):
                    if not isinstance(dep, str):
                        e(f"dependencies.{key}[{i}]", f"must be a string, got {type(dep).__name__}")

    # build
    build = rec.get("build", {})
    if not isinstance(build, dict):
        e("build", "must be an object")
    else:
        bk = build.get("system_kind", "")
        if bk and bk not in KNOWN_BUILD_SYSTEMS:
            w("build.system_kind", f"unknown value '{bk}' (known: {sorted(KNOWN_BUILD_SYSTEMS)})")

    # patches
    patches = rec.get("patches", [])
    if not isinstance(patches, list):
        e("patches", "must be an array")
    else:
        for i, p in enumerate(patches):
            if not isinstance(p, dict):
                e(f"patches[{i}]", "must be an object")
            elif "path" not in p:
                e(f"patches[{i}]", "missing required field 'path'")

    # provenance
    prov = rec.get("provenance", {})
    if not isinstance(prov, dict):
        e("provenance", "must be an object")
    else:
        conf = prov.get("confidence")
        if conf is not None:
            if not isinstance(conf, (int, float)):
                e("provenance.confidence", "must be a number")
            elif not (0.0 <= float(conf) <= 1.0):
                e("provenance.confidence", f"out of range [0, 1]: {conf}")
        if not isinstance(prov.get("unmapped", []), list):
            e("provenance.unmapped", "must be an array")
        if not isinstance(prov.get("warnings", []), list):
            e("provenance.warnings", "must be an array")
        if strict and prov.get("unmapped"):
            w("provenance.unmapped",
              f"{len(prov['unmapped'])} unmapped field(s): {prov['unmapped']}")
        if strict and prov.get("warnings"):
            w("provenance.warnings",
              f"{len(prov['warnings'])} warning(s): {prov['warnings']}")

    # platforms
    platforms = rec.get("platforms", {})
    if not isinstance(platforms, dict):
        e("platforms", "must be an object")
    else:
        for key in ("include", "exclude"):
            if key in platforms and not isinstance(platforms[key], list):
                e(f"platforms.{key}", "must be an array")

    # object-typed fields
    for field in ("features", "extensions", "tests"):
        val = rec.get(field)
        if val is not None and not isinstance(val, dict):
            e(field, "must be an object")

    # behavioral_spec — optional; when present, run verify_behavior and report failures
    bspec = rec.get("behavioral_spec")
    if bspec is not None:
        if not isinstance(bspec, str):
            e("behavioral_spec", "must be a string path to a .zspec.json file")
        else:
            bspec_path = REPO_ROOT / bspec
            if not bspec_path.exists():
                e("behavioral_spec", f"file not found: {bspec_path}")
            else:
                issues += _run_behavioral_spec(bspec_path, filename)

    return issues


def _run_behavioral_spec(spec_path: Path, record_name: str) -> list[str]:
    """
    Load and run verify_behavior against spec_path.
    Returns a list of ERROR strings for any invariants that fail or if the
    library cannot be loaded (treated as a WARN — the library may not be
    installed on the validating machine).
    """
    vb_path = REPO_ROOT / "tools" / "verify_behavior.py"
    spec = importlib.util.spec_from_file_location("verify_behavior", vb_path)
    vb = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(vb)  # type: ignore[union-attr]

    try:
        zspec = vb.SpecLoader().load(spec_path)
        lib   = vb.LibraryLoader().load(zspec["library"])
    except vb.LibraryNotFoundError as exc:
        return [f"  WARN   {record_name}:behavioral_spec: library not available — {exc}"]
    except Exception as exc:
        return [f"  ERROR  {record_name}:behavioral_spec: failed to load spec — {exc}"]

    runner  = vb.InvariantRunner()
    results = runner.run_all(zspec, lib)
    failed  = [r for r in results if not r.passed and not r.skip_reason]
    if not failed:
        return []
    lines = [f"  ERROR  {record_name}:behavioral_spec: {len(failed)} invariant(s) failed:"]
    for r in failed:
        lines.append(f"           FAIL  {r.inv_id}: {r.message}")
    return lines


# ---------------------------------------------------------------------------
# File/directory dispatch
# ---------------------------------------------------------------------------


def validate_paths(paths: list[Path], strict: bool, quiet: bool) -> tuple[int, int]:
    """
    Validate all records at the given paths.
    Returns (invalid_count, total_count).
    """
    invalid = 0
    total = 0

    for path in paths:
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(
                p for p in path.rglob("*.json")
                if p.name != "manifest.json"
            )
        else:
            print(f"Error: path not found: {path}", file=sys.stderr)
            invalid += 1
            continue

        for candidate in candidates:
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"\n{candidate}")
                print(f"  ERROR  {candidate.name}: invalid JSON — {exc}")
                invalid += 1
                total += 1
                continue

            if not isinstance(data, dict) or "identity" not in data:
                continue  # non-record file, skip silently

            total += 1
            issues = validate_record(data, candidate.name, strict=strict)
            errors = [i for i in issues if "ERROR" in i]
            if errors or issues:
                invalid += 1
                print(f"\n{candidate}")
                for issue in issues:
                    print(issue)
            elif not quiet:
                print(f"  OK     {candidate.name}")

    return (invalid, total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Validate canonical package recipe records against schema rules."
    )
    ap.add_argument("paths", nargs="+", type=Path, metavar="PATH",
                    help="JSON record file(s) or snapshot directory/ies")
    ap.add_argument("--strict", action="store_true",
                    help="Also flag warnings and non-empty unmapped/warnings fields")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress OK lines; only print issues")
    args = ap.parse_args()

    invalid, total = validate_paths(args.paths, strict=args.strict, quiet=args.quiet)
    print(f"\n{total} record(s) checked — {total - invalid} OK, {invalid} invalid.")

    if invalid > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
