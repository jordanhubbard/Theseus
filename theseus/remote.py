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
