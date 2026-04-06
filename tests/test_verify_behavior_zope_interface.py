"""
Tests for the python_module backend and zope.interface-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestZopeInterfaceLoader: loading zope.interface via the python_module backend
  - TestZopeInterfaceVersion: version category invariants (smoke test via Interface.__name__)
  - TestZopeInterfaceInterface: interface category invariants (__name__, __module__, metaclass)
  - TestZopeInterfaceClassNames: class_names category (implementer, providedBy, implementedBy, etc.)
  - TestZopeInterfaceModuleAttrs: module_attrs category (__name__, __package__)
  - TestZopeInterfaceImplementerClass: implementer_class category (is a class/type)
  - TestZopeInterfaceAll: all 13 invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

ZI_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "zope_interface.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def zi_spec():
    return vb.SpecLoader().load(ZI_SPEC_PATH)


@pytest.fixture(scope="module")
def zi_mod(zi_spec):
    return vb.LibraryLoader().load(zi_spec["library"])


@pytest.fixture(scope="module")
def constants_map(zi_spec):
    return vb.InvariantRunner().build_constants_map(zi_spec["constants"])


@pytest.fixture(scope="module")
def registry(zi_mod, constants_map):
    return vb.PatternRegistry(zi_mod, constants_map)


# ---------------------------------------------------------------------------
# TestZopeInterfaceLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestZopeInterfaceLoader:
    def test_loads_spec(self, zi_spec):
        assert isinstance(zi_spec, dict)

    def test_all_required_sections_present(self, zi_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in zi_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, zi_spec):
        assert zi_spec["library"]["backend"] == "python_module"

    def test_module_name_is_zope_interface(self, zi_spec):
        assert zi_spec["library"]["module_name"] == "zope.interface"

    def test_loads_zope_interface_module(self, zi_mod):
        import zope.interface
        assert zi_mod is zope.interface

    def test_all_invariant_kinds_known(self, zi_spec):
        for inv in zi_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, zi_spec):
        ids = [inv["id"] for inv in zi_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count(self, zi_spec):
        assert len(zi_spec["invariants"]) == 13


# ---------------------------------------------------------------------------
# TestZopeInterfaceVersion
# ---------------------------------------------------------------------------

class TestZopeInterfaceVersion:
    def test_interface_name_smoke(self, registry):
        """Smoke test: Interface.__name__ == 'Interface' confirms module loads."""
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Interface.__name__.__eq__",
                "args": ["Interface"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_metadata_version_contains_dot(self):
        """zope.interface version from importlib.metadata contains a dot."""
        import importlib.metadata
        ver = importlib.metadata.version("zope.interface")
        assert "." in ver, f"Expected version with dot, got: {ver!r}"

    def test_metadata_version_starts_with_digit(self):
        import importlib.metadata
        ver = importlib.metadata.version("zope.interface")
        assert ver[0].isdigit(), f"Expected version to start with digit, got: {ver!r}"


# ---------------------------------------------------------------------------
# TestZopeInterfaceInterface
# ---------------------------------------------------------------------------

class TestZopeInterfaceInterface:
    def test_interface_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Interface.__name__.__eq__",
                "args": ["Interface"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_interface_module_contains_zope(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Interface.__module__.__contains__",
                "args": ["zope"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_interface_module_eq(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Interface.__module__.__eq__",
                "args": ["zope.interface"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_interface_metaclass_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Interface.__class__.__name__.__eq__",
                "args": ["InterfaceClass"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_interface_is_accessible(self, zi_mod):
        """Direct check: Interface is accessible as a module attribute."""
        assert hasattr(zi_mod, "Interface")
        assert zi_mod.Interface.__name__ == "Interface"
        assert zi_mod.Interface.__module__ == "zope.interface"

    def test_interface_metaclass_is_interfaceclass(self, zi_mod):
        """Direct check: type(Interface).__name__ == 'InterfaceClass'."""
        assert type(zi_mod.Interface).__name__ == "InterfaceClass"


# ---------------------------------------------------------------------------
# TestZopeInterfaceClassNames
# ---------------------------------------------------------------------------

class TestZopeInterfaceClassNames:
    def test_implementer_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "implementer.__name__.__eq__",
                "args": ["implementer"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_providedBy_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "providedBy.__name__.__eq__",
                "args": ["providedBy"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_implementedBy_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "implementedBy.__name__.__eq__",
                "args": ["implementedBy"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_directlyProvidedBy_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "directlyProvidedBy.__name__.__eq__",
                "args": ["directlyProvidedBy"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_alsoProvides_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "alsoProvides.__name__.__eq__",
                "args": ["alsoProvides"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_callables_accessible(self, zi_mod):
        """Direct check: all key callables are accessible as module attributes."""
        for name in ("implementer", "providedBy", "implementedBy",
                     "directlyProvidedBy", "alsoProvides"):
            assert hasattr(zi_mod, name), f"Missing attribute: {name}"
            assert callable(getattr(zi_mod, name)), f"Not callable: {name}"

    def test_callable_names_match(self, zi_mod):
        """Direct check: each callable's __name__ matches its attribute name."""
        names = ["implementer", "providedBy", "implementedBy",
                 "directlyProvidedBy", "alsoProvides"]
        for name in names:
            obj = getattr(zi_mod, name)
            assert obj.__name__ == name, \
                f"{name}.__name__ = {obj.__name__!r}, expected {name!r}"


# ---------------------------------------------------------------------------
# TestZopeInterfaceModuleAttrs
# ---------------------------------------------------------------------------

class TestZopeInterfaceModuleAttrs:
    def test_module_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__name__.__eq__",
                "args": ["zope.interface"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_package_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__package__.__eq__",
                "args": ["zope.interface"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_module_name_direct(self, zi_mod):
        """Direct check: module's __name__ is 'zope.interface'."""
        assert zi_mod.__name__ == "zope.interface"

    def test_package_name_direct(self, zi_mod):
        """Direct check: module's __package__ is 'zope.interface'."""
        assert zi_mod.__package__ == "zope.interface"


# ---------------------------------------------------------------------------
# TestZopeInterfaceImplementerClass
# ---------------------------------------------------------------------------

class TestZopeInterfaceImplementerClass:
    def test_implementer_is_type(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "implementer.__class__.__name__.__eq__",
                "args": ["type"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_implementer_is_class_directly(self, zi_mod):
        """Direct check: implementer is a class, not a plain function."""
        import inspect
        assert inspect.isclass(zi_mod.implementer)

    def test_implementer_metaclass_is_type(self, zi_mod):
        """Direct check: type(implementer) is type — it's a regular class."""
        assert type(zi_mod.implementer) is type


# ---------------------------------------------------------------------------
# TestZopeInterfaceAll — all 13 invariants must pass
# ---------------------------------------------------------------------------

class TestZopeInterfaceAll:
    def test_all_pass(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod)
        assert len(results) == 13

    def test_filter_by_category_version(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod, filter_category="version")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_interface(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod, filter_category="interface")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_category_class_names(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod, filter_category="class_names")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_category_module_attrs(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod, filter_category="module_attrs")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_implementer_class(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod, filter_category="implementer_class")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_no_skipped_invariants(self, zi_spec, zi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(zi_spec, zi_mod)
        skipped = [r for r in results if r.skip_reason is not None]
        assert not skipped, f"Unexpected skips: {[r.inv_id for r in skipped]}"
