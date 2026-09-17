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


def _values_equal(observed, expected):
    left = resolve_typed(observed) if isinstance(observed, dict) and "type" in observed else observed
    right = resolve_typed(expected)
    if isinstance(left, tuple) and isinstance(right, list):
        left = list(left)
    if isinstance(right, tuple) and isinstance(left, list):
        right = list(right)
    return left == right


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


def probe_python(module_name, function, args, kwargs, method=None, method_args=None):
    """Import module_name and call function(*args, **kwargs). Never read source."""
    if "/" in module_name or module_name.endswith(".py") or module_name.endswith(".c"):
        raise ValueError("live probes take an import name, not a source path")
    mod = importlib.import_module(module_name)
    obj = mod
    for part in function.split("."):
        obj = getattr(obj, part)
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


def probe_node(module_name, function, args, kwargs):
    if kwargs:
        raise ValueError("node live probes do not accept kwargs in this spike")
    script = (
        "const m = require(process.argv[1]);\n"
        "const fn = process.argv[2].split('.').reduce((o,p)=>o[p], m);\n"
        "const args = JSON.parse(process.argv[3]);\n"
        "try {\n"
        "  const r = fn.apply(null, args);\n"
        "  process.stdout.write(JSON.stringify({ok:true, result:r}));\n"
        "} catch (e) {\n"
        "  process.stdout.write(JSON.stringify({ok:false, exc_type:e.name}));\n"
        "}\n"
    )
    proc = subprocess.run(
        ["node", "-e", script, module_name, function, json.dumps(args)],
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
        return {"ok": False, "exc_type": "NodeError", "error": proc.stdout[:300]}


def run_one(backend, module_name, function, args, kwargs, method=None, method_args=None):
    args = resolve_typed(args)
    kwargs = resolve_typed(kwargs or {})
    if backend in ("python_module", "python"):
        return probe_python(module_name, function, args, kwargs, method, method_args)
    if backend in ("node", "cli"):
        if method:
            raise ValueError("node live probes do not support method= in this spike")
        return probe_node(module_name, function, args, kwargs)
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
