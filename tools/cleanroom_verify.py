#!/usr/bin/env python3
"""
cleanroom_verify.py — Verify a clean-room implementation satisfies all spec invariants in isolation.

The original package is actively blocked via THESEUS_BLOCKED_PACKAGE during
every invariant check. Any import of the original package causes an immediate
isolation violation failure.

Usage:
  python3 tools/cleanroom_verify.py _build/zspecs/theseus_json.zspec.json
  python3 tools/cleanroom_verify.py _build/zspecs/theseus_json.zspec.json --verbose
"""
import argparse
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import sysconfig
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLEANROOM_PYTHON = _REPO_ROOT / "cleanroom" / "python"
_CLEANROOM_NODE = _REPO_ROOT / "cleanroom" / "node"
_REGISTRY_PATH = _REPO_ROOT / "theseus_registry.json"

_PY_IMPL_BACKDOORS = {
    "ast": {"_ast"},
    "bisect": {"_bisect"},
    "bz2": {"_bz2"},
    "collections": {"_collections", "_collections_abc"},
    "csv": {"_csv"},
    "ctypes": {"_ctypes"},
    "decimal": {"_decimal"},
    "elementtree": {"_elementtree"},
    "hashlib": {"_hashlib", "_blake2", "_md5", "_sha1", "_sha2", "_sha3"},
    "heapq": {"_heapq"},
    "io": {"_io"},
    "lzma": {"_lzma"},
    "pickle": {"_pickle"},
    "socket": {"_socket"},
    "sqlite3": {"_sqlite3"},
    "ssl": {"_ssl"},
    "struct": {"_struct"},
    "zstd": {"_zstd"},
}


def verify(spec_path: str, verbose: bool = False) -> dict:
    spec = json.loads(Path(spec_path).read_text())
    name = spec["identity"]["canonical_name"]
    lang = spec.get("backend_lang", "")

    if lang == "python_cleanroom":
        return _verify_python(spec, name, verbose)
    elif lang == "node_cleanroom":
        return _verify_node(spec, name, verbose)
    else:
        return {"error": f"Not a cleanroom spec (backend_lang={lang!r})", "pass": 0, "fail": 0, "errors": []}


def _get_blocked_package(spec: dict, name: str) -> str:
    """
    Determine which original package to block during verification.

    Checks (in order):
    1. spec["blocks"] field set explicitly in the ZSDL
    2. Strip "theseus_" prefix from the spec name (theseus_json → json)
    3. Fall back to the spec name itself
    """
    if "blocks" in spec:
        return spec["blocks"]
    if name.startswith("theseus_"):
        return name[len("theseus_"):]
    return name


def _verify_python(spec: dict, name: str, verbose: bool) -> dict:
    impl_dir = _CLEANROOM_PYTHON / name
    if not (impl_dir / "__init__.py").exists():
        return {
            "pass": 0,
            "fail": len(spec["invariants"]),
            "errors": [{"invariant": "ALL", "error": f"No implementation found at {impl_dir}/__init__.py"}],
        }

    blocked = _get_blocked_package(spec, name)
    policy_errors = _python_policy_errors(impl_dir, blocked)
    if policy_errors:
        return {
            "pass": 0,
            "fail": len(spec["invariants"]),
            "errors": [
                {"invariant": "POLICY", "error": err}
                for err in policy_errors
            ],
        }

    env = {
        **os.environ,
        "PYTHONPATH": str(_CLEANROOM_PYTHON),
        "PYTHONNOUSERSITE": "1",
        "THESEUS_BLOCKED_PACKAGE": blocked,
    }

    passed, failed, errors = 0, 0, []
    for inv in spec["invariants"]:
        inv_id = inv["id"]
        spec_dict = inv.get("spec", {})
        fn = spec_dict.get("function", "")
        args = spec_dict.get("args", [])
        expected = spec_dict.get("expected")

        # Use repr() so the test harness doesn't need to import json
        # (json may be the blocked package). ast.literal_eval is stdlib and safe.
        args_repr = repr(args)
        expected_repr = repr(expected)

        # When ast itself is blocked, fall back to eval() for simple literals.
        if blocked == "ast":
            lit_eval_import = ""
            lit_eval_fn = "eval"
        else:
            lit_eval_import = "import ast as _ast\n"
            lit_eval_fn = "_ast.literal_eval"
        code = (
            lit_eval_import
            + f"from {name} import {fn} as _fn\n"
            f"_args = {lit_eval_fn}({args_repr!r})\n"
            f"_expected = {lit_eval_fn}({expected_repr!r})\n"
            f"_result = _fn(*_args)\n"
            f"assert _result == _expected, f'got {{_result!r}}, expected {{_expected!r}}'\n"
            f"print('OK')\n"
        )

        r = subprocess.run(
            ["python3", "-c", code],
            capture_output=True, text=True, env=env,
        )

        if r.returncode == 0:
            passed += 1
            if verbose:
                print(f"  PASS  {inv_id}")
        else:
            failed += 1
            err_msg = (r.stderr or r.stdout).strip()
            errors.append({"invariant": inv_id, "error": err_msg})
            if verbose:
                print(f"  FAIL  {inv_id}: {err_msg[:120]}")

    return {"pass": passed, "fail": failed, "errors": errors}


