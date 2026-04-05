"""
Tests for the python_module backend against the python-dotenv (dotenv) spec.

Organized as:
  - TestDotenvLoader: loading dotenv via the python_module backend
  - TestDotenvVersion: version category invariants (module name identity)
  - TestDotenvApi: api category invariants (__all__ membership)
  - TestDotenvFunctionNames: function_names category invariants (__name__ attributes)
  - TestDotenvParse: parse category invariants (dotenv_values with nonexistent path)
  - TestDotenvAll: all 12 dotenv invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

DOTENV_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "dotenv.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dotenv_spec():
    return vb.SpecLoader().load(DOTENV_SPEC_PATH)


@pytest.fixture(scope="module")
def dotenv_mod(dotenv_spec):
    return vb.LibraryLoader().load(dotenv_spec["library"])


@pytest.fixture(scope="module")
def constants_map(dotenv_spec):
    return vb.InvariantRunner().build_constants_map(dotenv_spec["constants"])


@pytest.fixture(scope="module")
def registry(dotenv_mod, constants_map):
    return vb.PatternRegistry(dotenv_mod, constants_map)


# ---------------------------------------------------------------------------
# TestDotenvLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestDotenvLoader:
    def test_loads_dotenv_spec(self, dotenv_spec):
        assert isinstance(dotenv_spec, dict)

    def test_all_required_sections_present(self, dotenv_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in dotenv_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, dotenv_spec):
        assert dotenv_spec["library"]["backend"] == "python_module"

    def test_module_name_is_dotenv(self, dotenv_spec):
        assert dotenv_spec["library"]["module_name"] == "dotenv"

    def test_loads_dotenv_module(self, dotenv_mod):
        import dotenv
        assert dotenv_mod is dotenv

    def test_all_invariant_kinds_known(self, dotenv_spec):
        for inv in dotenv_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, dotenv_spec):
        ids = [inv["id"] for inv in dotenv_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestDotenvVersion
# ---------------------------------------------------------------------------

class TestDotenvVersion:
    def test_module_name_is_dotenv(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__name__.__eq__",
                "args": ["dotenv"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_module_name_is_string(self, dotenv_mod):
        assert isinstance(dotenv_mod.__name__, str)
        assert dotenv_mod.__name__ == "dotenv"


# ---------------------------------------------------------------------------
# TestDotenvApi
# ---------------------------------------------------------------------------

class TestDotenvApi:
    def test_all_contains_load_dotenv(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["load_dotenv"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_contains_dotenv_values(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["dotenv_values"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_contains_find_dotenv(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["find_dotenv"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_contains_get_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["get_key"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_contains_set_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["set_key"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_contains_unset_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["unset_key"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_is_list_of_strings(self, dotenv_mod):
        assert isinstance(dotenv_mod.__all__, list)
        assert all(isinstance(name, str) for name in dotenv_mod.__all__)

    def test_wrong_name_not_in_all(self, registry):
        """Sanity check: a nonexistent function is not in __all__."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["_nonexistent_function_xyz"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestDotenvFunctionNames
# ---------------------------------------------------------------------------

class TestDotenvFunctionNames:
    def test_load_dotenv_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "load_dotenv.__name__.__eq__",
                "args": ["load_dotenv"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_dotenv_values_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dotenv_values.__name__.__eq__",
                "args": ["dotenv_values"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_find_dotenv_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "find_dotenv.__name__.__eq__",
                "args": ["find_dotenv"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_functions_are_callable(self, dotenv_mod):
        """Direct check: all public functions are callable."""
        assert callable(dotenv_mod.load_dotenv)
        assert callable(dotenv_mod.dotenv_values)
        assert callable(dotenv_mod.find_dotenv)
        assert callable(dotenv_mod.get_key)
        assert callable(dotenv_mod.set_key)
        assert callable(dotenv_mod.unset_key)


# ---------------------------------------------------------------------------
# TestDotenvParse
# ---------------------------------------------------------------------------

class TestDotenvParse:
    def test_nonexistent_path_empty_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dotenv_values",
                "args": ["/nonexistent/.env"],
                "method": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_nonexistent_path_get_returns_none(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dotenv_values",
                "args": ["/nonexistent/.env"],
                "method": "get",
                "method_args": ["ANY_KEY"],
                "expected": None,
            },
        })
        assert ok, msg

    def test_dotenv_values_nonexistent_is_empty(self, dotenv_mod):
        """Direct check: dotenv_values with nonexistent file returns empty mapping."""
        result = dotenv_mod.dotenv_values("/nonexistent/.env")
        assert len(result) == 0
        assert result.get("FOO") is None

    def test_dotenv_values_result_is_mapping(self, dotenv_mod):
        """Direct check: dotenv_values result supports dict-like access."""
        result = dotenv_mod.dotenv_values("/nonexistent/.env")
        assert hasattr(result, "get")
        assert hasattr(result, "__len__")
        assert hasattr(result, "keys")


# ---------------------------------------------------------------------------
# TestDotenvAll — all 12 dotenv invariants must pass
# ---------------------------------------------------------------------------

class TestDotenvAll:
    def test_all_pass(self, dotenv_spec, dotenv_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dotenv_spec, dotenv_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, dotenv_spec, dotenv_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dotenv_spec, dotenv_mod)
        assert len(results) == 12

    def test_filter_by_category_version(self, dotenv_spec, dotenv_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dotenv_spec, dotenv_mod, filter_category="version")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_api(self, dotenv_spec, dotenv_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dotenv_spec, dotenv_mod, filter_category="api")
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_by_category_function_names(self, dotenv_spec, dotenv_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dotenv_spec, dotenv_mod, filter_category="function_names")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_parse(self, dotenv_spec, dotenv_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dotenv_spec, dotenv_mod, filter_category="parse")
        assert len(results) == 2
        assert all(r.passed for r in results)
