#!/usr/bin/env python3
"""
zsdl_compile.py — Compile *.zspec.zsdl (YAML) → *.zspec.json

Usage:
  python3 tools/zsdl_compile.py zspecs/difflib.zspec.zsdl
  python3 tools/zsdl_compile.py --all           # compile all .zsdl in zspecs/
  python3 tools/zsdl_compile.py --stdout FILE   # write compiled JSON to stdout
  python3 tools/zsdl_compile.py --check FILE    # compile but don't write (exit 1 on error)
"""

import argparse
import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Custom YAML tag types
# ---------------------------------------------------------------------------

class _Tagged:
    def __init__(self, value: Any): self.value = value
    def __repr__(self): return f"{type(self).__name__}({self.value!r})"

class B64Value(_Tagged): pass
class HexValue(_Tagged): pass
class AsciiValue(_Tagged): pass
class TupleValue(_Tagged): pass


def _make_loader():
    """Build a SafeLoader subclass with the four ZSDL custom tags."""
    loader = type("ZSDLLoader", (yaml.SafeLoader,), {})

    def _ctor(cls):
        return lambda ldr, node: cls(ldr.construct_scalar(node))

    loader.add_constructor("!b64",   _ctor(B64Value))
    loader.add_constructor("!hex",   _ctor(HexValue))
    loader.add_constructor("!ascii", _ctor(AsciiValue))
    loader.add_constructor(
        "!tuple",
        lambda ldr, node: TupleValue(ldr.construct_sequence(node)),
    )
    return loader


_LOADER = _make_loader()


# ---------------------------------------------------------------------------
# Value resolver  (ZSDL tag → JSON-spec typed dict)
# ---------------------------------------------------------------------------

def _resolve(v: Any) -> Any:
    """Convert a ZSDL value to JSON-serializable spec format.

    Tagged values become typed dicts.  Everything else passes through.
    """
    if isinstance(v, B64Value):
        return {"type": "bytes_b64", "value": v.value}
    if isinstance(v, HexValue):
        return {"type": "bytes_hex", "value": v.value}
    if isinstance(v, AsciiValue):
        return {"type": "bytes_ascii", "value": v.value}
    if isinstance(v, TupleValue):
        return {"type": "tuple", "value": [_resolve(x) for x in v.value]}
    if isinstance(v, list):
        return [_resolve(x) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(vv) for k, vv in v.items()}
    return v  # str, int, float, bool, None → pass through


# ---------------------------------------------------------------------------
# Call expression parser
# ---------------------------------------------------------------------------

def _is_pure_name(node: ast.expr) -> bool:
    """True if node is a bare name or dotted attribute chain with no calls."""
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Attribute):
        return _is_pure_name(node.value)
    return False


def _dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted_name(node.value)}.{node.attr}"
    raise ValueError(f"Expected name node, got {ast.dump(node)}")


