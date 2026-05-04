"""Tests for the clean-room isolation harness."""
import json
import os
from pathlib import Path
import subprocess

import pytest

import cleanroom_verify as cv

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


def _cleanroom_spec(tmp_path: Path, name: str, lang: str, blocks: str) -> Path:
    spec = {
        "identity": {"canonical_name": name, "spec_for_versions": ">=0"},
        "backend_lang": lang,
        "blocks": blocks,
        "invariants": [
            {
                "id": f"{name}.ok",
                "kind": "python_call_eq",
                "description": "ok",
                "category": "basic",
                "spec": {"function": "ok", "args": [], "expected": True},
            }
        ],
    }
    path = tmp_path / f"{name}.zspec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_python_cleanroom_rejects_unverified_dependency(tmp_path, monkeypatch):
    root = tmp_path / "python"
    impl = root / "theseus_bad_dep"
    impl.mkdir(parents=True)
    (impl / "__init__.py").write_text(
        "import not_a_real_theseus_dependency\n"
        "def ok():\n"
        "    return True\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cv, "_CLEANROOM_PYTHON", root)

    result = cv.verify(str(_cleanroom_spec(tmp_path, "theseus_bad_dep", "python_cleanroom", "realpkg")))

    assert result["pass"] == 0
    assert result["fail"] == 1
    assert "non-stdlib dependency" in result["errors"][0]["error"]


def test_python_cleanroom_rejects_private_backdoor_for_blocked_package(tmp_path, monkeypatch):
    root = tmp_path / "python"
    impl = root / "theseus_struct_wrapper"
    impl.mkdir(parents=True)
    (impl / "__init__.py").write_text(
        "import _struct\n"
        "def ok():\n"
        "    return True\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cv, "_CLEANROOM_PYTHON", root)

    result = cv.verify(str(_cleanroom_spec(tmp_path, "theseus_struct_wrapper", "python_cleanroom", "struct")))

    assert result["pass"] == 0
    assert result["fail"] == 1
    assert "implementation backdoor" in result["errors"][0]["error"]


def test_node_cleanroom_rejects_blocked_require(tmp_path, monkeypatch):
    root = tmp_path / "node"
    impl = root / "theseus_path_wrapper"
    impl.mkdir(parents=True)
    (impl / "index.js").write_text(
        "const path = require('path');\n"
        "module.exports = { ok: () => true };\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cv, "_CLEANROOM_NODE", root)

    result = cv.verify(str(_cleanroom_spec(tmp_path, "theseus_path_wrapper", "node_cleanroom", "path")))

    assert result["pass"] == 0
    assert result["fail"] == 1
    assert "blocked module" in result["errors"][0]["error"]
