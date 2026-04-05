"""
Tests for the python_module backend and setuptools-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestSetuptoolsLoader: loading setuptools via the python_module backend
  - TestSetuptoolsVersion: version category invariants
  - TestSetuptoolsApi: api category invariants (find_packages, find_namespace_packages)
  - TestSetuptoolsPackaging: packaging category invariants (Version class)
  - TestSetuptoolsExtension: extension category invariants (Extension object)
  - TestSetuptoolsAll: all 14 setuptools invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

SETUPTOOLS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "setuptools.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def setuptools_spec():
    return vb.SpecLoader().load(SETUPTOOLS_SPEC_PATH)


@pytest.fixture(scope="module")
def setuptools_mod(setuptools_spec):
    return vb.LibraryLoader().load(setuptools_spec["library"])


@pytest.fixture(scope="module")
def constants_map(setuptools_spec):
    return vb.InvariantRunner().build_constants_map(setuptools_spec["constants"])


@pytest.fixture(scope="module")
def registry(setuptools_mod, constants_map):
    return vb.PatternRegistry(setuptools_mod, constants_map)


# ---------------------------------------------------------------------------
# TestSetuptoolsLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestSetuptoolsLoader:
    def test_loads_setuptools_spec(self, setuptools_spec):
        assert isinstance(setuptools_spec, dict)

    def test_all_required_sections_present(self, setuptools_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in setuptools_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, setuptools_spec):
        assert setuptools_spec["library"]["backend"] == "python_module"

    def test_module_name_is_setuptools(self, setuptools_spec):
        assert setuptools_spec["library"]["module_name"] == "setuptools"

    def test_loads_setuptools_module(self, setuptools_mod):
        import setuptools
        assert setuptools_mod is setuptools

    def test_all_invariant_kinds_known(self, setuptools_spec):
        for inv in setuptools_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, setuptools_spec):
        ids = [inv["id"] for inv in setuptools_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestSetuptoolsVersion
# ---------------------------------------------------------------------------

class TestSetuptoolsVersion:
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

    def test_version_has_three_parts(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.split",
                "args": ["."],
                "method": "__len__",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_version_direct_check(self, setuptools_mod):
        """Direct check: __version__ is a non-empty string with at least one dot."""
        v = setuptools_mod.__version__
        assert isinstance(v, str)
        assert len(v) > 0
        assert "." in v


# ---------------------------------------------------------------------------
# TestSetuptoolsApi
# ---------------------------------------------------------------------------

class TestSetuptoolsApi:
    def test_find_packages_class_is_method(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "find_packages.__class__.__name__.__eq__",
                "args": ["method"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_find_namespace_packages_class_is_method(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "find_namespace_packages.__class__.__name__.__eq__",
                "args": ["method"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_find_packages_callable_directly(self, setuptools_mod):
        """Direct check: find_packages and find_namespace_packages are callable."""
        assert callable(setuptools_mod.find_packages)
        assert callable(setuptools_mod.find_namespace_packages)

    def test_setup_callable_directly(self, setuptools_mod):
        """Direct check: setup() entry point is callable."""
        assert callable(setuptools_mod.setup)


# ---------------------------------------------------------------------------
# TestSetuptoolsPackaging
# ---------------------------------------------------------------------------

class TestSetuptoolsPackaging:
    def test_version_str_roundtrip(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.2.3"],
                "method": "__str__",
                "method_args": [],
                "expected": "1.2.3",
            },
        })
        assert ok, msg

    def test_version_major(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.2.3"],
                "method": "major",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_version_minor(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.2.3"],
                "method": "minor",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_version_micro(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.2.3"],
                "method": "micro",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_version_epoch_zero(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.2.3"],
                "method": "epoch",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_stable_not_prerelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.2.3"],
                "method": "is_prerelease",
                "expected": False,
            },
        })
        assert ok, msg

    def test_prerelease_detected(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.0.0a1"],
                "method": "is_prerelease",
                "expected": True,
            },
        })
        assert ok, msg

    def test_prerelease_str_normalized(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "_vendor.packaging.version.Version",
                "args": ["1.0.0a1"],
                "method": "__str__",
                "method_args": [],
                "expected": "1.0.0a1",
            },
        })
        assert ok, msg

    def test_version_comparison_directly(self, setuptools_mod):
        """Direct check: Version comparison operators work as expected."""
        Version = setuptools_mod._vendor.packaging.version.Version
        v = Version("1.2.3")
        assert v < Version("2.0.0")
        assert v >= Version("1.0.0")
        assert v == Version("1.2.3")
        assert v != Version("2.0.0")

    def test_version_prerelease_directly(self, setuptools_mod):
        """Direct check: pre-release and stable versions are correctly classified."""
        Version = setuptools_mod._vendor.packaging.version.Version
        assert not Version("1.2.3").is_prerelease
        assert Version("1.0.0a1").is_prerelease
        assert Version("1.0.0b1").is_prerelease
        assert Version("1.0.0rc1").is_prerelease


# ---------------------------------------------------------------------------
# TestSetuptoolsExtension
# ---------------------------------------------------------------------------

class TestSetuptoolsExtension:
    def test_extension_name_attribute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Extension",
                "args": ["mymodule", ["mymodule.c"]],
                "method": "name",
                "expected": "mymodule",
            },
        })
        assert ok, msg

    def test_extension_directly(self, setuptools_mod):
        """Direct check: Extension carries name and sources."""
        ext = setuptools_mod.Extension("mymodule", ["mymodule.c"])
        assert ext.name == "mymodule"
        assert ext.sources == ["mymodule.c"]


# ---------------------------------------------------------------------------
# TestSetuptoolsAll — all 14 setuptools invariants must pass
# ---------------------------------------------------------------------------

class TestSetuptoolsAll:
    def test_all_pass(self, setuptools_spec, setuptools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(setuptools_spec, setuptools_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, setuptools_spec, setuptools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(setuptools_spec, setuptools_mod)
        assert len(results) == 14

    def test_filter_by_category_version(self, setuptools_spec, setuptools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(setuptools_spec, setuptools_mod, filter_category="version")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_api(self, setuptools_spec, setuptools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(setuptools_spec, setuptools_mod, filter_category="api")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_packaging(self, setuptools_spec, setuptools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(setuptools_spec, setuptools_mod, filter_category="packaging")
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_filter_by_category_extension(self, setuptools_spec, setuptools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(setuptools_spec, setuptools_mod, filter_category="extension")
        assert len(results) == 1
        assert all(r.passed for r in results)
