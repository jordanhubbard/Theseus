"""
Tests for the stevedore Z-layer behavioral spec (stevedore.zspec.zsdl).

Covers:
  - SpecLoader: loading stevedore spec via python_module backend
  - python_call_eq handler with stevedore-specific patterns
  - InvariantRunner integration: all 14 invariants pass
  - CLI: verify-behavior runs stevedore.zspec.json end-to-end

Categories verified:
  version (2)          — __name__ and __package__ identity (stevedore 5.x has no __version__)
  classes (3)          — ExtensionManager, DriverManager, HookManager class names
  manager (3)          — empty-namespace extensions len, names len, namespace attr
  manager_methods (3)  — map, names, map_method present in ExtensionManager class dict
  extension (1)        — extension.Extension.__name__ == 'Extension'
  public_api (2)       — __all__ contains ExtensionManager and DriverManager
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

STEVEDORE_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "stevedore.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def stevedore_spec():
    return vb.SpecLoader().load(STEVEDORE_SPEC_PATH)


@pytest.fixture(scope="module")
def stevedore_mod(stevedore_spec):
    return vb.LibraryLoader().load(stevedore_spec["library"])


@pytest.fixture(scope="module")
def constants_map(stevedore_spec):
    return vb.InvariantRunner().build_constants_map(stevedore_spec["constants"])


@pytest.fixture(scope="module")
def registry(stevedore_mod, constants_map):
    return vb.PatternRegistry(stevedore_mod, constants_map)


# ---------------------------------------------------------------------------
# TestStevedoreSpecLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestStevedoreSpecLoader:
    def test_loads_stevedore_spec(self, stevedore_spec):
        assert isinstance(stevedore_spec, dict)

    def test_all_required_sections_present(self, stevedore_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in stevedore_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, stevedore_spec):
        assert stevedore_spec["library"]["backend"] == "python_module"

    def test_module_name_is_stevedore(self, stevedore_spec):
        assert stevedore_spec["library"]["module_name"] == "stevedore"

    def test_loads_stevedore_module(self, stevedore_mod):
        import stevedore
        assert stevedore_mod is stevedore

    def test_all_invariant_kinds_known(self, stevedore_spec):
        for inv in stevedore_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, stevedore_spec):
        ids = [inv["id"] for inv in stevedore_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_14(self, stevedore_spec):
        assert len(stevedore_spec["invariants"]) == 14


# ---------------------------------------------------------------------------
# TestStevedoreVersion
# ---------------------------------------------------------------------------

class TestStevedoreVersion:
    def test_module_name_eq(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__name__.__eq__",
                "args": ["stevedore"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_package_eq(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__package__.__eq__",
                "args": ["stevedore"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_module_name_is_string(self, stevedore_mod):
        assert isinstance(stevedore_mod.__name__, str)
        assert stevedore_mod.__name__ == "stevedore"

    def test_metadata_version_has_dot(self):
        import importlib.metadata
        v = importlib.metadata.version("stevedore")
        assert "." in v
        assert isinstance(v, str)


# ---------------------------------------------------------------------------
# TestStevedoreClasses
# ---------------------------------------------------------------------------

class TestStevedoreClasses:
    def test_extension_manager_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager.__name__.__eq__",
                "args": ["ExtensionManager"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_driver_manager_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "DriverManager.__name__.__eq__",
                "args": ["DriverManager"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_hook_manager_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HookManager.__name__.__eq__",
                "args": ["HookManager"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_classes_are_types(self, stevedore_mod):
        for cls_name in ("ExtensionManager", "DriverManager", "HookManager",
                         "EnabledExtensionManager", "NamedExtensionManager"):
            cls = getattr(stevedore_mod, cls_name)
            assert isinstance(cls, type), f"{cls_name} is not a type"

    def test_enabled_extension_manager_exists(self, stevedore_mod):
        assert hasattr(stevedore_mod, "EnabledExtensionManager")
        assert stevedore_mod.EnabledExtensionManager.__name__ == "EnabledExtensionManager"

    def test_named_extension_manager_exists(self, stevedore_mod):
        assert hasattr(stevedore_mod, "NamedExtensionManager")
        assert stevedore_mod.NamedExtensionManager.__name__ == "NamedExtensionManager"


# ---------------------------------------------------------------------------
# TestStevedoreManager
# ---------------------------------------------------------------------------

_NONEXISTENT_NS = "totally.nonexistent.namespace.xyz"


class TestStevedoreManager:
    def test_empty_namespace_extensions_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager",
                "args": [_NONEXISTENT_NS],
                "kwargs": {"invoke_on_load": False},
                "method": "extensions",
                "method_chain": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_empty_namespace_names_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager",
                "args": [_NONEXISTENT_NS],
                "kwargs": {"invoke_on_load": False},
                "method": "names",
                "method_chain": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_namespace_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager",
                "args": [_NONEXISTENT_NS],
                "kwargs": {"invoke_on_load": False},
                "method": "namespace",
                "expected": _NONEXISTENT_NS,
            },
        })
        assert ok, msg

    def test_manager_creates_without_error(self, stevedore_mod):
        mgr = stevedore_mod.ExtensionManager(
            namespace=_NONEXISTENT_NS,
            invoke_on_load=False,
        )
        assert mgr is not None

    def test_names_returns_list(self, stevedore_mod):
        mgr = stevedore_mod.ExtensionManager(
            namespace=_NONEXISTENT_NS,
            invoke_on_load=False,
        )
        result = list(mgr.names())
        assert isinstance(result, list)
        assert len(result) == 0

    def test_extensions_is_list(self, stevedore_mod):
        mgr = stevedore_mod.ExtensionManager(
            namespace=_NONEXISTENT_NS,
            invoke_on_load=False,
        )
        assert isinstance(mgr.extensions, list)
        assert len(mgr.extensions) == 0


# ---------------------------------------------------------------------------
# TestStevedoreManagerMethods
# ---------------------------------------------------------------------------

class TestStevedoreManagerMethods:
    def test_has_map(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager.__dict__.__contains__",
                "args": ["map"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_has_names(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager.__dict__.__contains__",
                "args": ["names"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_has_map_method(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExtensionManager.__dict__.__contains__",
                "args": ["map_method"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_map_is_callable(self, stevedore_mod):
        mgr = stevedore_mod.ExtensionManager(
            namespace=_NONEXISTENT_NS,
            invoke_on_load=False,
        )
        assert callable(mgr.map)

    def test_names_is_callable(self, stevedore_mod):
        mgr = stevedore_mod.ExtensionManager(
            namespace=_NONEXISTENT_NS,
            invoke_on_load=False,
        )
        assert callable(mgr.names)

    def test_map_method_is_callable(self, stevedore_mod):
        mgr = stevedore_mod.ExtensionManager(
            namespace=_NONEXISTENT_NS,
            invoke_on_load=False,
        )
        assert callable(mgr.map_method)


# ---------------------------------------------------------------------------
# TestStevedoreExtension
# ---------------------------------------------------------------------------

class TestStevedoreExtension:
    def test_extension_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "extension.Extension.__name__.__eq__",
                "args": ["Extension"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_extension_submodule_accessible(self, stevedore_mod):
        assert hasattr(stevedore_mod, "extension")
        ext_mod = stevedore_mod.extension
        assert hasattr(ext_mod, "Extension")

    def test_extension_class_is_type(self, stevedore_mod):
        from stevedore import extension
        assert isinstance(extension.Extension, type)


# ---------------------------------------------------------------------------
# TestStevedorePublicAPI
# ---------------------------------------------------------------------------

class TestStevedorePublicAPI:
    def test_all_contains_extension_manager(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["ExtensionManager"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_contains_driver_manager(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__all__.__contains__",
                "args": ["DriverManager"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_is_list(self, stevedore_mod):
        assert isinstance(stevedore_mod.__all__, list)

    def test_all_contains_five_managers(self, stevedore_mod):
        expected = {
            "ExtensionManager",
            "DriverManager",
            "HookManager",
            "EnabledExtensionManager",
            "NamedExtensionManager",
        }
        for name in expected:
            assert name in stevedore_mod.__all__, f"{name} missing from __all__"


# ---------------------------------------------------------------------------
# TestStevedoreAll — all 14 invariants must pass
# ---------------------------------------------------------------------------

class TestStevedoreAll:
    def test_all_pass(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod)
        assert len(results) == 14

    def test_no_skips(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_classes_category(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod, filter_category="classes")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_manager_category(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod, filter_category="manager")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_manager_methods_category(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod, filter_category="manager_methods")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_extension_category(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod, filter_category="extension")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_public_api_category(self, stevedore_spec, stevedore_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(stevedore_spec, stevedore_mod, filter_category="public_api")
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestStevedoreCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(STEVEDORE_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(STEVEDORE_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "14 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(STEVEDORE_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "stevedore.version" in out
        assert "stevedore.classes" in out

    def test_filter_flag_version(self, capsys):
        vb.main([str(STEVEDORE_SPEC_PATH), "--filter", "version", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(STEVEDORE_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 14
        assert all(r["passed"] for r in data)
