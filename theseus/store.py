"""
theseus/store.py

Artifact storage for build outputs.

Supports:
  file://path   — local filesystem copy
  s3://bucket/prefix — upload via aws CLI (MinIO compatible via endpoint_url)
  https://host/path  — upload via curl (PUT)

For MinIO/compatible S3, pass store_cfg with:
  endpoint_url: http://ubumeh.local:9000
  access_key: ...
  secret_key: ...

Writes a build record to reports/builds.jsonl on every store() call.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store(
    url: str,
    canonical_name: str,
    driver: str,
    spec: dict,
    output_dir: Path,
    store_cfg: dict | None = None,
) -> tuple[bool, str]:
    """
    Store the spec JSON + driver output files at url/<canonical_name>/<driver>/.

    store_cfg is the full artifact_store config dict (may include endpoint_url,
    access_key, secret_key for MinIO / S3-compatible endpoints).

    Returns (success, error_message).  On success error_message is "".
    Also appends a build record to reports/builds.jsonl.
    """
    if not url:
        return False, "No artifact store URL configured"

    cfg = store_cfg or {}

    if url.startswith("file://"):
        ok, errmsg = _store_file(url, canonical_name, driver, spec, output_dir)
    elif url.startswith("s3://"):
        ok, errmsg = _store_s3(url, canonical_name, driver, spec, output_dir, cfg)
    elif url.startswith("https://") or url.startswith("http://"):
        ok, errmsg = _store_http(url, canonical_name, driver, spec, output_dir)
    else:
        return False, f"Unsupported artifact store URL scheme: {url}"

    _append_build_record(
        canonical_name=canonical_name,
        driver=driver,
        store_url=url,
        success=ok,
        error=errmsg,
    )
    return ok, errmsg


# ---------------------------------------------------------------------------
# file:// storage
# ---------------------------------------------------------------------------

def _store_file(
    url: str,
    canonical_name: str,
    driver: str,
    spec: dict,
    output_dir: Path,
) -> tuple[bool, str]:
    """Copy files to a local path derived from the file:// URL."""
    # file:///absolute/path or file://relative/path
    local_root = url[len("file://"):]
    dest = Path(local_root) / canonical_name / driver
    try:
        dest.mkdir(parents=True, exist_ok=True)
        # Write spec.json
        spec_dest = dest / "spec.json"
        spec_dest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        # Copy all output files
        for src_file in output_dir.iterdir():
            if src_file.is_file():
                shutil.copy2(src_file, dest / src_file.name)
    except OSError as e:
        return False, str(e)
    return True, ""


# ---------------------------------------------------------------------------
# s3:// storage
# ---------------------------------------------------------------------------

def _store_s3(
    url: str,
    canonical_name: str,
    driver: str,
    spec: dict,
    output_dir: Path,
    cfg: dict,
) -> tuple[bool, str]:
    """Upload files to S3 (or MinIO-compatible) via the aws CLI."""
    if not shutil.which("aws"):
        return False, "aws CLI not found in PATH"

    prefix = url.rstrip("/") + f"/{canonical_name}/{driver}"
    endpoint_url = cfg.get("endpoint_url", "")
    access_key = cfg.get("access_key", "")
    secret_key = cfg.get("secret_key", "")

    spec_tmp = output_dir / "_spec.json"
    try:
        spec_tmp.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        ok, errmsg = _aws_cp(
            spec_tmp, f"{prefix}/spec.json", endpoint_url, access_key, secret_key
        )
        if not ok:
            return False, errmsg

        for src_file in output_dir.iterdir():
            if src_file.is_file() and src_file.name != "_spec.json":
                ok, errmsg = _aws_cp(
                    src_file,
                    f"{prefix}/{src_file.name}",
                    endpoint_url,
                    access_key,
                    secret_key,
                )
                if not ok:
                    return False, errmsg
    finally:
        if spec_tmp.exists():
            spec_tmp.unlink()

    return True, ""


def _aws_cp(
    src: Path,
    dest: str,
    endpoint_url: str = "",
    access_key: str = "",
    secret_key: str = "",
) -> tuple[bool, str]:
    cmd = ["aws", "s3", "cp", str(src), dest]
    if endpoint_url:
        cmd += ["--endpoint-url", endpoint_url]

    env = os.environ.copy()
    if access_key:
        env["AWS_ACCESS_KEY_ID"] = access_key
    if secret_key:
        env["AWS_SECRET_ACCESS_KEY"] = secret_key
    # MinIO doesn't care about region but aws CLI requires one
    env.setdefault("AWS_DEFAULT_REGION", "us-east-1")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


# ---------------------------------------------------------------------------
# https:// storage
# ---------------------------------------------------------------------------

def _store_http(
    url: str,
    canonical_name: str,
    driver: str,
    spec: dict,
    output_dir: Path,
) -> tuple[bool, str]:
    """Upload files via curl PUT."""
    if not shutil.which("curl"):
        return False, "curl not found in PATH"

    prefix = url.rstrip("/") + f"/{canonical_name}/{driver}"

    spec_tmp = output_dir / "_spec.json"
    try:
        spec_tmp.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        ok, errmsg = _curl_put(spec_tmp, f"{prefix}/spec.json")
        if not ok:
            return False, errmsg

        for src_file in output_dir.iterdir():
            if src_file.is_file() and src_file.name != "_spec.json":
                ok, errmsg = _curl_put(src_file, f"{prefix}/{src_file.name}")
                if not ok:
                    return False, errmsg
    finally:
        if spec_tmp.exists():
            spec_tmp.unlink()

    return True, ""


def _curl_put(src: Path, dest: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["curl", "-s", "-S", "-f", "-X", "PUT", "--data-binary", f"@{src}", dest],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


# ---------------------------------------------------------------------------
# Build record log
# ---------------------------------------------------------------------------

def _append_build_record(
    *,
    canonical_name: str,
    driver: str,
    store_url: str,
    success: bool,
    error: str,
) -> None:
    """Append one JSON line to reports/builds.jsonl."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "canonical_name": canonical_name,
        "driver": driver,
        "store_url": store_url,
        "success": success,
        "error": error,
    }
    reports_dir = Path("reports")
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        builds_log = reports_dir / "builds.jsonl"
        with builds_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass  # Best-effort; don't mask a successful store with a log failure