def _verify_node(spec: dict, name: str, verbose: bool) -> dict:
    impl_dir = _CLEANROOM_NODE / name
    if not (impl_dir / "index.js").exists():
        return {
            "pass": 0,
            "fail": len(spec["invariants"]),
            "errors": [{"invariant": "ALL", "error": f"No implementation found at {impl_dir}/index.js"}],
        }

    blocked = _get_blocked_package(spec, name)
    policy_errors = _node_policy_errors(impl_dir / "index.js", blocked)
    if policy_errors:
        return {
            "pass": 0,
            "fail": len(spec["invariants"]),
            "errors": [
                {"invariant": "POLICY", "error": err}
                for err in policy_errors
            ],
        }

    passed, failed, errors = 0, 0, []
    for inv in spec["invariants"]:
        inv_id = inv["id"]
        spec_dict = inv.get("spec", {})
        fn = spec_dict.get("function", "")
        args = spec_dict.get("args", [])
        expected = spec_dict.get("expected")

        args_json = json.dumps(args)
        expected_json = json.dumps(expected)
        impl_json = json.dumps(str(impl_dir / "index.js"))
        blocked_json = json.dumps(blocked)

        code = (
            "const Module = require('module');\n"
            "const blocked = " + blocked_json + ";\n"
            "const builtin = new Set(Module.builtinModules.flatMap((m) => "
            "[m, m.startsWith('node:') ? m.slice(5) : 'node:' + m]));\n"
            "const originalLoad = Module._load;\n"
            "Module._load = function(request, parent, isMain) {\n"
            "  const root = request.startsWith('node:') ? request.slice(5).split('/')[0] : request.split('/')[0];\n"
            "  if (request === blocked || request.startsWith(blocked + '/') || request === 'node:' + blocked) {\n"
            "    throw new Error('THESEUS ISOLATION VIOLATION: attempted to require blocked module ' + request);\n"
            "  }\n"
            "  if (!request.startsWith('.') && !request.startsWith('/') && !builtin.has(request) && !builtin.has(root)) {\n"
            "    throw new Error('THESEUS DEPENDENCY VIOLATION: attempted to require npm package ' + request);\n"
            "  }\n"
            "  return originalLoad.apply(this, arguments);\n"
            "};\n"
            f"const pkg = require({impl_json});\n"
            f"const result = pkg.{fn}(...{args_json});\n"
            f"const expected = {expected_json};\n"
            f"if (JSON.stringify(result) !== JSON.stringify(expected)) {{\n"
            f"  process.stderr.write('got ' + JSON.stringify(result) + ', expected ' + JSON.stringify(expected));\n"
            f"  process.exit(1);\n"
            f"}}\n"
            f"console.log('OK');\n"
        )

        r = subprocess.run(
            ["node", "-e", code],
            capture_output=True, text=True,
        )

        if r.returncode == 0:
            passed += 1
            if verbose:
                print(f"  PASS  {inv_id}")
        else:
            failed += 1
            err_msg = (r.stderr or r.stdout).strip()
            errors.append({"invariant": inv_id, "error": err_msg})
            if verbose:
                print(f"  FAIL  {inv_id}: {err_msg[:120]}")

    return {"pass": passed, "fail": failed, "errors": errors}


