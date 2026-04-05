"""
Tests for the traitlets Z-layer behavioral spec (traitlets.zspec.zsdl).

Covers:
  - SpecLoader: loading traitlets spec via python_module backend
  - python_call_eq handler with traitlets-specific patterns
  - InvariantRunner integration: all 14 invariants pass
  - CLI: verify-behavior runs traitlets.zspec.json end-to-end

Categories verified:
  version (2)    — __version__ is a string and contains a dot
  trait_types (6) — Int/Unicode/Bool/Float/List/Dict class __name__ attributes
  has_traits (2) — HasTraits and TraitType class __name__ attributes
  defaults (4)   — Int/Unicode/Bool/Float default() return value
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

TRAITLETS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "traitlets.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def traitlets_spec():
    return vb.SpecLoader().load(TRAITLETS_SPEC_PATH)


@pytest.fixture(scope="module")
def traitlets_mod(traitlets_spec):
    return vb.LibraryLoader().load(traitlets_spec["library"])


@pytest.fixture(scope="module")
def constants_map(traitlets_spec):
    return vb.InvariantRunner().build_constants_map(traitlets_spec["constants"])


@pytest.fixture(scope="module")
def registry(traitlets_mod, constants_map):
    return vb.PatternRegistry(traitlets_mod, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader / module loader
# ---------------------------------------------------------------------------

class TestTraitletsSpecLoader:
    def test_loads_traitlets_spec(self, traitlets_spec):
        assert isinstance(traitlets_spec, dict)

    def test_all_required_sections_present(self, traitlets_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in traitlets_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, traitlets_spec):
        assert traitlets_spec["library"]["backend"] == "python_module"

    def test_module_name_is_traitlets(self, traitlets_spec):
        assert traitlets_spec["library"]["module_name"] == "traitlets"

    def test_loads_traitlets_module(self, traitlets_mod):
        import traitlets
        assert traitlets_mod is traitlets

    def test_all_invariant_kinds_known(self, traitlets_spec):
        for inv in traitlets_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, traitlets_spec):
        ids = [inv["id"] for inv in traitlets_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version — __version__ is a string containing dots
# ---------------------------------------------------------------------------

class TestTraitletsVersion:
    def test_version_is_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__class__.__name__.__eq__",
                "args": ["str"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_contains_dot(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["."],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_wrong_class_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__class__.__name__.__eq__",
                "args": ["int"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# trait_types — class __name__ attributes for core trait types
# ---------------------------------------------------------------------------

class TestTraitletsTraitTypes:
    def test_int_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Int.__name__.__eq__",
                "args": ["Int"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_unicode_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Unicode.__name__.__eq__",
                "args": ["Unicode"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_bool_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Bool.__name__.__eq__",
                "args": ["Bool"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_float_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Float.__name__.__eq__",
                "args": ["Float"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_list_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "List.__name__.__eq__",
                "args": ["List"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_dict_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Dict.__name__.__eq__",
                "args": ["Dict"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrong_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Int.__name__.__eq__",
                "args": ["NotInt"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# has_traits — base class names
# ---------------------------------------------------------------------------

class TestTraitletsHasTraits:
    def test_has_traits_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HasTraits.__name__.__eq__",
                "args": ["HasTraits"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_trait_type_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "TraitType.__name__.__eq__",
                "args": ["TraitType"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrong_class_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HasTraits.__name__.__eq__",
                "args": ["WrongName"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# defaults — TraitType instances return correct default values
# ---------------------------------------------------------------------------

class TestTraitletsDefaults:
    def test_int_default_five(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Int",
                "args": [5],
                "method": "default",
                "expected": 5,
            },
        })
        assert ok, msg

    def test_unicode_default_hello(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Unicode",
                "args": ["hello"],
                "method": "default",
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_bool_default_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Bool",
                "args": [True],
                "method": "default",
                "expected": True,
            },
        })
        assert ok, msg

    def test_float_default_pi(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Float",
                "args": [3.14],
                "method": "default",
                "expected": 3.14,
            },
        })
        assert ok, msg

    def test_wrong_default_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Int",
                "args": [5],
                "method": "default",
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 14 traitlets invariants must pass
# ---------------------------------------------------------------------------

class TestTraitletsAll:
    def test_all_pass(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod)
        assert len(results) == 14

    def test_no_skips(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_trait_types_category(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod, filter_category="trait_types")
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_by_has_traits_category(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod, filter_category="has_traits")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_defaults_category(self, traitlets_spec, traitlets_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(traitlets_spec, traitlets_mod, filter_category="defaults")
        assert len(results) == 4
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestTraitletsCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(TRAITLETS_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(TRAITLETS_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "14 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(TRAITLETS_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "traitlets.version" in out
        assert "traitlets.trait_type" in out

    def test_filter_flag(self, capsys):
        vb.main([str(TRAITLETS_SPEC_PATH), "--filter", "version", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(TRAITLETS_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 14
        assert all(r["passed"] for r in data)
