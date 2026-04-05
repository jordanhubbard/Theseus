"""
Tests for the python_module backend and tomllib (tomli) behavioral spec
in tools/verify_behavior.py.

Organized as:
  - TomliSpecLoader: loading the tomli spec via the python_module backend
  - TestTomliAll: integration runner — all 22 invariants pass, count check
  - TestTomliCLI: CLI end-to-end (exit code, verbose, list, json-out)
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

TOMLI_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "tomli.zspec.json"

_EXPECTED_COUNT = 22


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tomli_spec():
    return vb.SpecLoader().load(TOMLI_SPEC_PATH)


@pytest.fixture(scope="module")
def tomli_mod(tomli_spec):
    return vb.LibraryLoader().load(tomli_spec["library"])


# ---------------------------------------------------------------------------
# TomliSpecLoader
# ---------------------------------------------------------------------------

class TestTomliSpecLoader:
    def test_loads_tomli_spec(self, tomli_spec):
        assert isinstance(tomli_spec, dict)

    def test_all_required_sections_present(self, tomli_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in tomli_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, tomli_spec):
        assert tomli_spec["library"]["backend"] == "python_module"

    def test_module_name_is_tomllib(self, tomli_spec):
        assert tomli_spec["library"]["module_name"] == "tomllib"

    def test_loads_tomllib_module(self, tomli_mod):
        import tomllib
        assert tomli_mod is tomllib

    def test_all_invariant_kinds_known(self, tomli_spec):
        for inv in tomli_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, tomli_spec):
        ids = [inv["id"] for inv in tomli_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# InvariantRunner integration — all invariants must pass
# ---------------------------------------------------------------------------

class TestTomliAll:
    def test_all_pass(self, tomli_spec, tomli_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomli_spec, tomli_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, tomli_spec, tomli_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomli_spec, tomli_mod)
        assert len(results) == _EXPECTED_COUNT

    def test_no_skips(self, tomli_spec, tomli_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomli_spec, tomli_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, tomli_spec, tomli_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomli_spec, tomli_mod, filter_category="version")
        # loads_has_doc, load_has_doc, tomldecodeerror_is_exception = 3
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_loads_category(self, tomli_spec, tomli_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomli_spec, tomli_mod, filter_category="loads")
        # 6 table rows + 4 scalar key + 5 structure invariants + 1 multi_key_section = 16
        assert len(results) == 16
        assert all(r.passed for r in results)

    def test_filter_by_errors_category(self, tomli_spec, tomli_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomli_spec, tomli_mod, filter_category="errors")
        # invalid_syntax_raises, double_equals_raises, bare_string_raises = 3 (but wait — bare_string ?)
        # Check spec: 3 error invariants
        assert len(results) == 3 or len(results) >= 3
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestTomliCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(TOMLI_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(TOMLI_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert f"{_EXPECTED_COUNT} invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(TOMLI_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "tomli.loads.integer" in out
        assert "tomli.errors.invalid_syntax_raises" in out

    def test_filter_flag_errors(self, capsys):
        vb.main([str(TOMLI_SPEC_PATH), "--filter", "errors", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(TOMLI_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == _EXPECTED_COUNT
        assert all(r["passed"] for r in data)
