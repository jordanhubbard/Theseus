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
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLEANROOM_PYTHON = _REPO_ROOT / "cleanroom" / "python"
_CLEANROOM_NODE = _REPO_ROOT / "cleanroom" / "node"


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

    passed, failed, errors = 0, 0, []
    for inv in spec["invariants"]:
        inv_id = inv["id"]
        spec_dict = inv.get("spec", {})
        fn = spec_dict.get("function", "")
        args = spec_dict.get("args", [])
        expected = spec_dict.get("expected")

        args_json = json.dumps(args)
        expected_json = json.dumps(expected)

        code = (
            f"const pkg = require('{impl_dir}/index.js');\n"
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
