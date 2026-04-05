#!/usr/bin/env python3
"""
validate_zspec.py — Static schema validation for Z-layer behavioral spec files.

Validates every *.zspec.json file in _build/zspecs/ against
zspecs/schema/behavioral-spec.schema.json using jsonschema if available,
falling back to a minimal stdlib structural check otherwise.

Exit codes:
  0 — all specs valid
  1 — one or more specs failed validation
  2 — usage error / cannot read schema

Usage:
  python3 tools/validate_zspec.py [spec_file_or_dir ...]

  If no paths are given, defaults to _build/zspecs/ (run 'make compile-zsdl' first).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parent.parent
SCHEMA_PATH  = REPO_ROOT / "zspecs" / "schema" / "behavioral-spec.schema.json"
DEFAULT_GLOB = "_build/zspecs/*.zspec.json"

REQUIRED_TOP_LEVEL = [
    "schema_version",
    "identity",
    "provenance",
    "library",
    "constants",
    "types",
    "functions",
    "invariants",
    "wire_formats",
    "error_model",
]

REQUIRED_IDENTITY   = {"canonical_name", "spec_for_versions"}
REQUIRED_PROVENANCE = {"derived_from", "not_derived_from"}
REQUIRED_LIBRARY    = {"soname_patterns"}
REQUIRED_INVARIANT  = {"id", "description", "category", "kind", "spec"}
REQUIRED_ERROR      = {"return_code_semantics", "error_codes"}

# Kept in sync with KNOWN_KINDS in verify_behavior.py
KNOWN_KINDS = {
    "constant_eq", "call_eq", "call_returns", "version_prefix",
    "roundtrip", "wire_bytes", "error_on_bad_input", "incremental_eq_oneshot",
    "call_ge",
    "hash_known_vector", "hash_incremental", "hash_object_attr",
    "python_set_contains", "hash_digest_consistency", "hash_copy_independence",
    "hash_api_equivalence",
    "python_call_eq", "python_call_raises", "python_encode_decode_roundtrip",
    "python_struct_roundtrip", "python_sqlite_roundtrip",
    "cli_exits_with", "cli_stdout_eq", "cli_stdout_contains",
    "cli_stdout_matches", "cli_stderr_contains",
    "node_module_call_eq",
    "node_constructor_call_eq",
    "node_factory_call_eq",
    "lz4_roundtrip",
}


# ---------------------------------------------------------------------------
# Minimal stdlib fallback validator
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    pass


def _check_required(obj: dict, required: set[str], context: str) -> list[str]:
    missing = [k for k in sorted(required) if k not in obj]
    return [f"{context}: missing required field '{k}'" for k in missing]


def _stdlib_validate(spec: dict, path: Path) -> list[str]:
    """Return a list of error strings; empty list means valid."""
    errors: list[str] = []

    # Top-level required fields
    errors += _check_required(spec, set(REQUIRED_TOP_LEVEL), str(path.name))

    # identity
    if isinstance(spec.get("identity"), dict):
        errors += _check_required(spec["identity"], REQUIRED_IDENTITY, "identity")

    # provenance
    if isinstance(spec.get("provenance"), dict):
        errors += _check_required(spec["provenance"], REQUIRED_PROVENANCE, "provenance")
        for field in ("derived_from", "not_derived_from"):
            val = spec["provenance"].get(field)
            if val is not None and not isinstance(val, list):
                errors.append(f"provenance.{field}: must be an array")

    # library
    if isinstance(spec.get("library"), dict):
        errors += _check_required(spec["library"], REQUIRED_LIBRARY, "library")

    # invariants
    invariants = spec.get("invariants")
    if invariants is not None:
        if not isinstance(invariants, list):
            errors.append("invariants: must be an array")
        else:
            seen_ids: set[str] = set()
            for i, inv in enumerate(invariants):
                ctx = f"invariants[{i}]"
                if not isinstance(inv, dict):
                    errors.append(f"{ctx}: must be an object")
                    continue
                errors += _check_required(inv, REQUIRED_INVARIANT, ctx)
                inv_id = inv.get("id", f"<index {i}>")
                if inv_id in seen_ids:
                    errors.append(f"{ctx}: duplicate id '{inv_id}'")
                seen_ids.add(inv_id)
                kind = inv.get("kind")
                if kind is not None and kind not in KNOWN_KINDS:
                    errors.append(
                        f"{ctx} (id={inv_id!r}): unknown kind '{kind}' "
                        f"(known: {', '.join(sorted(KNOWN_KINDS))})"
                    )

    # error_model
    if isinstance(spec.get("error_model"), dict):
        errors += _check_required(spec["error_model"], REQUIRED_ERROR, "error_model")

    # Programmatic cross-field check: arg_types length must match args length
    errors += _check_arg_types_length(spec)

    return errors


def _check_arg_types_length(spec: dict) -> list[str]:
    """Return errors for any invariant where len(arg_types) != len(args)."""
    errors: list[str] = []
    invariants = spec.get("invariants")
    if not isinstance(invariants, list):
        return errors
    for i, inv in enumerate(invariants):
        if not isinstance(inv, dict):
            continue
        spec_block = inv.get("spec")
        if not isinstance(spec_block, dict):
            continue
        args = spec_block.get("args")
        arg_types = spec_block.get("arg_types")
        if args is None or arg_types is None:
            continue
        if not isinstance(args, list) or not isinstance(arg_types, list):
            continue
        if len(args) != len(arg_types):
            inv_id = inv.get("id", f"<index {i}>")
            errors.append(
                f"invariants[{i}] (id={inv_id!r}): "
                f"arg_types length ({len(arg_types)}) does not match "
                f"args length ({len(args)})"
            )
    return errors


# ---------------------------------------------------------------------------
# jsonschema validator (used when the package is available)
# ---------------------------------------------------------------------------

def _jsonschema_validate(spec: dict, schema: dict, path: Path) -> list[str]:
    import jsonschema  # type: ignore
    errors: list[str] = []
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{location}: {err.message}")
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_schema() -> dict | None:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except OSError as e:
        print(f"ERROR: cannot read schema at {SCHEMA_PATH}: {e}", file=sys.stderr)
        return None


def collect_specs(paths: list[str]) -> list[Path]:
    result: list[Path] = []
    if not paths:
        result.extend(sorted(REPO_ROOT.glob(DEFAULT_GLOB)))
    else:
        for p in paths:
            fp = Path(p)
            if fp.is_dir():
                result.extend(sorted(fp.glob("*.zspec.json")))
            elif fp.is_file():
                result.append(fp)
            else:
                print(f"WARNING: {p} does not exist, skipping", file=sys.stderr)
    return result


def validate_file(path: Path, schema: dict | None, use_jsonschema: bool) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"cannot read file: {e}"]
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    if not isinstance(spec, dict):
        return ["top-level value must be a JSON object"]

    if use_jsonschema and schema is not None:
        errors = _jsonschema_validate(spec, schema, path)
        errors += _check_arg_types_length(spec)
        return errors
    return _stdlib_validate(spec, path)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    schema = load_schema()
    if schema is None:
        return 2

    try:
        import jsonschema  # noqa: F401
        use_jsonschema = True
    except ImportError:
        use_jsonschema = False

    specs = collect_specs(argv)
    if not specs:
        print("No spec files found.", file=sys.stderr)
        return 2

    failed = 0
    for path in specs:
        errors = validate_file(path, schema, use_jsonschema)
        rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        if errors:
            failed += 1
            print(f"FAIL  {rel}")
            for err in errors:
                print(f"      {err}")
        else:
            print(f"OK    {rel}")

    backend = "jsonschema" if use_jsonschema else "stdlib"
    total = len(specs)
    print(
        f"\n{total} spec(s) validated ({backend}): "
        f"{total - failed} OK, {failed} failed"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
