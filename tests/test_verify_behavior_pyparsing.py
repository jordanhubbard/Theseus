"""
Tests for the python_module backend and pyparsing-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - PythonModuleLoader: loading pyparsing via the python_module backend
  - TestPyparsingAll: all 15 pyparsing invariants pass, invariant count check
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PYPARSING_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pyparsing.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pyparsing_spec():
    return vb.SpecLoader().load(PYPARSING_SPEC_PATH)


@pytest.fixture(scope="module")
def pyparsing_mod(pyparsing_spec):
    return vb.LibraryLoader().load(pyparsing_spec["library"])


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

class TestPythonModuleLoader:
    def test_loads_pyparsing_spec(self, pyparsing_spec):
        assert isinstance(pyparsing_spec, dict)

    def test_all_required_sections_present(self, pyparsing_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pyparsing_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pyparsing_spec):
        assert pyparsing_spec["library"]["backend"] == "python_module"

    def test_module_name_is_pyparsing(self, pyparsing_spec):
        assert pyparsing_spec["library"]["module_name"] == "pyparsing"

    def test_loads_pyparsing_module(self, pyparsing_mod):
        import pyparsing
        assert pyparsing_mod is pyparsing

    def test_all_invariant_kinds_known(self, pyparsing_spec):
        for inv in pyparsing_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pyparsing_spec):
        ids = [inv["id"] for inv in pyparsing_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 15 pyparsing invariants must pass
# ---------------------------------------------------------------------------

class TestPyparsingAll:
    def test_all_pass(self, pyparsing_spec, pyparsing_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyparsing_spec, pyparsing_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pyparsing_spec, pyparsing_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyparsing_spec, pyparsing_mod)
        assert len(results) == 15

    def test_no_skips(self, pyparsing_spec, pyparsing_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyparsing_spec, pyparsing_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_srange(self, pyparsing_spec, pyparsing_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyparsing_spec, pyparsing_mod, filter_category="srange")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_position(self, pyparsing_spec, pyparsing_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyparsing_spec, pyparsing_mod, filter_category="position")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_common(self, pyparsing_spec, pyparsing_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyparsing_spec, pyparsing_mod, filter_category="common")
        assert len(results) == 3
        assert all(r.passed for r in results)
