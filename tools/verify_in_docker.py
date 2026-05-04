#!/usr/bin/env python3
"""
verify_in_docker.py — Run verify_behavior.py inside a disposable Docker container.

Builds (or reuses) the theseus-verify base image, starts a container with the
repo root mounted at /theseus, installs the requested packages via the appropriate
package manager, runs verify_behavior.py, then removes the container.

Supports all spec backend types:
  --pip  pkg[>=ver]    Python packages  (pip install)
  --apt  pkg           Debian packages  (apt-get install, for ctypes specs)
  --npm  pkg[@ver]     Node.js packages (npm install -g, for node specs)
  --cargo crate[@ver]  Rust crates      (cargo install, for rust_module specs)

Usage:
  python3 tools/verify_in_docker.py zspecs/zlib.zspec.zsdl
  python3 tools/verify_in_docker.py zspecs/requests.zspec.zsdl --pip requests
  python3 tools/verify_in_docker.py zspecs/zlib_ctypes.zspec.zsdl --apt zlib1g-dev
  python3 tools/verify_in_docker.py zspecs/chalk.zspec.zsdl --npm chalk
  python3 tools/verify_in_docker.py zspecs/serde_json_rust.zspec.zsdl --cargo serde_json

Multiple packages of the same type can be passed by repeating the flag:
  python3 tools/verify_in_docker.py zspecs/foo.zspec.zsdl --pip requests --pip urllib3

The compiled spec (.zspec.json) is produced automatically via zsdl_compile.py if
it does not already exist.

Exit codes:
  0  All invariants passed
  1  One or more invariants failed
  2  Setup error (Docker not found, image build failed, compile failed, etc.)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BUILD_DIR = _REPO_ROOT / "_build" / "zspecs"
_COMPILE_TOOL = _REPO_ROOT / "tools" / "zsdl_compile.py"
_VERIFY_TOOL = _REPO_ROOT / "tools" / "verify_behavior.py"
_DOCKERFILE = _REPO_ROOT / "docker" / "Dockerfile.verify"
_IMAGE_TAG = "theseus-verify:latest"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(argv: list[str], *, check: bool = True, capture: bool = False,
         input_: str | None = None) -> subprocess.CompletedProcess:
    kwargs: dict = dict(text=True)
    if capture:
        kwargs["capture_output"] = True
    if input_ is not None:
        kwargs["input"] = input_
    r = subprocess.run(argv, **kwargs)
    if check and r.returncode != 0:
        raise SystemExit(2)
    return r


def _docker(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    return _run(["docker"] + list(args), capture=capture)


def _check_docker() -> None:
    if shutil.which("docker") is None:
        print("ERROR: 'docker' not found in PATH. Install Docker Desktop or Docker Engine.",
              file=sys.stderr)
        sys.exit(2)
    r = _run(["docker", "info"], capture=True, check=False)
    if r.returncode != 0:
        print("ERROR: Docker daemon is not running. Start Docker and retry.", file=sys.stderr)
        sys.exit(2)


def _image_exists(tag: str) -> bool:
    r = _run(["docker", "image", "inspect", tag], capture=True, check=False)
    return r.returncode == 0


def _build_image(rebuild: bool) -> None:
    if not _DOCKERFILE.exists():
        print(f"ERROR: Dockerfile not found: {_DOCKERFILE}", file=sys.stderr)
        sys.exit(2)
    if _image_exists(_IMAGE_TAG) and not rebuild:
        print(f"Using existing image {_IMAGE_TAG}  (pass --rebuild to force rebuild)")
        return
    print(f"Building Docker image {_IMAGE_TAG} ...")
    _run(["docker", "build",
          "-f", str(_DOCKERFILE),
          "-t", _IMAGE_TAG,
          str(_REPO_ROOT)])


def _compile_spec(zsdl_path: Path) -> Path:
    stem = zsdl_path.stem  # e.g. "json.zspec"
    compiled = _BUILD_DIR / f"{stem}.json"
    _BUILD_DIR.mkdir(parents=True, exist_ok=True)
    r = _run([sys.executable, str(_COMPILE_TOOL), str(zsdl_path)],
             capture=True, check=False)
    if r.returncode != 0:
        print(f"ERROR: compile failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(2)
    if not compiled.exists():
        print(f"ERROR: expected compiled spec at {compiled}", file=sys.stderr)
        sys.exit(2)
    return compiled


# ── Container execution ────────────────────────────────────────────────────────

def _make_install_script(pip: list[str], apt: list[str],
                          npm: list[str], cargo: list[str]) -> str:
    lines = ["#!/bin/bash", "set -e"]
    if apt:
        lines += [
            "apt-get update -qq",
            f"apt-get install -y --no-install-recommends {' '.join(apt)}",
        ]
    if pip:
        lines.append(f"pip3 install --quiet {' '.join(pip)}")
    if npm:
        lines.append(f"npm install --prefix /npm-deps --quiet {' '.join(npm)}")
    if cargo:
        for crate in cargo:
            lines.append(f"cargo install {crate}")
    return "\n".join(lines) + "\n"


def _run_in_container(compiled_spec: Path,
                      pip: list[str], apt: list[str],
                      npm: list[str], cargo: list[str],
                      verbose: bool, filter_: str | None,
                      keep: bool) -> int:
    container_name = f"theseus-verify-{uuid.uuid4().hex[:8]}"
    # Path inside the container (repo root is mounted at /theseus)
    rel_spec = compiled_spec.relative_to(_REPO_ROOT)
    container_spec = f"/theseus/{rel_spec}"
    container_verify = "/theseus/tools/verify_behavior.py"

    install_script = _make_install_script(pip, apt, npm, cargo)
    # Write to a temp file that will be accessible via the mount
    script_host = _REPO_ROOT / "_build" / f".install_{container_name}.sh"
    script_host.parent.mkdir(parents=True, exist_ok=True)
    script_host.write_text(install_script)

    container_script = f"/theseus/_build/.install_{container_name}.sh"

    verify_cmd = ["python3", container_verify, container_spec]
    if verbose:
        verify_cmd.append("--verbose")
    if filter_:
        verify_cmd += ["--filter", filter_]

    # Build the full shell command for the container
    # NODE_PATH includes /npm-deps/node_modules for npm-installed packages
    run_cmd = (f"bash {container_script} && "
               f"NODE_PATH=/npm-deps/node_modules {' '.join(verify_cmd)}")

    docker_argv = [
        "docker", "run",
        "--rm" if not keep else "",
        "--name", container_name,
        "-v", f"{_REPO_ROOT}:/theseus:ro",
        # writable _build so the install script can write there
        "--tmpfs", "/theseus/_build",
        # but we need the already-compiled spec readable, so bind that dir rw
    ]
    # Replace the approach: mount repo read-only but _build read-write via overlay
    # Simpler: mount repo rw (no secrets in the repo root that matter for isolation)
    docker_argv = [
        "docker", "run",
        "--name", container_name,
        "-v", f"{_REPO_ROOT}:/theseus",
        "--workdir", "/theseus",
    ]
    if not keep:
        docker_argv.append("--rm")

    docker_argv += [_IMAGE_TAG, "bash", "-c", run_cmd]
    # Remove empty strings from optional --rm
    docker_argv = [a for a in docker_argv if a]

    print(f"Starting container {container_name} ...")
    if pip or apt or npm or cargo:
        labels = []
        if pip:   labels.append(f"pip: {', '.join(pip)}")
        if apt:   labels.append(f"apt: {', '.join(apt)}")
        if npm:   labels.append(f"npm: {', '.join(npm)}")
        if cargo: labels.append(f"cargo: {', '.join(cargo)}")
        print(f"Installing: {'; '.join(labels)}")
    print(f"\nVerifying {compiled_spec.name} ...\n")

    r = subprocess.run(docker_argv)
    script_host.unlink(missing_ok=True)

    if keep:
        print(f"\nContainer kept: {container_name}")
        print(f"Inspect with: docker exec -it {container_name} bash")

    return r.returncode


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a behavioral spec inside a disposable Docker container"
    )
    parser.add_argument("spec", help="Path to .zspec.zsdl (or compiled .zspec.json)")
    parser.add_argument("--pip",   dest="pip",   metavar="PKG", action="append", default=[],
                        help="Python package to install via pip (repeatable)")
    parser.add_argument("--apt",   dest="apt",   metavar="PKG", action="append", default=[],
                        help="Debian package to install via apt-get (repeatable)")
    parser.add_argument("--npm",   dest="npm",   metavar="PKG", action="append", default=[],
                        help="Node.js package to install globally via npm (repeatable)")
    parser.add_argument("--cargo", dest="cargo", metavar="CRATE", action="append", default=[],
                        help="Rust crate to install via cargo install (repeatable)")
    parser.add_argument("--rebuild", action="store_true",
                        help="Force rebuild of the Docker base image")
    parser.add_argument("--keep", action="store_true",
                        help="Keep container after verification (useful for debugging)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Pass --verbose to verify_behavior.py")
    parser.add_argument("--filter", dest="filter_",
                        help="Pass --filter PATTERN to verify_behavior.py")
    args = parser.parse_args()

    _check_docker()

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

    _build_image(args.rebuild)

    return _run_in_container(
        compiled,
        pip=args.pip, apt=args.apt, npm=args.npm, cargo=args.cargo,
        verbose=args.verbose, filter_=args.filter_,
        keep=args.keep,
    )


if __name__ == "__main__":
    sys.exit(main())
