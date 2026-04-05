"""
Tests for the python_module backend and packaging-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - PackagingModuleLoader: loading packaging via the python_module backend
  - One test class per invariant category:
      - TestPackagingVersion: version field extraction (PEP 440)
      - TestPackagingPrerelease: pre-release and dev-release detection
      - TestPackagingSpecifier: SpecifierSet.contains() evaluation
      - TestPackagingUtils: canonicalize_name per PEP 503
      - TestPackagingRequirement: Specifier attribute parsing (PEP 440/508)
  - TestPackagingAll: all 24 invariants pass; count check
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PACKAGING_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "packaging.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def packaging_spec():
    return vb.SpecLoader().load(PACKAGING_SPEC_PATH)


@pytest.fixture(scope="module")
def packaging_mod(packaging_spec):
    return vb.LibraryLoader().load(packaging_spec["library"])


@pytest.fixture(scope="module")
def constants_map(packaging_spec):
    return vb.InvariantRunner().build_constants_map(packaging_spec["constants"])


@pytest.fixture(scope="module")
def registry(packaging_mod, constants_map):
    # The harness's _check_spec_version() imports packaging.specifiers and
    # packaging.version as a side effect of the version-constraint check.
    # When running unit tests against the registry directly (without going
    # through InvariantRunner.run_all), those imports have not happened yet,
    # so the dotted-path resolver cannot find 'version.Version' et al. on
    # the bare packaging module.  Import the submodules here to replicate
    # the same module state that verify_behavior.py establishes before it
    # runs any invariants.
    import packaging.version       # noqa: F401 — side-effect: sets packaging.version
    import packaging.specifiers    # noqa: F401 — side-effect: sets packaging.specifiers
    import packaging.utils         # noqa: F401 — side-effect: sets packaging.utils
    return vb.PatternRegistry(packaging_mod, constants_map)


# ---------------------------------------------------------------------------
# PackagingModuleLoader
# ---------------------------------------------------------------------------

class TestPackagingModuleLoader:
    def test_loads_packaging_spec(self, packaging_spec):
        assert isinstance(packaging_spec, dict)

    def test_all_required_sections_present(self, packaging_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in packaging_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, packaging_spec):
        assert packaging_spec["library"]["backend"] == "python_module"

    def test_module_name_is_packaging(self, packaging_spec):
        assert packaging_spec["library"]["module_name"] == "packaging"

    def test_loads_packaging_module(self, packaging_mod):
        import packaging
        assert packaging_mod is packaging

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz",
            })

    def test_all_invariant_kinds_known(self, packaging_spec):
        for inv in packaging_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, packaging_spec):
        ids = [inv["id"] for inv in packaging_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestPackagingVersion — PEP 440 version field extraction
# ---------------------------------------------------------------------------

class TestPackagingVersion:
    def test_version_major(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
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
                "function": "version.Version",
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
                "function": "version.Version",
                "args": ["1.2.3"],
                "method": "micro",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_stable_not_prerelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.2.3"],
                "method": "is_prerelease",
                "expected": False,
            },
        })
        assert ok, msg

    def test_stable_not_devrelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.2.3"],
                "method": "is_devrelease",
                "expected": False,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_major(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.2.3"],
                "method": "major",
                "expected": 99,
            },
        })
        assert not ok

    def test_fails_on_invalid_version_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["not-a-version"],
                "method": "major",
                "expected": 0,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPackagingPrerelease — PEP 440 pre-release detection
# ---------------------------------------------------------------------------

class TestPackagingPrerelease:
    def test_alpha_is_prerelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.0a1"],
                "method": "is_prerelease",
                "expected": True,
            },
        })
        assert ok, msg

    def test_dev_is_devrelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.0.dev1"],
                "method": "is_devrelease",
                "expected": True,
            },
        })
        assert ok, msg

    def test_dev_is_also_prerelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.0.dev1"],
                "method": "is_prerelease",
                "expected": True,
            },
        })
        assert ok, msg

    def test_rc_is_prerelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["2.0rc1"],
                "method": "is_prerelease",
                "expected": True,
            },
        })
        assert ok, msg

    def test_stable_is_not_prerelease(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.0.0"],
                "method": "is_prerelease",
                "expected": False,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_prerelease_expectation(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.Version",
                "args": ["1.0a1"],
                "method": "is_prerelease",
                "expected": False,  # wrong — alpha IS a pre-release
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPackagingSpecifier — SpecifierSet.contains() evaluation (PEP 440)
# ---------------------------------------------------------------------------

class TestPackagingSpecifier:
    def test_in_range(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": [">=1.0,<2.0"],
                "method": "contains",
                "method_args": ["1.5"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_below_lower_bound(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": [">=1.0,<2.0"],
                "method": "contains",
                "method_args": ["0.9"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_at_upper_bound_excluded(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": [">=1.0,<2.0"],
                "method": "contains",
                "method_args": ["2.0"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_at_lower_bound_included(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": [">=1.0,<2.0"],
                "method": "contains",
                "method_args": ["1.0"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_exact_pin_match(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": ["==1.2.3"],
                "method": "contains",
                "method_args": ["1.2.3"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_exact_pin_mismatch(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": ["==1.2.3"],
                "method": "contains",
                "method_args": ["1.2.4"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_empty_specifier_matches_all(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": [""],
                "method": "contains",
                "method_args": ["99.0"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_result(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.SpecifierSet",
                "args": [">=1.0,<2.0"],
                "method": "contains",
                "method_args": ["0.9"],
                "expected": True,  # wrong — 0.9 is not in >=1.0
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPackagingUtils — canonicalize_name per PEP 503
# ---------------------------------------------------------------------------

class TestPackagingUtils:
    def test_uppercase_pillow(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utils.canonicalize_name",
                "args": ["Pillow"],
                "expected": "pillow",
            },
        })
        assert ok, msg

    def test_underscore_to_dash(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utils.canonicalize_name",
                "args": ["my_package"],
                "expected": "my-package",
            },
        })
        assert ok, msg

    def test_django_lowercase(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utils.canonicalize_name",
                "args": ["Django"],
                "expected": "django",
            },
        })
        assert ok, msg

    def test_mixed_separators(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utils.canonicalize_name",
                "args": ["Foo_Bar-Baz"],
                "expected": "foo-bar-baz",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_expected(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utils.canonicalize_name",
                "args": ["Pillow"],
                "expected": "Pillow",  # wrong — should be lowercase
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPackagingRequirement — Specifier attribute parsing (PEP 440/508)
# ---------------------------------------------------------------------------

class TestPackagingRequirement:
    def test_specifier_operator_ge(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.Specifier",
                "args": [">=2.0"],
                "method": "operator",
                "expected": ">=",
            },
        })
        assert ok, msg

    def test_specifier_version_ge(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.Specifier",
                "args": [">=2.0"],
                "method": "version",
                "expected": "2.0",
            },
        })
        assert ok, msg

    def test_specifier_pin_operator(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.Specifier",
                "args": ["==1.2.3"],
                "method": "operator",
                "expected": "==",
            },
        })
        assert ok, msg

    def test_specifier_pin_version(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.Specifier",
                "args": ["==1.2.3"],
                "method": "version",
                "expected": "1.2.3",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_operator(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "specifiers.Specifier",
                "args": [">=2.0"],
                "method": "operator",
                "expected": "==",  # wrong
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPackagingAll — all 24 invariants pass; total count
# ---------------------------------------------------------------------------

class TestPackagingAll:
    def test_all_pass(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod)
        assert len(results) == 24

    def test_no_skips(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_version_category(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod, filter_category="version")
        # major, minor, micro, is_prerelease_stable, is_devrelease_stable = 5
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_prerelease_category(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod, filter_category="prerelease")
        # alpha_is_prerelease, dev_is_devrelease, dev_is_prerelease, rc_is_prerelease = 4
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_specifier_category(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod, filter_category="specifier")
        # in_range, below_range, at_upper, at_lower, exact_match, exact_mismatch, empty = 7
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_filter_utils_category(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod, filter_category="utils")
        # uppercase, underscore, django, mixed_seps = 4
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_requirement_category(self, packaging_spec, packaging_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(packaging_spec, packaging_mod, filter_category="requirement")
        # operator, version, pin_operator, pin_version = 4
        assert len(results) == 4
        assert all(r.passed for r in results)
