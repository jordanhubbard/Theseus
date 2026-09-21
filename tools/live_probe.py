#!/usr/bin/env python3
"""
live_probe.py — Call an installed library's public API. Do not read its source.

Usage:
  python3 tools/live_probe.py --module json --function dumps --args '[42]'
  python3 tools/live_probe.py --from gold/json/probes.yaml
  python3 tools/live_probe.py --from gold/json/probes.yaml --json

Probes are characterization evidence (ADR 0003). They import the installed
module as a black box. They never open the module's __file__.
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools"))

try:
    import yaml
except ImportError:
    yaml = None


def resolve_typed(value):
    """Same typed-value tags as verify_behavior / ZSDL (tuple, bytes_*, null)."""
    if isinstance(value, dict) and "type" in value:
        kind = value.get("type")
        inner = value.get("value")
        if kind == "tuple":
            return tuple(resolve_typed(x) for x in (inner or []))
        if kind == "null":
            return None
        if kind == "bytes_b64":
            import base64
            return base64.b64decode(inner) if inner else b""
        if kind == "bytes_ascii":
            return (inner or "").encode("ascii")
        if kind == "bytes_hex":
            return bytes.fromhex(inner) if inner else b""
        return inner
    if isinstance(value, list):
        return [resolve_typed(x) for x in value]
    if isinstance(value, dict):
        return {k: resolve_typed(v) for k, v in value.items()}
    return value


def _encode_observed(value):
    if isinstance(value, bytes):
        return {"type": "bytes_hex", "value": value.hex()}
    if isinstance(value, tuple):
        return {"type": "tuple", "value": [_encode_observed(x) for x in value]}
    if isinstance(value, list):
        return [_encode_observed(x) for x in value]
    if isinstance(value, dict):
        return {k: _encode_observed(v) for k, v in value.items()}
    return value


_ENCODED_TYPES = frozenset({"tuple", "bytes_hex", "bytes_ascii", "bytes_b64", "null"})


def _as_data(value):
    """Compare tuples, lists, and encoded receipts as plain data."""
    if isinstance(value, dict) and set(value) <= {"type", "value"} and value.get("type") in _ENCODED_TYPES:
        return _as_data(resolve_typed(value))
    if isinstance(value, tuple):
        return [_as_data(item) for item in value]
    if isinstance(value, list):
        return [_as_data(item) for item in value]
    if isinstance(value, dict):
        return {key: _as_data(item) for key, item in value.items()}
    return value


def _values_equal(observed, expected):
    return _as_data(observed) == _as_data(resolve_typed(expected))


def _apply_method(value, method, method_args):
    """Read a property or call a method on a live return value. No source reads."""
    if not method:
        return value
    obj = value
    for part in method.split("."):
        obj = getattr(obj, part)
    if callable(obj):
        return obj(*resolve_typed(method_args or []))
    return obj


def _walk_public(mod, function):
    """Walk a dotted public name, importing a submodule when it is not an attribute."""
    obj = mod
    module_name = mod.__name__
    for part in function.split("."):
        found = getattr(obj, part, None)
        if found is None and isinstance(obj, types.ModuleType):
            try:
                found = importlib.import_module(module_name + "." + part)
            except ImportError:
                found = None
        if found is None:
            raise AttributeError(function)
        obj = found
        if isinstance(obj, types.ModuleType):
            module_name = obj.__name__
    return obj


def probe_python(module_name, function, args, kwargs, method=None, method_args=None):
    """Import module_name and call function(*args, **kwargs). Never read source."""
    if "/" in module_name or module_name.endswith(".py") or module_name.endswith(".c"):
        raise ValueError("live probes take an import name, not a source path")
    mod = importlib.import_module(module_name)
    obj = _walk_public(mod, function)
    origin = getattr(mod, "__file__", None)
    # Touching origin is allowed only as a path string in the receipt, not contents.
    try:
        result = obj(*args, **kwargs)
        result = _apply_method(result, method, method_args)
    except Exception as exc:
        return {
            "ok": False,
            "exc_type": type(exc).__name__,
            "exc_module": type(exc).__module__,
            "module_file": origin,
        }
    return {"ok": True, "result": _encode_observed(result), "module_file": origin}


def probe_node(module_name, function, args, kwargs, method=None, method_args=None):
    if kwargs:
        raise ValueError("node live probes do not accept kwargs in this spike")
    # CJS require first; ESM dynamic import() fallback. Optional method hop
    # (including method: call) matches python live probes for factories.
    # function "bare" uses the module object itself (ZSDL entry: bare).
    script = (
        "const modName = process.argv[1];\n"
        "const fnPath = process.argv[2];\n"
        "const args = JSON.parse(process.argv[3]);\n"
        "const method = process.argv[4];\n"
        "const methodArgs = JSON.parse(process.argv[5]);\n"
        "function walk(obj, path) {\n"
        "  if (!path || path === '~') return obj;\n"
        "  let o = obj;\n"
        "  for (const p of path.split('.')) {\n"
        "    if (o && o[p] !== undefined) { o = o[p]; continue; }\n"
        "    if (o && o.default && o.default[p] !== undefined) { o = o.default[p]; continue; }\n"
        "    return undefined;\n"
        "  }\n"
        "  return o;\n"
        "}\n"
        "function resolveFn(m) {\n"
        "  if (fnPath === 'bare') return m;\n"
        "  if (!fnPath || fnPath === '~' || fnPath === 'default') {\n"
        "    if (typeof m === 'function') return m;\n"
        "    if (m && typeof m.default === 'function') return m.default;\n"
        "    return m && m.default !== undefined ? m.default : m;\n"
        "  }\n"
        "  const found = walk(m, fnPath);\n"
        "  if (found !== undefined) return found;\n"
        "  if (m && m.default) return walk(m.default, fnPath);\n"
        "  return found;\n"
        "}\n"
        "function applyMethod(r) {\n"
        "  if (!method) return r;\n"
        "  if (method === 'call') return r.apply(null, methodArgs);\n"
        "  let o = r;\n"
        "  for (const p of method.split('.')) o = o[p];\n"
        "  if (typeof o === 'function') return o.apply(r, methodArgs);\n"
        "  return o;\n"
        "}\n"
        "function invoke(fn) {\n"
        "  if (fnPath === 'bare') return applyMethod(fn);\n"
        "  try { return applyMethod(fn.apply(null, args)); }\n"
        "  catch (e) {\n"
        "    if (e instanceof TypeError) return applyMethod(new fn(...args));\n"
        "    throw e;\n"
        "  }\n"
        "}\n"
        "(async () => {\n"
        "  let m;\n"
        "  try { m = require(modName); }\n"
        "  catch (e) { m = await import(modName); }\n"
        "  try {\n"
        "    const r = invoke(resolveFn(m));\n"
        "    process.stdout.write(JSON.stringify({ok:true, result:r}));\n"
        "  } catch (e) {\n"
        "    process.stdout.write(JSON.stringify({ok:false, exc_type:e.name, error:String(e.message||e).slice(0,200)}));\n"
        "  }\n"
        "})().catch((e) => {\n"
        "  process.stdout.write(JSON.stringify({ok:false, exc_type:'NodeError', error:String(e).slice(0,200)}));\n"
        "});\n"
    )
    proc = subprocess.run(
        [
            "node", "-e", script,
            module_name,
            function or "",
            json.dumps(args),
            method or "",
            json.dumps(method_args or []),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "node probe failed").strip()
        return {"ok": False, "exc_type": "NodeError", "error": err[:300]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "exc_type": "NodeError", "error": (proc.stdout or proc.stderr or "")[:300]}


def run_one(backend, module_name, function, args, kwargs, method=None, method_args=None):
    args = resolve_typed(args)
    kwargs = resolve_typed(kwargs or {})
    if backend in ("python_module", "python"):
        return probe_python(module_name, function, args, kwargs, method, method_args)
    if backend in ("node", "cli"):
        return probe_node(module_name, function, args, kwargs, method, method_args)
    raise ValueError("unsupported probe backend: {}".format(backend))


def load_probe_file(path):
    if yaml is None:
        raise RuntimeError("pyyaml is required to load probe files")
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("{}: top-level must be a mapping".format(path))
    return doc


def check_expect(observed, expect):
    if not expect:
        return True, "no expect"
    if "raises" in expect:
        want = expect["raises"]
        if observed.get("ok"):
            return False, "did not raise {}".format(want)
        got = observed.get("exc_type") or ""
        if got == want or got.endswith(want) or want.endswith(got):
            return True, "raised {}".format(got)
        return False, "raised {}, expected {}".format(got, want)
    if "eq" in expect:
        if not observed.get("ok"):
            return False, "raised {} instead of returning".format(observed.get("exc_type"))
        if _values_equal(observed.get("result"), expect["eq"]):
            return True, "eq"
        return False, "got {!r}, expected {!r}".format(observed.get("result"), expect["eq"])
    if "contains" in expect:
        if not observed.get("ok"):
            return False, "raised {} instead of returning".format(observed.get("exc_type"))
        result = observed.get("result")
        want = expect["contains"]
        if not isinstance(result, dict) or not isinstance(want, dict):
            return False, "contains expects a mapping result, got {!r}".format(result)
        for key, value in want.items():
            if not _values_equal(result.get(key), value):
                return False, "key {} got {!r}, expected {!r}".format(
                    key, result.get(key), value
                )
        return True, "contains"
    return True, "no expect"


def run_file(path):
    doc = load_probe_file(path)
    backend = doc.get("backend") or "python_module"
    module_name = doc.get("module")
    rows = []
    failed = 0
    for probe in doc.get("probes") or []:
        observed = run_one(
            backend,
            module_name,
            probe["function"],
            probe.get("args") or [],
            probe.get("kwargs") or {},
            probe.get("method"),
            probe.get("method_args") or [],
        )
        ok, msg = check_expect(observed, probe.get("expect") or {})
        row = {
            "id": probe.get("id") or probe["function"],
            "passed": ok,
            "message": msg,
            "observed": observed,
        }
        rows.append(row)
        if not ok:
            failed += 1
    return {
        "family": doc.get("family"),
        "backend": backend,
        "module": module_name,
        "pass": len(rows) - failed,
        "fail": failed,
        "probes": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Live-probe an installed public API (no source reads)")
    parser.add_argument("--from", dest="probe_file", type=Path)
    parser.add_argument("--module")
    parser.add_argument("--function")
    parser.add_argument("--args", default="[]")
    parser.add_argument("--kwargs", default="{}")
    parser.add_argument("--backend", default="python_module")
    parser.add_argument("--method")
    parser.add_argument("--method-args", default="[]")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.probe_file:
        result = run_file(args.probe_file)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("{}/{} probes passed ({})".format(
                result["pass"], result["pass"] + result["fail"], args.probe_file
            ))
            for row in result["probes"]:
                flag = "PASS" if row["passed"] else "FAIL"
                print("  {}  {}  {}".format(flag, row["id"], row["message"]))
        return 0 if result["fail"] == 0 else 1

    if not args.module or not args.function:
        parser.error("provide --from FILE or --module and --function")
    observed = run_one(
        args.backend,
        args.module,
        args.function,
        json.loads(args.args),
        json.loads(args.kwargs),
        args.method,
        json.loads(args.method_args),
    )
    print(json.dumps(observed, indent=2))
    return 0 if observed.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
