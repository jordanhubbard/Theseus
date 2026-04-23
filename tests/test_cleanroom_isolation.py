"""Tests for the clean-room isolation harness."""
import os
import subprocess


CLEANROOM_PYTHON = os.path.abspath("cleanroom/python")


def _run_isolated(code: str, blocked: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "PYTHONPATH": CLEANROOM_PYTHON,
        "PYTHONNOUSERSITE": "1",
        "THESEUS_BLOCKED_PACKAGE": blocked,
    }
    return subprocess.run(
        ["python3", "-c", code],
        capture_output=True,
        env=env,
    )


def test_blocker_prevents_stdlib_import():
    result = _run_isolated("import json", "json")
    assert result.returncode != 0
    assert b"THESEUS ISOLATION VIOLATION" in result.stderr


def test_blocker_prevents_submodule_import():
    result = _run_isolated("import json.decoder", "json")
    assert result.returncode != 0
    assert b"THESEUS ISOLATION VIOLATION" in result.stderr


def test_blocker_allows_other_imports():
    result = _run_isolated("import os; import sys; print('ok')", "json")
    assert result.returncode == 0
    assert b"ok" in result.stdout


def test_no_blocked_package_env_allows_all():
    env = {**os.environ, "PYTHONPATH": CLEANROOM_PYTHON, "PYTHONNOUSERSITE": "1"}
    env.pop("THESEUS_BLOCKED_PACKAGE", None)
    result = subprocess.run(
        ["python3", "-c", "import json; print('ok')"],
        capture_output=True, env=env,
    )
    assert result.returncode == 0
    assert b"ok" in result.stdout
