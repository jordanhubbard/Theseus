#!/usr/bin/env python3
"""
build_and_verify.py — End-to-end build and behavioral verification harness.

Fetches the source of a package from its upstream repository (only for
permissive-licensed packages), builds and installs it into a temp prefix,
then runs verify_behavior.py against the freshly built artifact.

Supports local builds (macOS/Linux/FreeBSD) and remote builds via SSH
using the targets defined in config.yaml.

Usage:
    python3 tools/build_and_verify.py --record specs/zlib.json \\
        --zspec _build/zspecs/zlib.zspec.json

    python3 tools/build_and_verify.py --record specs/zlib.json \\
        --zspec _build/zspecs/zlib.zspec.json --target ubuntu.local

    python3 tools/build_and_verify.py --record specs/zlib.json \\
        --zspec _build/zspecs/zlib.zspec.json --all-targets

Exit codes:
    0   All targets passed
    1   One or more targets failed
    2   Configuration / setup error
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from theseus import config as _config
from theseus.remote import build_from_source_on_target, SourceBuildResult


# ---------------------------------------------------------------------------
# License gate
# ---------------------------------------------------------------------------

_GPL_SUBSTRINGS = ("GPL", "AGPL", "LGPL", "copyleft")
_PERMISSIVE_PREFIXES = (
    "MIT", "BSD", "Apache", "ISC", "0BSD", "Unlicense", "Zlib",
    "OpenSSL", "curl", "PSF", "Python-",
)


def _check_license(licenses: list) -> tuple:
    """Return (is_allowed, reason).  Raises nothing."""
    if not licenses:
        return True, "no license info — proceeding (unknown)"
    for lic in licenses:
        upper = lic.upper()
        for bad in _GPL_SUBSTRINGS:
            if bad.upper() in upper:
                return False, f"GPL-family license detected: {lic!r}"
    for lic in licenses:
        if any(lic.startswith(p) for p in _PERMISSIVE_PREFIXES):
            return True, lic
    return True, f"unrecognised license {licenses!r} — proceeding"


# ---------------------------------------------------------------------------
# Build environment per ecosystem
# ---------------------------------------------------------------------------

def _env_for(system_kind: str, prefix: str) -> dict:
    """Return extra environment variables needed for verify_behavior to find the built artifact."""
    env = dict(os.environ)
    lib_paths = [
        os.path.join(prefix, "lib"),
        os.path.join(prefix, "lib64"),
        os.path.join(prefix, "usr", "local", "lib"),
    ]
    node_path = os.path.join(prefix, "node_modules")

    if system_kind in ("autotools", "cmake", "meson"):
        existing_ld = env.get("LD_LIBRARY_PATH", "")
        existing_dyld = env.get("DYLD_LIBRARY_PATH", "")
        joined = ":".join(p for p in lib_paths if Path(p).exists())
        if joined:
            env["LD_LIBRARY_PATH"] = f"{joined}:{existing_ld}" if existing_ld else joined
            env["DYLD_LIBRARY_PATH"] = f"{joined}:{existing_dyld}" if existing_dyld else joined
    elif system_kind == "pypi":
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{prefix}:{existing}" if existing else prefix
    elif system_kind == "npm":
        existing = env.get("NODE_PATH", "")
        env["NODE_PATH"] = f"{node_path}:{existing}" if existing else node_path

    return env


def _lib_dir_flags(system_kind: str, prefix: str) -> list:
    """Return --lib-dir flags to pass to verify_behavior.py for ctypes packages."""
    if system_kind in ("autotools", "cmake", "meson"):
        dirs = [
            os.path.join(prefix, "lib"),
            os.path.join(prefix, "lib64"),
            os.path.join(prefix, "usr", "local", "lib"),
        ]
        flags = []
        for d in dirs:
            if Path(d).exists():
                flags += ["--lib-dir", d]
        return flags
    return []


# ---------------------------------------------------------------------------
# Local verify
# ---------------------------------------------------------------------------

def _verify_local(zspec: str, prefix: str, system_kind: str, verbose: bool) -> tuple:
    """Run verify_behavior.py in a subprocess with modified environment.

    Returns (passed, output).
    """
    verify_py = str(_REPO_ROOT / "tools" / "verify_behavior.py")
    cmd = [sys.executable, verify_py, zspec]
    cmd += _lib_dir_flags(system_kind, prefix)
    if verbose:
        cmd.append("--verbose")

    env = _env_for(system_kind, prefix)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, env=env,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "verify_behavior.py timed out after 120s"


# ---------------------------------------------------------------------------
# Remote verify
# ---------------------------------------------------------------------------

def _verify_remote(
    zspec: str,
    prefix: str,
    system_kind: str,
    target_cfg: dict,
    verbose: bool,
) -> tuple:
    """Copy zspec to remote target, run verify_behavior.py there, return (passed, output)."""
    from theseus.remote import _ssh_dest, _ssh_run, _rsync_to, _scp_to

    dest = _ssh_dest(target_cfg)
    python = target_cfg.get("python", "python3")
    work_base = "/tmp/theseus-e2e-verify"

    # Copy verify_behavior.py and the zspec to the remote
    verify_src = _REPO_ROOT / "tools" / "verify_behavior.py"
    remote_verify = f"{work_base}/verify_behavior.py"
    remote_zspec = f"{work_base}/spec.zspec.json"

    # Create remote dir
    rc, out, err = _ssh_run(dest, f"mkdir -p {work_base}", timeout=15)
    if rc != 0:
        return False, f"Could not create {work_base}: {err}"

    # rsync verify_behavior.py
    import shutil as _sh
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        _sh.copy2(verify_src, td_path / "verify_behavior.py")
        _sh.copy2(zspec, td_path / "spec.zspec.json")
        ok, errmsg = _rsync_to(td_path, dest, work_base, timeout=30)
        if not ok:
            ok, errmsg = _scp_to(td_path, dest, work_base, timeout=30)
        if not ok:
            return False, f"Could not copy files: {errmsg}"

    # Build env prefix string for ssh command
    lib_dirs = [
        f"{prefix}/lib", f"{prefix}/lib64",
        f"{prefix}/usr/local/lib",
    ]
    lib_dir_flags = " ".join(f"--lib-dir {d}" for d in lib_dirs)

    env_prefix = ""
    if system_kind in ("autotools", "cmake", "meson"):
        lib_path_str = ":".join(lib_dirs)
        env_prefix = f"LD_LIBRARY_PATH={lib_path_str} DYLD_LIBRARY_PATH={lib_path_str}"
    elif system_kind == "pypi":
        env_prefix = f"PYTHONPATH={prefix}"
    elif system_kind == "npm":
        env_prefix = f"NODE_PATH={prefix}/node_modules"

    verbose_flag = "--verbose" if verbose else ""
    cmd = (
        f"{env_prefix} {python} {remote_verify} {remote_zspec} "
        f"{lib_dir_flags} {verbose_flag} 2>&1"
    )
    rc, out, err = _ssh_run(dest, cmd, timeout=120)
    return rc == 0, out + err


# ---------------------------------------------------------------------------
# Per-target run
# ---------------------------------------------------------------------------

def _run_for_target(
    record: dict,
    zspec: str,
    target_cfg: dict,
    verbose: bool,
) -> dict:
    """Build, install, and verify on one target. Returns result dict."""
    target_name = target_cfg.get("name", "unknown")
    is_local = target_cfg.get("local", False)

    identity = record.get("identity", {})
    pkg_name = identity.get("ecosystem_id") or identity.get("canonical_name", "")
    pkg_version = identity.get("version", "")
    ecosystem = identity.get("ecosystem", "")

    # Determine system_kind and source_repository
    build = record.get("build", {})
    system_kind = build.get("system_kind", "autotools")
    extensions = record.get("extensions", {})
    source_repository = (
        extensions.get("pypi", {}).get("source_repository")
        or extensions.get("npm", {}).get("source_repository")
        or ""
    )
    if not source_repository:
        # Fallback to sources[].url (Nixpkgs/FreeBSD records)
        sources = record.get("sources", [])
        if sources:
            source_repository = sources[0].get("url", "")

    print(f"  [{target_name}] building {pkg_name}=={pkg_version} ({system_kind})")

    result = build_from_source_on_target(
        source_repo_url=source_repository,
        version_tag=f"v{pkg_version}",
        system_kind=system_kind,
        pkg_name=pkg_name,
        pkg_version=pkg_version,
        target_cfg=target_cfg,
        timeout=600,
    )

    if not result.success:
        return {
            "target": target_name, "passed": False,
            "phase": result.phase, "output": result.stderr,
        }

    # Verify
    print(f"  [{target_name}] verifying {pkg_name}")
    if is_local:
        passed, output = _verify_local(zspec, result.prefix, system_kind, verbose)
    else:
        passed, output = _verify_remote(zspec, result.prefix, system_kind, target_cfg, verbose)

    return {"target": target_name, "passed": passed, "phase": "verify", "output": output}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="End-to-end build and behavioral verification harness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--record", type=Path, required=True, metavar="PATH",
                    help="Canonical package record JSON")
    ap.add_argument("--zspec", type=Path, required=True, metavar="PATH",
                    help="Compiled Z-spec JSON (_build/zspecs/<name>.zspec.json)")
    ap.add_argument("--target", metavar="NAME",
                    help="Target name from config.yaml (default: local only)")
    ap.add_argument("--all-targets", action="store_true",
                    help="Run on all targets in config.yaml plus local")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json-out", type=Path, metavar="PATH",
                    help="Write JSON results to this file")
    ap.add_argument("--config", type=Path, default=None, metavar="PATH",
                    help="Path to config.yaml (default: repo root)")
    args = ap.parse_args()

    # Load record
    if not args.record.exists():
        print(f"Error: record not found: {args.record}", file=sys.stderr)
        return 2
    record = json.loads(args.record.read_text(encoding="utf-8"))

    # Load zspec
    if not args.zspec.exists():
        print(f"Error: zspec not found: {args.zspec}", file=sys.stderr)
        return 2
    zspec = str(args.zspec.resolve())

    # License gate
    licenses = record.get("descriptive", {}).get("license", [])
    allowed, reason = _check_license(licenses)
    if not allowed:
        print(f"SKIP — {reason}", file=sys.stderr)
        print("Source inspection is restricted to permissive-licensed packages.", file=sys.stderr)
        return 2
    print(f"License: {reason}")

    # Load config / build target list
    cfg = _config.load(args.config)
    all_targets_cfg = cfg.get("targets", [])

    targets_to_run = []
    if args.all_targets:
        targets_to_run = all_targets_cfg
    elif args.target:
        matched = [t for t in all_targets_cfg if t.get("name") == args.target]
        if not matched:
            print(f"Error: target {args.target!r} not found in config.yaml", file=sys.stderr)
            return 2
        targets_to_run = matched
    else:
        # Default: local target only
        targets_to_run = [{"name": "local", "local": True}]

    if not targets_to_run:
        print("No targets configured. Add targets to config.yaml or use --target.", file=sys.stderr)
        return 2

    pkg_name = record.get("identity", {}).get("canonical_name", "?")
    print(f"\nBuild-and-verify: {pkg_name}")
    print(f"Targets: {', '.join(t.get('name', '?') for t in targets_to_run)}\n")

    results = []
    for target_cfg in targets_to_run:
        r = _run_for_target(record, zspec, target_cfg, args.verbose)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {status}  {r['target']}  (phase: {r['phase']})")
        if args.verbose or not r["passed"]:
            for line in (r.get("output") or "").splitlines()[-30:]:
                print(f"    {line}")

    if args.json_out:
        args.json_out.write_text(
            json.dumps({"package": pkg_name, "results": results}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nResults written to {args.json_out}")

    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    print(f"\n{total - failed}/{total} targets passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
