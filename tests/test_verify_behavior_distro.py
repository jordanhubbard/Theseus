"""
Tests for the python_module backend and distro-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestDistroLoader: loading distro via the python_module backend
  - TestDistroVersion: version category invariants
  - TestDistroApiCallable: api_callable category invariants
  - TestDistroApiReturnsStr: api_returns_str category invariants
  - TestDistroInfo: info category invariants
  - TestDistroAll: all 15 distro invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

DISTRO_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "distro.zspec.json"

distro = pytest.importorskip("distro", reason="distro not installed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def distro_spec():
    return vb.SpecLoader().load(DISTRO_SPEC_PATH)


@pytest.fixture(scope="module")
def distro_mod(distro_spec):
    return vb.LibraryLoader().load(distro_spec["library"])


@pytest.fixture(scope="module")
def constants_map(distro_spec):
    return vb.InvariantRunner().build_constants_map(distro_spec["constants"])


@pytest.fixture(scope="module")
def registry(distro_mod, constants_map):
    return vb.PatternRegistry(distro_mod, constants_map)


# ---------------------------------------------------------------------------
# TestDistroLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestDistroLoader:
    def test_loads_distro_spec(self, distro_spec):
        assert isinstance(distro_spec, dict)

    def test_all_required_sections_present(self, distro_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in distro_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, distro_spec):
        assert distro_spec["library"]["backend"] == "python_module"

    def test_module_name_is_distro(self, distro_spec):
        assert distro_spec["library"]["module_name"] == "distro"

    def test_loads_distro_module(self, distro_mod):
        import distro
        assert distro_mod is distro

    def test_all_invariant_kinds_known(self, distro_spec):
        for inv in distro_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, distro_spec):
        ids = [inv["id"] for inv in distro_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestDistroVersion
# ---------------------------------------------------------------------------

class TestDistroVersion:
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

    def test_version_startswith_digit(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["1"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_is_string(self, distro_mod):
        """Direct check: __version__ is a non-empty string."""
        assert isinstance(distro_mod.__version__, str)
        assert len(distro_mod.__version__) > 0
        assert "." in distro_mod.__version__


# ---------------------------------------------------------------------------
# TestDistroApiCallable
# ---------------------------------------------------------------------------

class TestDistroApiCallable:
    def test_id_function_named_id(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "id.__name__.__eq__",
                "args": ["id"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_name_function_named_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name.__name__.__eq__",
                "args": ["name"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_function_named_version(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.__name__.__eq__",
                "args": ["version"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_like_function_named_like(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "like.__name__.__eq__",
                "args": ["like"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_codename_function_named_codename(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "codename.__name__.__eq__",
                "args": ["codename"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_functions_are_callable(self, distro_mod):
        """Direct check: all public API entries are callable."""
        for fn_name in ("id", "name", "version", "like", "codename", "info"):
            assert callable(getattr(distro_mod, fn_name)), \
                f"distro.{fn_name} is not callable"


# ---------------------------------------------------------------------------
# TestDistroApiReturnsStr
# ---------------------------------------------------------------------------

class TestDistroApiReturnsStr:
    def test_id_returns_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "id",
                "args": [],
                "method": "endswith",
                "method_args": [""],
                "expected": True,
            },
        })
        assert ok, msg

    def test_name_returns_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "name",
                "args": [],
                "method": "endswith",
                "method_args": [""],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_returns_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version",
                "args": [],
                "method": "endswith",
                "method_args": [""],
                "expected": True,
            },
        })
        assert ok, msg

    def test_like_returns_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "like",
                "args": [],
                "method": "endswith",
                "method_args": [""],
                "expected": True,
            },
        })
        assert ok, msg

    def test_codename_returns_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "codename",
                "args": [],
                "method": "endswith",
                "method_args": [""],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_api_functions_return_str(self, distro_mod):
        """Direct check: all public API functions return str on this platform."""
        for fn_name in ("id", "name", "version", "like", "codename"):
            result = getattr(distro_mod, fn_name)()
            assert isinstance(result, str), \
                f"distro.{fn_name}() returned {type(result).__name__}, expected str"

    def test_endswith_empty_wrong_value_fails(self, registry):
        """Sanity check: comparing result to wrong expected value fails."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "id",
                "args": [],
                "method": "endswith",
                "method_args": [""],
                "expected": False,  # endswith('') is always True, so False fails
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestDistroInfo
# ---------------------------------------------------------------------------

class TestDistroInfo:
    def test_info_has_id_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "info",
                "args": [],
                "method": "__contains__",
                "method_args": ["id"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_info_has_version_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "info",
                "args": [],
                "method": "__contains__",
                "method_args": ["version"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_info_has_like_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "info",
                "args": [],
                "method": "__contains__",
                "method_args": ["like"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_info_returns_dict(self, distro_mod):
        """Direct check: info() returns a dict with expected keys."""
        info = distro_mod.info()
        assert isinstance(info, dict)
        for key in ("id", "version", "version_parts", "like", "codename"):
            assert key in info, f"info() missing key: {key}"

    def test_info_id_matches_id_function(self, distro_mod):
        """Direct check: info()['id'] matches distro.id()."""
        assert distro_mod.info()["id"] == distro_mod.id()

    def test_info_version_parts_has_major(self, distro_mod):
        """Direct check: info()['version_parts'] has 'major' key."""
        assert "major" in distro_mod.info()["version_parts"]

    def test_info_missing_key_fails(self, registry):
        """Sanity check: checking for a non-existent key fails."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "info",
                "args": [],
                "method": "__contains__",
                "method_args": ["nonexistent_key_xyz"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestDistroAll — all 15 distro invariants must pass
# ---------------------------------------------------------------------------

class TestDistroAll:
    def test_all_pass(self, distro_spec, distro_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(distro_spec, distro_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, distro_spec, distro_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(distro_spec, distro_mod)
        assert len(results) == 15

    def test_filter_by_category_version(self, distro_spec, distro_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(distro_spec, distro_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_api_callable(self, distro_spec, distro_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(distro_spec, distro_mod, filter_category="api_callable")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_category_api_returns_str(self, distro_spec, distro_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(distro_spec, distro_mod, filter_category="api_returns_str")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_category_info(self, distro_spec, distro_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(distro_spec, distro_mod, filter_category="info")
        assert len(results) == 3
        assert all(r.passed for r in results)
