"""
Tests for the attrs Z-layer behavioral spec (attrs.zspec.zsdl).

Covers:
  - SpecLoader: loading attrs spec via python_module backend
  - python_call_eq handler with attrs-specific patterns
  - InvariantRunner integration: all 14 invariants pass
  - CLI: verify-behavior runs attrs.zspec.json end-to-end

Categories verified:
  version (4)    — VersionInfo constructor field access
  has (4)        — attr.has() returns False for non-attrs values
  make_class (2) — attr.make_class() creates correctly named class with empty attrs
  validators (2) — validator factory stores type/options on the result
  exceptions (2) — exception __repr__() returns canonical strings
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

ATTRS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "attrs.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def attrs_spec():
    return vb.SpecLoader().load(ATTRS_SPEC_PATH)


@pytest.fixture(scope="module")
def attrs_mod(attrs_spec):
    return vb.LibraryLoader().load(attrs_spec["library"])


@pytest.fixture(scope="module")
def constants_map(attrs_spec):
    return vb.InvariantRunner().build_constants_map(attrs_spec["constants"])


@pytest.fixture(scope="module")
def registry(attrs_mod, constants_map):
    return vb.PatternRegistry(attrs_mod, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader / module loader
# ---------------------------------------------------------------------------

class TestAttrsSpecLoader:
    def test_loads_attrs_spec(self, attrs_spec):
        assert isinstance(attrs_spec, dict)

    def test_all_required_sections_present(self, attrs_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in attrs_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, attrs_spec):
        assert attrs_spec["library"]["backend"] == "python_module"

    def test_module_name_is_attr(self, attrs_spec):
        assert attrs_spec["library"]["module_name"] == "attr"

    def test_loads_attr_module(self, attrs_mod):
        import attr
        assert attrs_mod is attr

    def test_all_invariant_kinds_known(self, attrs_spec):
        for inv in attrs_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, attrs_spec):
        ids = [inv["id"] for inv in attrs_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version — VersionInfo constructor field access
# ---------------------------------------------------------------------------

class TestAttrsVersion:
    def test_version_info_year(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "VersionInfo",
                "args": [21, 2, 0, "final"],
                "method": "year",
                "expected": 21,
            },
        })
        assert ok, msg

    def test_version_info_minor(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "VersionInfo",
                "args": [21, 2, 0, "final"],
                "method": "minor",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_version_info_micro(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "VersionInfo",
                "args": [21, 2, 0, "final"],
                "method": "micro",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_version_info_releaselevel(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "VersionInfo",
                "args": [21, 2, 0, "final"],
                "method": "releaselevel",
                "expected": "final",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_year(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "VersionInfo",
                "args": [21, 2, 0, "final"],
                "method": "year",
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# has — attr.has() returns False for non-attrs values
# ---------------------------------------------------------------------------

class TestAttrsHas:
    def test_has_false_returns_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "has",
                "args": [False],
                "expected": False,
            },
        })
        assert ok, msg

    def test_has_int_zero_returns_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "has",
                "args": [0],
                "expected": False,
            },
        })
        assert ok, msg

    def test_has_empty_string_returns_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "has",
                "args": [""],
                "expected": False,
            },
        })
        assert ok, msg

    def test_has_plain_string_returns_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "has",
                "args": ["x"],
                "expected": False,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# make_class — attr.make_class() creates a valid attrs class
# ---------------------------------------------------------------------------

class TestAttrsMakeClass:
    def test_make_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "make_class",
                "args": ["Pt", ["x", "y"]],
                "method": "__name__",
                "expected": "Pt",
            },
        })
        assert ok, msg

    def test_make_class_empty_fields(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "make_class",
                "args": ["Empty", []],
                "method": "__attrs_attrs__",
                "expected": [],
            },
        })
        assert ok, msg

    def test_make_class_wrong_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "make_class",
                "args": ["Pt", ["x", "y"]],
                "method": "__name__",
                "expected": "NotPt",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# validators — factory stores type/options on result
# ---------------------------------------------------------------------------

class TestAttrsValidators:
    def test_instance_of_type_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "validators.instance_of",
                "args": ["mytype"],
                "method": "type",
                "expected": "mytype",
            },
        })
        assert ok, msg

    def test_in_options_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "validators.in_",
                "args": [[1, 2, 3]],
                "method": "options",
                "expected": [1, 2, 3],
            },
        })
        assert ok, msg

    def test_instance_of_wrong_type_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "validators.instance_of",
                "args": ["mytype"],
                "method": "type",
                "expected": "wrongtype",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# exceptions — exception __repr__ returns canonical strings
# ---------------------------------------------------------------------------

class TestAttrsExceptions:
    def test_frozen_instance_error_repr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.FrozenInstanceError",
                "args": [],
                "method": "__repr__",
                "expected": "FrozenInstanceError(\"can't set attribute\")",
            },
        })
        assert ok, msg

    def test_not_an_attrs_class_error_repr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.NotAnAttrsClassError",
                "args": [],
                "method": "__repr__",
                "expected": "NotAnAttrsClassError()",
            },
        })
        assert ok, msg

    def test_wrong_repr_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.NotAnAttrsClassError",
                "args": [],
                "method": "__repr__",
                "expected": "SomethingElse()",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 14 attrs invariants must pass
# ---------------------------------------------------------------------------

class TestAttrsAll:
    def test_all_pass(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod)
        assert len(results) == 14

    def test_no_skips(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod, filter_category="version")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_has_category(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod, filter_category="has")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_make_class_category(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod, filter_category="make_class")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_validators_category(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod, filter_category="validators")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_exceptions_category(self, attrs_spec, attrs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(attrs_spec, attrs_mod, filter_category="exceptions")
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestAttrsCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(ATTRS_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(ATTRS_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "14 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(ATTRS_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "attrs.version" in out
        assert "attrs.has" in out

    def test_filter_flag(self, capsys):
        vb.main([str(ATTRS_SPEC_PATH), "--filter", "version", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(ATTRS_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 14
        assert all(r["passed"] for r in data)
