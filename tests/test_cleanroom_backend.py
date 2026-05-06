"""Tests for python_cleanroom and node_cleanroom backend support in the ZSDL compiler."""
import json
import os
import subprocess
import sys
import textwrap

import pytest


SAMPLE_PY_CLEANROOM = textwrap.dedent("""\
    spec: sample_cr
    version: ">=3.9"
    backend: python_cleanroom(sample_cr)

    invariant sample_cr.always_true:
      description: "always true"
      kind: python_call_eq
      function: always_true
      args: []
      expected: true
""")

SAMPLE_NODE_CLEANROOM = textwrap.dedent("""\
    spec: sample_node_cr
    version: ">=18"
    backend: node_cleanroom(sample_node_cr)

    invariant sample_node_cr.always_true:
      description: "always true"
      kind: python_call_eq
      function: always_true
      args: []
      expected: true
""")


def _compile(spec_text: str, tmp_path) -> dict:
    spec_file = tmp_path / "sample.zspec.zsdl"
    spec_file.write_text(spec_text)
    result = subprocess.run(
        [sys.executable, "tools/zsdl_compile.py", str(spec_file)],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    assert result.returncode == 0, f"Compiler failed:\n{result.stderr}"
    # Compiler names output from the input file stem: sample.zspec.zsdl → sample.zspec.json
    out_path = "_build/zspecs/sample.zspec.json"
    return json.load(open(out_path))


def test_python_cleanroom_backend_lang(tmp_path):
    out = _compile(SAMPLE_PY_CLEANROOM, tmp_path)
    assert out["backend_lang"] == "python_cleanroom"


def test_python_cleanroom_path(tmp_path):
    out = _compile(SAMPLE_PY_CLEANROOM, tmp_path)
    assert out["cleanroom_path"] == "cleanroom/python/sample_cr"


def test_node_cleanroom_backend_lang(tmp_path):
    out = _compile(SAMPLE_NODE_CLEANROOM, tmp_path)
    assert out["backend_lang"] == "node_cleanroom"


def test_node_cleanroom_path(tmp_path):
    out = _compile(SAMPLE_NODE_CLEANROOM, tmp_path)
    assert out["cleanroom_path"] == "cleanroom/node/sample_node_cr"


def test_python_cleanroom_invariants_present(tmp_path):
    out = _compile(SAMPLE_PY_CLEANROOM, tmp_path)
    assert len(out["invariants"]) == 1
    assert out["invariants"][0]["id"] == "sample_cr.always_true"