def _ast_to_value(node: ast.expr) -> Any:
    """Convert an AST literal node to a plain Python value."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_ast_to_value(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_ast_to_value(k): _ast_to_value(v)
                for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Tuple):
        # YAML tuples need a typed dict; in a call expr we produce it
        return {"type": "tuple", "value": [_ast_to_value(e) for e in node.elts]}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_ast_to_value(node.operand)
    raise ValueError(f"Unsupported literal in call expression: {ast.dump(node)}")


def _call_parts(node: ast.Call) -> tuple[list, dict]:
    args = [_ast_to_value(a) for a in node.args]
    kwargs = {kw.arg: _ast_to_value(kw.value) for kw in node.keywords}
    return args, kwargs


def parse_call_expr(expr: str) -> dict:
    """Parse a Python call expression into a partial spec dict.

    Supports up to two chain levels:
        fn(args)                      → function, args
        fn(args).attr                 → function, args, method=attr
        fn(args).method(margs)        → function, args, method, method_args
        fn(args).method().attr        → function, args, method, method_chain
        fn(args).method(margs).attr   → function, args, method, method_args, method_chain
    """
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Cannot parse call expression {expr!r}: {e}") from e

    node = tree.body
    chain: list[tuple] = []  # collected (outermost first)

    # Peel chain layers from the outside in
    while True:
        if isinstance(node, ast.Call):
            if _is_pure_name(node.func):
                # Base call — done
                fn_name = _dotted_name(node.func)
                args, kwargs = _call_parts(node)
                base: dict = {"function": fn_name, "args": args}
                if kwargs:
                    base["kwargs"] = kwargs
                break
            if isinstance(node.func, ast.Attribute) and not _is_pure_name(node.func):
                # Chained method call: inner_expr.method(args)
                method_name = node.func.attr
                method_args, _ = _call_parts(node)
                chain.append(("call", method_name, method_args))
                node = node.func.value
                continue
            raise ValueError(f"Unexpected func in call: {ast.dump(node.func)}")

        if isinstance(node, ast.Attribute):
            chain.append(("attr", node.attr))
            node = node.value
            continue

        raise ValueError(f"Unexpected expression node: {type(node).__name__}")

    chain.reverse()  # now innermost first

    if len(chain) > 2:
        raise ValueError(
            f"Call expression chain depth {len(chain)} > 2: {expr!r}"
        )

    result = dict(base)

    for i, layer in enumerate(chain):
        if layer[0] == "call":
            _, method_name, method_args = layer
            if i == 0:
                result["method"] = method_name
                if method_args:
                    result["method_args"] = method_args
            else:
                # Depth-2 call — harness doesn't support args at chain level 2
                result["method_chain"] = method_name
        elif layer[0] == "attr":
            _, attr_name = layer
            if i == 0:
                result["method"] = attr_name
            else:
                result["method_chain"] = attr_name

    return result


# ---------------------------------------------------------------------------
# Section: top-level invariant / table field classification
# ---------------------------------------------------------------------------

# These keys (at the ZSDL invariant-block or table-row level) map to the
# top-level invariant JSON fields, not to the nested spec dict.
_INVARIANT_TOP_KEYS = frozenset({
    "description", "category", "rfc", "skip_if",
    # call-expression form
    "call", "eq", "raises",
    # kind is also top-level but handled separately
    "kind",
})


# ---------------------------------------------------------------------------
# ZSDLCompiler
# ---------------------------------------------------------------------------

class CompileError(Exception):
    pass


class ZSDLCompiler:

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def compile_file(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            raise CompileError(f"Cannot read {path}: {e}") from e
        try:
            doc = yaml.load(text, Loader=_LOADER)
        except yaml.YAMLError as e:
            raise CompileError(f"YAML parse error in {path}: {e}") from e
        if not isinstance(doc, dict):
            raise CompileError(f"{path}: top-level must be a YAML mapping")
        return self._compile(doc, path)

    # ------------------------------------------------------------------
    # Top-level compiler
    # ------------------------------------------------------------------

    def _compile(self, doc: dict, path: Path) -> dict:
        canonical_name = doc.get("spec")
        if not canonical_name:
            raise CompileError("Missing required field 'spec'")

        identity = self._compile_identity(doc)
        library  = self._compile_library(doc)
        prov     = self._compile_provenance(doc, canonical_name)
        consts   = self._compile_constants(doc.get("constants", {}))
        types_   = doc.get("types", {}) or {}
        wire     = self._compile_wire_formats(doc.get("wire_formats", {}))
        funcs    = self._compile_functions(doc.get("functions", {}))
        errmod   = self._compile_error_model(doc.get("error_model"))
        invs     = self._compile_all_invariants(doc, canonical_name)

        return {
            "schema_version": "0.1",
            "identity": identity,
            "provenance": prov,
            "library": library,
            "constants": consts,
            "types": types_,
            "wire_formats": wire,
            "functions": funcs,
            "invariants": invs,
            "error_model": errmod,
        }

    # ------------------------------------------------------------------
    # Header: identity
    # ------------------------------------------------------------------

    def _compile_identity(self, doc: dict) -> dict:
        canonical = doc["spec"]
        backend_str = doc.get("backend", "")

        # Determine default api_header from backend type
        if backend_str.startswith("python_module"):
            default_api_header = "N/A — Python stdlib"
        else:
            default_api_header = ""

        ident: dict = {
            "canonical_name": canonical,
            "spec_for_versions": doc.get("version", ">=0"),
            "api_header": doc.get("api_header", default_api_header),
        }

        docs_url = doc.get("docs")
        if docs_url:
            ident["public_docs_url"] = docs_url

        rfcs = doc.get("rfcs", [])
        if rfcs:
            ident["rfc_references"] = self._compile_rfcs(rfcs)

        return ident

    def _compile_rfcs(self, rfcs: list) -> list:
        out = []
        for item in rfcs:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str):
                # Try to parse "RFC XXXX — Title" or "RFC XXXX Title"
                m = re.match(r"(RFC\s*\S+)\s*[—–-]\s*(.*)", item, re.IGNORECASE)
                if m:
                    out.append({"rfc": m.group(1).strip(), "title": m.group(2).strip()})
                else:
                    out.append({"rfc": item, "title": ""})
        return out

    # ------------------------------------------------------------------
    # Header: library
    # ------------------------------------------------------------------

    def _compile_library(self, doc: dict) -> dict:
        backend_str = doc.get("backend", "")
        extra: dict = {}

        # Additional library-level fields from the header
        if "version_function" in doc:
            extra["version_function"] = doc["version_function"]
        if "min_version_prefix" in doc:
            extra["min_version_prefix"] = doc["min_version_prefix"]

        if backend_str.startswith("python_module(") and backend_str.endswith(")"):
            module_name = backend_str[len("python_module("):-1]
            return {
                "backend": "python_module",
                "module_name": module_name,
                "soname_patterns": [],
                **extra,
            }

        if backend_str.startswith("ctypes(") and backend_str.endswith(")"):
            lib_name = backend_str[len("ctypes("):-1]
            # Keep soname pattern as a list matching the original convention
            return {
                "soname_patterns": [lib_name],
                **extra,
            }

        if backend_str.startswith("cli(") and backend_str.endswith(")"):
            cmd = backend_str[len("cli("):-1]
            return {
                "backend": "cli",
                "command": cmd,
                "soname_patterns": [],
                **extra,
            }

        if backend_str.startswith("node(") and backend_str.endswith(")"):
            mod = backend_str[len("node("):-1]
            return {
                "backend": "cli",
                "command": "node",
                "module_name": mod,
                "soname_patterns": [],
                **extra,
            }

        # Fallback: ctypes with no known pattern
        return {"soname_patterns": [], **extra}

    # ------------------------------------------------------------------
    # Header: provenance
    # ------------------------------------------------------------------

    def _compile_provenance(self, doc: dict, canonical_name: str) -> dict:
        raw = doc.get("provenance")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        defaults: dict = {
            "spec_authors": ["Theseus Z-layer"],
            "created_at": now,
        }
        if raw is None:
            return defaults
        prov = dict(raw)
        prov.setdefault("spec_authors", ["Theseus Z-layer"])
        prov.setdefault("created_at", now)
        return prov

    # ------------------------------------------------------------------
    # Doc section: constants
    # ------------------------------------------------------------------

    def _compile_constants(self, raw) -> dict:
        if not raw:
            return {}
        out: dict = {}
        for category, items in raw.items():
            if isinstance(items, dict):
                arr = []
                for name, meta in items.items():
                    entry = {"name": name}
                    if isinstance(meta, dict):
                        entry.update(meta)
                    else:
                        entry["value"] = meta
                    arr.append(entry)
                out[category] = arr
            elif isinstance(items, list):
                out[category] = items  # already array form
            else:
                out[category] = items
        return out

    # ------------------------------------------------------------------
    # Doc section: functions
    # ------------------------------------------------------------------

    def _compile_functions(self, raw) -> dict:
        if not raw:
            return {}
        out: dict = {}
        for fn_name, fn_spec in raw.items():
            if not isinstance(fn_spec, dict):
                out[fn_name] = fn_spec
                continue
            fn_out: dict = {}
            for k, v in fn_spec.items():
                if k in ("params",):
                    # dict-of-dicts → array-of-objects
                    if isinstance(v, dict):
                        params = []
                        for pname, pmeta in v.items():
                            param = {"name": pname}
                            if isinstance(pmeta, dict):
                                param.update(pmeta)
                            params.append(param)
                        fn_out["parameters"] = params
                    else:
                        fn_out["parameters"] = v
                elif k == "returns":
                    fn_out["return_type"] = v
                elif k == "post":
                    fn_out["postconditions"] = v
                elif k == "pre":
                    fn_out["preconditions"] = v
                else:
                    fn_out[k] = v
            out[fn_name] = fn_out
        return out

    # ------------------------------------------------------------------
    # Doc section: wire_formats
    # ------------------------------------------------------------------

    def _compile_wire_formats(self, raw) -> dict:
        return raw if isinstance(raw, dict) else {}

    # ------------------------------------------------------------------
    # Doc section: error_model
    # ------------------------------------------------------------------

    def _compile_error_model(self, raw) -> dict:
        if raw is None or raw == {}:
            return {
                "return_code_semantics": "",
                "stream_error_field": "null",
                "error_stickiness": "N/A",
                "error_codes": [],
            }
        if raw == "python_exceptions":
            return {
                "return_code_semantics": (
                    "Python exceptions; raises on bad inputs; each call is stateless"
                ),
                "stream_error_field": "null",
                "error_stickiness": "N/A — each call is stateless",
                "error_codes": [],
            }
        if isinstance(raw, str):
            # Unknown shorthand — pass through
            return {"return_code_semantics": raw, "stream_error_field": "null",
                    "error_stickiness": "N/A", "error_codes": []}

        if not isinstance(raw, dict):
            return raw

        out: dict = {}
        codes_raw = raw.get("codes", {})
        if isinstance(codes_raw, dict):
            codes = []
            for name, meta in codes_raw.items():
                entry = {"name": name}
                if isinstance(meta, dict):
                    entry.update(meta)
                codes.append(entry)
        elif isinstance(codes_raw, list):
            codes = codes_raw
        else:
            codes = []

        out["return_code_semantics"] = raw.get("semantics", "")
        out["stream_error_field"]    = str(raw.get("stderr", "null"))
        out["error_stickiness"]      = raw.get("stickiness", "N/A")
        out["error_codes"]           = codes
        return out

    # ------------------------------------------------------------------
    # Invariants: dispatch over all invariant/table keys
    # ------------------------------------------------------------------

    def _compile_all_invariants(self, doc: dict, canonical_name: str) -> list:
        invs: list = []
        for key, value in doc.items():
            if key.startswith("invariant "):
                full_id = key[len("invariant "):].strip()
                invs.append(self._compile_invariant(full_id, value, canonical_name))
            elif key.startswith("table "):
                label = key[len("table "):].strip()
                invs.extend(self._compile_table(label, value, canonical_name))
        return invs

    # ------------------------------------------------------------------
    # Single invariant block
    # ------------------------------------------------------------------

    def _compile_invariant(self, full_id: str, block: dict, canonical_name: str) -> dict:
        if not isinstance(block, dict):
            raise CompileError(f"Invariant {full_id!r}: block must be a mapping")

        inv: dict = {"id": full_id}

        # Check for call-expression form
        if "call" in block:
            call_expr = block["call"]
            if "eq" not in block and "raises" not in block:
                raise CompileError(
                    f"Invariant {full_id!r}: 'call:' requires 'eq:' or 'raises:'"
                )
            kind = "python_call_eq" if "eq" in block else "python_call_raises"
            parsed = parse_call_expr(call_expr)
            spec_dict = _resolve(parsed)
            if "eq" in block:
                spec_dict["expected"] = _resolve(block["eq"])
            else:
                spec_dict["expected_exception"] = _resolve(block["raises"])
            inv["kind"] = kind
            if "description" in block:
                inv["description"] = block["description"]
            else:
                inv["description"] = f"{kind}: {full_id}"
            if "category" in block:
                inv["category"] = block["category"]
            if "rfc" in block:
                inv["rfc_reference"] = block["rfc"]
            if "skip_if" in block:
                inv["skip_if"] = block["skip_if"]
            inv["spec"] = spec_dict
            return inv

        # Structured form
        kind = block.get("kind")
        if not kind:
            raise CompileError(
                f"Invariant {full_id!r}: missing 'kind' (and no 'call:' expression)"
            )
        inv["kind"] = kind

        desc = block.get("description")
        inv["description"] = desc if desc else f"{kind}: {full_id}"
        if "category" in block:
            inv["category"] = block["category"]
        if "rfc" in block:
            inv["rfc_reference"] = block["rfc"]
        if "skip_if" in block:
            inv["skip_if"] = block["skip_if"]

        # Everything not a top-level invariant field → spec dict
        spec_dict: dict = {}
        for k, v in block.items():
            if k not in _INVARIANT_TOP_KEYS and k != "description":
                spec_dict[k] = _resolve(v)
        inv["spec"] = spec_dict
        return inv

    # ------------------------------------------------------------------
    # Table block → list of invariants
    # ------------------------------------------------------------------

    def _compile_table(self, label: str, tbl: dict, canonical_name: str) -> list:
        if not isinstance(tbl, dict):
            raise CompileError(f"Table {label!r}: must be a mapping")

        kind      = tbl.get("kind", "")
        category  = tbl.get("category", "")
        id_prefix = tbl.get("id_prefix")   # None means "absent" (use row id directly)
        id_from   = tbl.get("id_from")     # column name to use as row id
        describe  = tbl.get("describe")    # optional description template
        rfc_shared = tbl.get("rfc")

        columns: list = tbl.get("columns", [])
        rows: list    = tbl.get("rows", [])

        if not columns:
            raise CompileError(f"Table {label!r}: missing 'columns'")

        # Shared spec fields from the table header (everything not a table meta-key)
        _TABLE_META = frozenset({
            "kind", "category", "id_prefix", "id_from", "describe",
            "rfc", "columns", "rows",
            # Invariant-level fields that live in the table header but not in spec
            "skip_if",
        })
        shared_spec: dict = {}
        for k, v in tbl.items():
            if k not in _TABLE_META:
                shared_spec[k] = _resolve(v)

        invs: list = []
        for row in rows:
            if not isinstance(row, (list, tuple)):
                raise CompileError(f"Table {label!r}: each row must be a list")
            row = list(row)

            # Detect optional trailing override dict.
            # An override is present only when the row has one more element than
            # columns AND that extra element is a plain dict (not a tagged value).
            override: dict = {}
            if (len(row) == len(columns) + 1
                    and isinstance(row[-1], dict)
                    and not isinstance(row[-1], _Tagged)):
                override = row.pop()

            if len(row) != len(columns):
                raise CompileError(
                    f"Table {label!r}: row has {len(row)} values but {len(columns)} columns"
                )

            row_map = dict(zip(columns, row))

            # Determine row id
            if id_from:
                row_id = str(row_map[id_from])
            elif "id" in row_map:
                row_id = str(row_map["id"])
            else:
                raise CompileError(
                    f"Table {label!r}: no 'id' column and no 'id_from' specified"
                )

            # Build full invariant id
            if id_prefix:
                full_id = f"{canonical_name}.{id_prefix}.{row_id}"
            else:
                full_id = f"{canonical_name}.{row_id}"

            # Build description
            if describe:
                try:
                    description = describe.format(**row_map)
                except KeyError as e:
                    raise CompileError(
                        f"Table {label!r}: 'describe' template references unknown column {e}"
                    ) from e
            else:
                description = f"{kind}: {full_id}"

            # Per-row description override
            if "description" in row_map:
                description = str(row_map["description"])

            # Build spec dict: shared + per-row columns (excluding meta columns)
            _META_COLUMNS = frozenset({"id", "description", "rfc", "skip_if", "category"})
            spec_dict = dict(shared_spec)

            for col, val in row_map.items():
                if col in _META_COLUMNS:
                    continue
                # The special "id" column is only for ID generation, not a spec field.
                # But a column named by id_from IS a real spec field (e.g. "name" in constant_eq).
                if not id_from and col == "id":
                    continue

                resolved_val = _resolve(val)
                # null kwargs → don't add (or add as empty dict; we skip)
                if col == "kwargs" and resolved_val is None:
                    continue
                spec_dict[col] = resolved_val

            # Apply per-row overrides
            for k, v in override.items():
                # Overrides may be top-level or spec-level
                spec_dict[k] = _resolve(v)

            # Build invariant
            inv: dict = {
                "id": full_id,
                "description": description,
                "kind": kind,
                "spec": spec_dict,
            }
            if category:
                inv["category"] = category
            if "category" in row_map:
                inv["category"] = str(row_map["category"])
            if rfc_shared:
                inv["rfc_reference"] = rfc_shared
            if "rfc" in row_map:
                inv["rfc_reference"] = str(row_map["rfc"])
            if "skip_if" in row_map:
                inv["skip_if"] = str(row_map["skip_if"])
            if tbl.get("skip_if"):
                inv.setdefault("skip_if", tbl["skip_if"])

            invs.append(inv)

        return invs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

REPO_ROOT  = Path(__file__).resolve().parent.parent
BUILD_DIR  = REPO_ROOT / "_build" / "zspecs"


def _compile_one(path: Path, stdout_only: bool = False) -> bool:
    compiler = ZSDLCompiler()
    try:
        result = compiler.compile_file(path)
    except CompileError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False
    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    if stdout_only:
        print(json_str)
        return True
    # Output goes to _build/zspecs/ — never alongside the .zsdl source
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    stem = path.name  # e.g. hashlib.zspec.zsdl
    if stem.endswith(".zsdl"):
        stem = stem[:-5]  # strip .zsdl → hashlib.zspec
    out_path = BUILD_DIR / (stem if stem.endswith(".json") else stem + ".json")
    out_path.write_text(json_str + "\n", encoding="utf-8")
    print(f"  {path} → {out_path}  ({len(result['invariants'])} invariants)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile *.zspec.zsdl → _build/zspecs/*.zspec.json"
    )
    parser.add_argument("files", nargs="*", help="ZSDL file(s) to compile")
    parser.add_argument("--all", action="store_true",
                        help="Compile all .zsdl files in zspecs/")
    parser.add_argument("--stdout", action="store_true",
                        help="Write compiled JSON to stdout (single file only)")
    parser.add_argument("--check", action="store_true",
                        help="Compile without writing output (exit 1 on error)")
    args = parser.parse_args()

    if args.all:
        here = REPO_ROOT
        files = sorted(here.glob("zspecs/*.zspec.zsdl"))
        if not files:
            print("No .zspec.zsdl files found in zspecs/", file=sys.stderr)
            return 1
    else:
        files = [Path(f) for f in args.files]
        if not files:
            parser.print_help()
            return 2

    ok = True
    for path in files:
        if args.check:
            compiler = ZSDLCompiler()
            try:
                compiler.compile_file(path)
                print(f"OK: {path}")
            except CompileError as e:
                print(f"ERROR: {path}: {e}", file=sys.stderr)
                ok = False
        elif args.stdout:
            ok = _compile_one(path, stdout_only=True) and ok
        else:
            ok = _compile_one(path, stdout_only=False) and ok

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