def _node_policy_errors(impl_file: Path, blocked: str) -> list[str]:
    try:
        text = impl_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{impl_file}: cannot read implementation: {exc}"]

    requests = []
    patterns = [
        r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        r"\bfrom\s*['\"]([^'\"]+)['\"]",
        r"\bimport\s*['\"]([^'\"]+)['\"]",
    ]
    for pattern in patterns:
        requests.extend(re.findall(pattern, text))

    errors = []
    for request in requests:
        root = request[5:] if request.startswith("node:") else request
        root = root.split("/", 1)[0]
        if request == blocked or request.startswith(blocked + "/") or root == blocked:
            errors.append(
                f"{impl_file}: imports blocked module {request!r}; clean-room implementations must not wrap the original"
            )
        elif not request.startswith((".", "/", "node:")) and not _is_node_builtin(root):
            errors.append(
                f"{impl_file}: imports npm dependency {request!r}; only Node built-ins are allowed"
            )
    return errors


def _is_node_builtin(root: str) -> bool:
    script = (
        "const Module=require('module');"
        "const m=process.argv[1];"
        "process.exit(Module.builtinModules.includes(m)||Module.builtinModules.includes('node:'+m)?0:1)"
    )
    try:
        r = subprocess.run(["node", "-e", script, root], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def _python_policy_errors(impl_dir: Path, blocked: str) -> list[str]:
    """Return dependency-policy violations for a Python clean-room package."""
    allowed_theseus = _verified_registry_names()
    errors = []
    blocked_root = blocked.split(".", 1)[0]
    backdoors = set(_PY_IMPL_BACKDOORS.get(blocked, set()))
    backdoors.update(_PY_IMPL_BACKDOORS.get(blocked_root, set()))

    for path in sorted(impl_dir.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path}: cannot parse implementation: {exc}")
            continue

        for root in _import_roots(tree):
            if root == "__future__":
                continue
            if root == blocked_root or root == blocked:
                errors.append(
                    f"{path}: imports blocked package {root!r}; clean-room implementations must not wrap the original"
                )
            elif root in backdoors:
                errors.append(
                    f"{path}: imports implementation backdoor {root!r} for blocked package {blocked!r}"
                )
            elif root.startswith("theseus_"):
                if root not in allowed_theseus:
                    errors.append(
                        f"{path}: imports unverified Theseus dependency {root!r}"
                    )
            elif not _is_stdlib_module(root):
                errors.append(
                    f"{path}: imports non-stdlib dependency {root!r}; only stdlib and verified Theseus packages are allowed"
                )

    return errors


def _import_roots(tree: ast.AST) -> set[str]:
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def _verified_registry_names() -> set[str]:
    try:
        reg = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        name for name, info in reg.get("packages", {}).items()
        if isinstance(info, dict) and info.get("status") == "verified"
    }


def _is_stdlib_module(root: str) -> bool:
    if root == "__main__":
        return True
    if root in sys.builtin_module_names:
        return True
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if stdlib_names and root in stdlib_names:
        return True

    try:
        spec = importlib.util.find_spec(root)
    except (ImportError, ValueError):
        return False
    if spec is None or spec.origin is None:
        return False
    if spec.origin in ("built-in", "frozen"):
        return True

    origin = Path(spec.origin).resolve()
    stdlib_paths = [
        Path(p).resolve()
        for p in (sysconfig.get_path("stdlib"), sysconfig.get_path("platstdlib"))
        if p
    ]
    for stdlib_path in stdlib_paths:
        try:
            origin.relative_to(stdlib_path)
        except ValueError:
            continue
        parts = set(origin.parts)
        return "site-packages" not in parts and "dist-packages" not in parts
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a clean-room implementation in isolation")
    parser.add_argument("spec_json", help="Path to compiled .zspec.json file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    result = verify(args.spec_json, verbose=args.verbose)

    if "error" in result and result.get("pass", 0) == 0 and result.get("fail", 0) == 0:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        return 2

    total = result["pass"] + result["fail"]
    print(f"  {result['pass']}/{total} invariants passed")
    if result["errors"]:
        for e in result["errors"]:
            print(f"  FAIL {e['invariant']}: {e['error'][:200]}")
    return 0 if result["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
