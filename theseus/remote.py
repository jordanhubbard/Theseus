"""
theseus/remote.py

Remote (and local) build dispatch.

Given a driver name, the directory containing driver output files, and a
target config dict, copies the files to the target and runs the appropriate
build command.  Uses subprocess + SSH/rsync — no third-party dependencies.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BuildResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    target: str = ""
    driver: str = ""
    command: str = ""


# ---------------------------------------------------------------------------
# Build command generation
# ---------------------------------------------------------------------------

def build_command(driver: str, work_path: str, target_cfg: dict) -> str:
    """
    Return the shell command string that builds a spec on the target.

    work_path is the absolute path (on the target) where driver output files
    have been placed.
    """
    os_name = target_cfg.get("os", "")

    if driver == "freebsd_ports":
        ports_root = target_cfg.get("ports_root", "/usr/ports")
        # make fetch verifies the distfile URL + checksum.
        # make build compiles.  Both are run; failure of either is reported.
        return (
            f"make -C {work_path} PORTSDIR={ports_root} fetch 2>&1 && "
            f"make -C {work_path} PORTSDIR={ports_root} build 2>&1"
        )

    if driver == "nixpkgs":
        nix_cmd = (
            f"nix-build --no-out-link "
            f"--expr 'with import <nixpkgs> {{}}; "
            f"callPackage {work_path}/default.nix {{}}' 2>&1"
        )
        # If the target doesn't have a native Nix install but has Docker,
        # wrap the build in a nixos/nix container.
        if target_cfg.get("nix_via_docker"):
            nix_cmd = (
                f"docker run --rm "
                f"-v {work_path}:{work_path}:ro "
                f"nixos/nix nix-build --no-out-link "
                f"--option filter-syscalls false "
                f"--expr 'with import <nixpkgs> {{}}; "
                f"callPackage {work_path}/default.nix {{}}' 2>&1"
            )
        return nix_cmd

    return f"echo 'No build command defined for driver: {driver}'; exit 1"


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

_SSH_OPTS = [
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=10",
]


def _ssh_dest(target_cfg: dict) -> str:
    user = target_cfg.get("user", "")
    host = target_cfg.get("host", "localhost")
    return f"{user}@{host}" if user else host


def _ssh_run(
    dest: str,
    cmd: str,
    *,
    timeout: int = 300,
) -> tuple[int, str, str]:
    """Run cmd on dest via SSH.  Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["ssh", *_SSH_OPTS, dest, cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def _rsync_to(
    src_dir: Path,
    dest: str,
    remote_path: str,
    *,
    timeout: int = 60,
) -> tuple[bool, str]:
    """
    Copy src_dir/* to dest:remote_path/ via rsync.
    Returns (success, error_message).
    """
    if not shutil.which("rsync"):
        return False, "rsync not found in PATH"
    result = subprocess.run(
        [
            "rsync", "-a", "--delete",
            str(src_dir).rstrip("/") + "/",
            f"{dest}:{remote_path}/",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


def _scp_to(
    src_dir: Path,
    dest: str,
    remote_path: str,
    *,
    timeout: int = 60,
) -> tuple[bool, str]:
    """Fallback to scp -r when rsync is unavailable."""
    result = subprocess.run(
        ["scp", "-r", str(src_dir), f"{dest}:{remote_path}"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def build_on_target(
    driver: str,
    output_dir: Path,
    canonical_name: str,
    target_cfg: dict,
    *,
    timeout: int = 300,
) -> BuildResult:
    """
    Copy driver output to the target and run the build.

    output_dir contains the files produced by the driver for canonical_name.
    target_cfg is a dict from config.yaml's targets list.
    Returns a BuildResult describing the outcome.
    """
    target_name = target_cfg.get("name", "unknown")
    is_local = target_cfg.get("local", False)

    if is_local:
        return _build_local(driver, output_dir, canonical_name, target_cfg, timeout=timeout)
    return _build_remote(driver, output_dir, canonical_name, target_cfg, timeout=timeout)


def _build_local(
    driver: str,
    output_dir: Path,
    canonical_name: str,
    target_cfg: dict,
    *,
    timeout: int = 300,
) -> BuildResult:
    target_name = target_cfg.get("name", "local")
    cmd = build_command(driver, str(output_dir.resolve()), target_cfg)
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return BuildResult(
        success=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
        target=target_name,
        driver=driver,
        command=cmd,
    )


def _build_remote(
    driver: str,
    output_dir: Path,
    canonical_name: str,
    target_cfg: dict,
    *,
    timeout: int = 300,
) -> BuildResult:
    target_name = target_cfg.get("name", "remote")
    dest = _ssh_dest(target_cfg)
    remote_work = f"/tmp/theseus-build/{canonical_name}"

    # 1. Create remote work directory
    rc, out, err = _ssh_run(dest, f"mkdir -p {remote_work}", timeout=30)
    if rc != 0:
        return BuildResult(
            success=False,
            stdout=out,
            stderr=f"Failed to create remote directory {remote_work}: {err}",
            returncode=rc,
            target=target_name,
            driver=driver,
            command=f"mkdir -p {remote_work}",
        )

    # 2. Copy files (rsync preferred, scp fallback)
    ok, errmsg = _rsync_to(output_dir, dest, remote_work, timeout=60)
    if not ok:
        # Try scp fallback
        ok, errmsg = _scp_to(output_dir, dest, remote_work, timeout=60)
    if not ok:
        return BuildResult(
            success=False,
            stdout="",
            stderr=f"File copy to {dest}:{remote_work} failed: {errmsg}",
            returncode=1,
            target=target_name,
            driver=driver,
            command="rsync/scp",
        )

    # 3. Run build command
    cmd = build_command(driver, remote_work, target_cfg)
    rc, out, err = _ssh_run(dest, cmd, timeout=timeout)
    return BuildResult(
        success=rc == 0,
        stdout=out,
        stderr=err,
        returncode=rc,
        target=target_name,
        driver=driver,
        command=cmd,
    )


# ---------------------------------------------------------------------------
# Source-fetch and from-source build
# ---------------------------------------------------------------------------

_BUILD_SYSTEM_COMMANDS: dict[str, str] = {
    "cmake": (
        "cmake -S {src} -B {src}/_build_theseus "
        "-DCMAKE_INSTALL_PREFIX={prefix} -DCMAKE_BUILD_TYPE=Release 2>&1 && "
        "cmake --build {src}/_build_theseus --parallel 4 2>&1 && "
        "cmake --install {src}/_build_theseus 2>&1"
    ),
    "autotools": (
        "cd {src} && "
        "([ -f configure ] || ([ -f autogen.sh ] && sh autogen.sh 2>&1) || autoreconf -fi 2>&1) && "
        "./configure --prefix={prefix} 2>&1 && "
        "make -j4 2>&1 && make install 2>&1"
    ),
    "meson": (
        "cd {src} && meson setup _build_theseus --prefix={prefix} 2>&1 && "
        "meson compile -C _build_theseus 2>&1 && "
        "meson install -C _build_theseus 2>&1"
    ),
    "pypi": (
        "pip3 install --target={prefix} --no-deps "
        "--disable-pip-version-check -q {pkg}=={ver} 2>&1"
    ),
    "npm": (
        "mkdir -p {prefix} && "
        "npm install --prefix {prefix} --no-save {pkg}@{ver} 2>&1"
    ),
}


@dataclass
class SourceBuildResult:
    success: bool
    prefix: str          # absolute path to the install prefix on the target
    stdout: str
    stderr: str
    returncode: int
    target: str = ""
    phase: str = ""      # "clone", "build", "install"


def build_from_source_on_target(
    source_repo_url: str,
    version_tag: str,
    system_kind: str,
    pkg_name: str,
    pkg_version: str,
    target_cfg: dict,
    *,
    work_base: str = "/tmp/theseus-e2e",
    timeout: int = 600,
) -> SourceBuildResult:
    """Clone a source repository on the target, build, and install to a temp prefix.

    For package-manager installs (pypi, npm) the clone step is skipped and the
    package is fetched directly from the registry.

    Returns a SourceBuildResult with the prefix path on the target.
    """
    target_name = target_cfg.get("name", "unknown")
    is_local = target_cfg.get("local", False)
    safe_name = pkg_name.replace("/", "__").replace("@", "")
    work_dir = f"{work_base}/{safe_name}"
    src_dir = f"{work_dir}/src"
    prefix = f"{work_dir}/prefix"

    def _run(cmd: str, phase: str, t: int = timeout):
        if is_local:
            import subprocess as _sp
            r = _sp.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
            if r.returncode != 0:
                return SourceBuildResult(
                    success=False, prefix=prefix, stdout=r.stdout,
                    stderr=r.stderr, returncode=r.returncode,
                    target=target_name, phase=phase,
                )
            return None
        else:
            dest = _ssh_dest(target_cfg)
            rc, out, err = _ssh_run(dest, cmd, timeout=t)
            if rc != 0:
                return SourceBuildResult(
                    success=False, prefix=prefix, stdout=out,
                    stderr=err, returncode=rc,
                    target=target_name, phase=phase,
                )
            return None

    def _run_ok(cmd: str, phase: str, t: int = timeout):
        """Run cmd; return error message or None on success."""
        r = _run(cmd, phase, t)
        return r.stderr if r else None

    # 1. Create working directory
    err = _run_ok(f"mkdir -p {src_dir} {prefix}", "setup", 30)
    if err:
        return SourceBuildResult(False, prefix, "", err, 1, target_name, "setup")

    # 2. Fetch source (skip for package-manager builds)
    if system_kind not in ("pypi", "npm"):
        if not source_repo_url:
            return SourceBuildResult(
                False, prefix, "", "No source_repository URL in record", 1,
                target_name, "clone",
            )
        tag_flags = f"--branch {version_tag} --depth 1" if version_tag else "--depth 1"
        clone_cmd = f"git clone {tag_flags} {source_repo_url} {src_dir} 2>&1"
        err = _run_ok(clone_cmd, "clone", 120)
        if err:
            return SourceBuildResult(False, prefix, "", err, 1, target_name, "clone")

    # 3. Build and install
    tpl = _BUILD_SYSTEM_COMMANDS.get(system_kind, _BUILD_SYSTEM_COMMANDS["autotools"])
    build_cmd = tpl.format(
        src=src_dir, prefix=prefix, pkg=pkg_name, ver=pkg_version,
    )
    err = _run_ok(build_cmd, "build", timeout)
    if err:
        return SourceBuildResult(False, prefix, "", err, 1, target_name, "build")

    return SourceBuildResult(
        success=True, prefix=prefix, stdout="", stderr="",
        returncode=0, target=target_name, phase="done",
    )
