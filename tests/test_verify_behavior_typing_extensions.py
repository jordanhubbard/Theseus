"""
Tests for the python_module backend and typing_extensions-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestTypingExtensionsLoader: loading typing_extensions via the python_module backend
  - TestTypingExtensionsVersion: version category invariants
  - TestTypingExtensionsNames: names category invariants (Literal, TypedDict, Protocol, Final, Annotated)
  - TestTypingExtensionsIntrospection: introspection category invariants (get_args, get_origin, get_type_hints)
  - TestTypingExtensionsRuntimeHelpers: runtime_helpers category (reveal_type, assert_never, get_overloads)
  - TestTypingExtensionsAll: all 13 invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

TE_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "typing_extensions.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def te_spec():
    return vb.SpecLoader().load(TE_SPEC_PATH)


@pytest.fixture(scope="module")
def te_mod(te_spec):
    return vb.LibraryLoader().load(te_spec["library"])


@pytest.fixture(scope="module")
def constants_map(te_spec):
    return vb.InvariantRunner().build_constants_map(te_spec["constants"])


@pytest.fixture(scope="module")
def registry(te_mod, constants_map):
    return vb.PatternRegistry(te_mod, constants_map)


# ---------------------------------------------------------------------------
# TestTypingExtensionsLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestTypingExtensionsLoader:
    def test_loads_spec(self, te_spec):
        assert isinstance(te_spec, dict)

    def test_all_required_sections_present(self, te_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in te_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, te_spec):
        assert te_spec["library"]["backend"] == "python_module"

    def test_module_name_is_typing_extensions(self, te_spec):
        assert te_spec["library"]["module_name"] == "typing_extensions"

    def test_loads_typing_extensions_module(self, te_mod):
        import typing_extensions
        assert te_mod is typing_extensions

    def test_all_invariant_kinds_known(self, te_spec):
        for inv in te_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, te_spec):
        ids = [inv["id"] for inv in te_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count(self, te_spec):
        assert len(te_spec["invariants"]) == 13


# ---------------------------------------------------------------------------
# TestTypingExtensionsVersion
# ---------------------------------------------------------------------------

class TestTypingExtensionsVersion:
    def test_version_satisfies_smoke(self, registry):
        """The smoke-test invariant verifies get_args.__name__ == 'get_args'."""
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_args.__name__.__eq__",
                "args": ["get_args"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_metadata_version_contains_dot(self, te_mod):
        """typing_extensions version from importlib.metadata contains a dot."""
        import importlib.metadata
        ver = importlib.metadata.version("typing_extensions")
        assert "." in ver, f"Expected version with dot, got: {ver!r}"

    def test_metadata_version_starts_with_digit(self):
        import importlib.metadata
        ver = importlib.metadata.version("typing_extensions")
        assert ver[0].isdigit(), f"Expected version to start with digit, got: {ver!r}"


# ---------------------------------------------------------------------------
# TestTypingExtensionsNames
# ---------------------------------------------------------------------------

class TestTypingExtensionsNames:
    def test_Literal_present(self, registry):
        # Match the spec's substring approach — the exact internal class name
        # has shifted across typing_extensions releases (_TypedCacheSpecialForm
        # vs _SpecialForm depending on version + Python release).
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Literal.__class__.__name__.__contains__",
                "args": ["SpecialForm"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TypedDict_present(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "TypedDict.__class__.__name__.__eq__",
                "args": ["_TypedDictSpecialForm"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_Protocol_present(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Protocol.__class__.__name__.__eq__",
                "args": ["_ProtocolMeta"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_Final_present(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Final.__class__.__name__.__eq__",
                "args": ["_SpecialForm"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_Annotated_present(self, registry):
        # Same module-name check the spec uses — survives the case where
        # typing_extensions re-exports stdlib's Annotated (whose __class__
        # is _AnnotatedAlias, not anything containing 'SpecialForm').
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Annotated.__module__.__contains__",
                "args": ["typing"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_key_names_exist_on_module(self, te_mod):
        """Direct check: all required names are module attributes."""
        for name in ("Literal", "TypedDict", "Protocol", "Final", "Annotated",
                     "get_args", "get_origin", "get_type_hints", "get_overloads",
                     "reveal_type", "assert_never"):
            assert hasattr(te_mod, name), f"Missing attribute: {name}"


# ---------------------------------------------------------------------------
# TestTypingExtensionsIntrospection
# ---------------------------------------------------------------------------

class TestTypingExtensionsIntrospection:
    def test_get_args_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_args.__name__.__eq__",
                "args": ["get_args"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_get_origin_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_origin.__name__.__eq__",
                "args": ["get_origin"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_get_type_hints_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_type_hints.__name__.__eq__",
                "args": ["get_type_hints"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_get_args_is_callable(self, te_mod):
        assert callable(te_mod.get_args)

    def test_get_origin_is_callable(self, te_mod):
        assert callable(te_mod.get_origin)

    def test_get_type_hints_is_callable(self, te_mod):
        assert callable(te_mod.get_type_hints)

    def test_get_args_plain_type_returns_empty(self, te_mod):
        """get_args(int) == () — plain types have no type parameters."""
        assert te_mod.get_args(int) == ()
        assert te_mod.get_args(str) == ()

    def test_get_origin_plain_type_returns_none(self, te_mod):
        """get_origin(int) is None — plain types have no parameterized origin."""
        assert te_mod.get_origin(int) is None


# ---------------------------------------------------------------------------
# TestTypingExtensionsRuntimeHelpers
# ---------------------------------------------------------------------------

class TestTypingExtensionsRuntimeHelpers:
    def test_reveal_type_int(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "reveal_type",
                "args": [42],
                "expected": 42,
            },
        })
        assert ok, msg

    def test_reveal_type_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "reveal_type",
                "args": ["hello"],
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_assert_never_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "assert_never.__name__.__eq__",
                "args": ["assert_never"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_get_overloads_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_overloads.__name__.__eq__",
                "args": ["get_overloads"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_reveal_type_returns_value_unchanged(self, te_mod):
        """reveal_type is a runtime noop — it returns its argument unchanged."""
        assert te_mod.reveal_type(42) == 42
        assert te_mod.reveal_type("hello") == "hello"
        assert te_mod.reveal_type([1, 2, 3]) == [1, 2, 3]

    def test_get_overloads_nonoverloaded_fn_returns_empty(self, te_mod):
        """get_overloads(fn) == [] for a function without @overload variants."""
        def plain(): pass
        assert te_mod.get_overloads(plain) == []
        assert te_mod.get_overloads(len) == []

    def test_assert_never_is_callable(self, te_mod):
        assert callable(te_mod.assert_never)


# ---------------------------------------------------------------------------
# TestTypingExtensionsAll — all 13 invariants must pass
# ---------------------------------------------------------------------------

class TestTypingExtensionsAll:
    def test_all_pass(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod)
        assert len(results) == 13

    def test_filter_by_category_version(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod, filter_category="version")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_names(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod, filter_category="names")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_category_introspection(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod, filter_category="introspection")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_runtime_helpers(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod, filter_category="runtime_helpers")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_no_skipped_invariants(self, te_spec, te_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(te_spec, te_mod)
        skipped = [r for r in results if r.skip_reason is not None]
        assert not skipped, f"Unexpected skips: {[r.inv_id for r in skipped]}"
