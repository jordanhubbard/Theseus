#!/usr/bin/env python3
"""
verify_in_venv.py — Run verify_behavior.py inside a temporary virtual environment.

Creates a fresh venv, installs the specified package(s), runs the behavioral
spec verification, then removes the venv.  This lets you verify a spec without
permanently installing the library on your system.

Usage:
  python3 tools/verify_in_venv.py zspecs/json.zspec.zsdl json
  python3 tools/verify_in_venv.py zspecs/hashlib.zspec.zsdl   # stdlib — no install needed
  python3 tools/verify_in_venv.py zspecs/requests_utils_rust.zspec.zsdl requests
  python3 tools/verify_in_venv.py zspecs/pydantic_rust.zspec.zsdl "pydantic>=2"
  python3 tools/verify_in_venv.py zspecs/zlib.zspec.zsdl --no-install  # ctypes/stdlib
  python3 tools/verify_in_venv.py zspecs/json.zspec.zsdl json --keep    # keep venv for inspection

The compiled spec (.zspec.json) is produced automatically via compile-zsdl if
it does not already exist.

Exit codes:
  0  All invariants passed
  1  One or more invariants failed
  2  Setup error (venv creation failed, package install failed, etc.)
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BUILD_DIR = _REPO_ROOT / "_build" / "zspecs"
_COMPILE_TOOL = _REPO_ROOT / "tools" / "zsdl_compile.py"
_VERIFY_TOOL = _REPO_ROOT / "tools" / "verify_behavior.py"


def _compile_spec(zsdl_path: Path) -> Path:
    """Compile a .zspec.zsdl → .zspec.json if not already current."""
    stem = zsdl_path.stem  # e.g. "json.zspec"
    compiled = _BUILD_DIR / f"{stem}.json"
    _BUILD_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, str(_COMPILE_TOOL), str(zsdl_path)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"ERROR: compile failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(2)
    if not compiled.exists():
        print(f"ERROR: expected compiled spec at {compiled} but it was not created",
              file=sys.stderr)
        sys.exit(2)
    return compiled


def _create_venv(venv_dir: Path) -> Path:
    """Create a venv and return the path to its python executable."""
    r = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: venv creation failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(2)
    python = venv_dir / "bin" / "python"
    if not python.exists():
        python = venv_dir / "Scripts" / "python.exe"  # Windows
    return python


def _install_packages(venv_python: Path, packages: list[str]) -> None:
    """pip install packages into the venv."""
    r = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet"] + packages,
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"ERROR: pip install failed:\n{r.stdout}\n{r.stderr}", file=sys.stderr)
        sys.exit(2)
    for pkg in packages:
        print(f"  installed: {pkg}")


def _run_verify(venv_python: Path, compiled_spec: Path, verbose: bool, filter_: str | None) -> int:
    """Run verify_behavior.py inside the venv and return its exit code."""
    cmd = [str(venv_python), str(_VERIFY_TOOL), str(compiled_spec)]
    if verbose:
        cmd.append("--verbose")
    if filter_:
        cmd += ["--filter", filter_]
    r = subprocess.run(cmd, cwd=str(_REPO_ROOT))
    return r.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a behavioral spec in an isolated virtual environment"
    )
    parser.add_argument("spec", help="Path to .zspec.zsdl (or compiled .zspec.json)")
    parser.add_argument("packages", nargs="*",
                        help="PyPI package(s) to install before verification "
                             "(e.g. 'requests' 'pydantic>=2'). "
                             "Omit for stdlib and ctypes specs.")
    parser.add_argument("--no-install", action="store_true",
                        help="Skip pip install (for stdlib / ctypes specs)")
    parser.add_argument("--keep", action="store_true",
                        help="Keep the venv after verification (useful for debugging)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Pass --verbose to verify_behavior.py")
    parser.add_argument("--filter", dest="filter_",
                        help="Pass --filter to verify_behavior.py")
    parser.add_argument("--python", default=sys.executable,
                        help="Python interpreter to use for the venv (default: current)")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = _REPO_ROOT / spec_path

    if not spec_path.exists():
        print(f"ERROR: spec not found: {spec_path}", file=sys.stderr)
        return 2

    # Compile if needed
    if spec_path.suffix == ".zsdl":
        print(f"Compiling {spec_path.name} ...")
        compiled = _compile_spec(spec_path)
    else:
        compiled = spec_path

    # Create temp venv
    venv_dir = Path(tempfile.mkdtemp(prefix="theseus-venv-"))
    print(f"Creating venv at {venv_dir} ...")
    venv_python = _create_venv(venv_dir)

    try:
        # Install packages
        if args.packages and not args.no_install:
            print(f"Installing: {', '.join(args.packages)}")
            _install_packages(venv_python, args.packages)
        elif not args.no_install and not args.packages:
            print("No packages specified — running against stdlib/ctypes only.")

        # Run verification
        print(f"\nVerifying {compiled.name} ...\n")
        exit_code = _run_verify(venv_python, compiled, args.verbose, args.filter_)

    finally:
        if args.keep:
            print(f"\nVenv kept at: {venv_dir}")
            print(f"Activate with: source {venv_dir}/bin/activate")
        else:
            shutil.rmtree(venv_dir, ignore_errors=True)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
