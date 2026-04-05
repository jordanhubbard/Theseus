"""
Tests for the pluggy Z-layer behavioral spec (pluggy.zspec.zsdl).

Covers:
  - SpecLoader: loading pluggy spec via python_module backend
  - python_call_eq handler with pluggy-specific patterns
  - InvariantRunner integration: all 13 invariants pass
  - CLI: verify-behavior runs pluggy.zspec.json end-to-end

Categories verified:
  version (2)      — __version__ is a string with a dot, starts with '1'
  plugin_manager (2) — PluginManager.project_name; PluginManager class name
  markers (4)      — HookspecMarker/HookimplMarker class names and project_name attribute
  pm_methods (5)   — get_plugins() empty; is_registered(None) False; register/unregister/get_plugins present
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PLUGGY_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pluggy.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pluggy_spec():
    return vb.SpecLoader().load(PLUGGY_SPEC_PATH)


@pytest.fixture(scope="module")
def pluggy_mod(pluggy_spec):
    return vb.LibraryLoader().load(pluggy_spec["library"])


@pytest.fixture(scope="module")
def constants_map(pluggy_spec):
    return vb.InvariantRunner().build_constants_map(pluggy_spec["constants"])


@pytest.fixture(scope="module")
def registry(pluggy_mod, constants_map):
    return vb.PatternRegistry(pluggy_mod, constants_map)


# ---------------------------------------------------------------------------
# TestPluggySpecLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestPluggySpecLoader:
    def test_loads_pluggy_spec(self, pluggy_spec):
        assert isinstance(pluggy_spec, dict)

    def test_all_required_sections_present(self, pluggy_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pluggy_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pluggy_spec):
        assert pluggy_spec["library"]["backend"] == "python_module"

    def test_module_name_is_pluggy(self, pluggy_spec):
        assert pluggy_spec["library"]["module_name"] == "pluggy"

    def test_loads_pluggy_module(self, pluggy_mod):
        import pluggy
        assert pluggy_mod is pluggy

    def test_all_invariant_kinds_known(self, pluggy_spec):
        for inv in pluggy_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pluggy_spec):
        ids = [inv["id"] for inv in pluggy_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestPluggyVersion
# ---------------------------------------------------------------------------

class TestPluggyVersion:
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

    def test_version_starts_with_digit(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["1"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_is_string(self, pluggy_mod):
        assert isinstance(pluggy_mod.__version__, str)
        assert len(pluggy_mod.__version__) > 0

    def test_version_has_dot(self, pluggy_mod):
        assert "." in pluggy_mod.__version__


# ---------------------------------------------------------------------------
# TestPluggyPluginManager
# ---------------------------------------------------------------------------

class TestPluggyPluginManager:
    def test_project_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager",
                "args": ["myproject"],
                "method": "project_name",
                "expected": "myproject",
            },
        })
        assert ok, msg

    def test_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager.__name__.__eq__",
                "args": ["PluginManager"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_plugin_manager_class_exists(self, pluggy_mod):
        assert hasattr(pluggy_mod, "PluginManager")
        assert isinstance(pluggy_mod.PluginManager, type)

    def test_plugin_manager_instantiates(self, pluggy_mod):
        pm = pluggy_mod.PluginManager("test")
        assert pm.project_name == "test"


# ---------------------------------------------------------------------------
# TestPluggyMarkers
# ---------------------------------------------------------------------------

class TestPluggyMarkers:
    def test_hookspec_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HookspecMarker.__name__.__eq__",
                "args": ["HookspecMarker"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_hookimpl_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HookimplMarker.__name__.__eq__",
                "args": ["HookimplMarker"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_hookspec_instance_project_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HookspecMarker",
                "args": ["myproject"],
                "method": "project_name",
                "expected": "myproject",
            },
        })
        assert ok, msg

    def test_hookimpl_instance_project_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HookimplMarker",
                "args": ["myproject"],
                "method": "project_name",
                "expected": "myproject",
            },
        })
        assert ok, msg

    def test_hookspec_is_callable(self, pluggy_mod):
        assert callable(pluggy_mod.HookspecMarker)
        hookspec = pluggy_mod.HookspecMarker("myproject")
        assert callable(hookspec)

    def test_hookimpl_is_callable(self, pluggy_mod):
        assert callable(pluggy_mod.HookimplMarker)
        hookimpl = pluggy_mod.HookimplMarker("myproject")
        assert callable(hookimpl)

    def test_hookspec_wrong_project_name_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HookspecMarker",
                "args": ["myproject"],
                "method": "project_name",
                "expected": "other",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPluggyPMMethods
# ---------------------------------------------------------------------------

class TestPluggyPMMethods:
    def test_get_plugins_is_empty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager",
                "args": ["x"],
                "method": "get_plugins",
                "method_chain": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_is_registered_none_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager",
                "args": ["x"],
                "method": "is_registered",
                "method_args": [None],
                "expected": False,
            },
        })
        assert ok, msg

    def test_has_register(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager.__dict__.__contains__",
                "args": ["register"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_has_unregister(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager.__dict__.__contains__",
                "args": ["unregister"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_has_get_plugins(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PluginManager.__dict__.__contains__",
                "args": ["get_plugins"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_get_plugins_returns_set(self, pluggy_mod):
        pm = pluggy_mod.PluginManager("x")
        result = pm.get_plugins()
        assert isinstance(result, set)

    def test_get_plugins_empty_on_fresh_manager(self, pluggy_mod):
        pm = pluggy_mod.PluginManager("fresh")
        assert len(pm.get_plugins()) == 0

    def test_is_registered_none_returns_bool(self, pluggy_mod):
        pm = pluggy_mod.PluginManager("x")
        result = pm.is_registered(None)
        assert isinstance(result, bool)
        assert result is False


# ---------------------------------------------------------------------------
# TestPluggyAll — all 13 pluggy invariants must pass
# ---------------------------------------------------------------------------

class TestPluggyAll:
    def test_all_pass(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod)
        assert len(results) == 13

    def test_no_skips(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_plugin_manager_category(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod, filter_category="plugin_manager")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_markers_category(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod, filter_category="markers")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_pm_methods_category(self, pluggy_spec, pluggy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pluggy_spec, pluggy_mod, filter_category="pm_methods")
        assert len(results) == 5
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestPluggyCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PLUGGY_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(PLUGGY_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "13 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PLUGGY_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "pluggy.version" in out
        assert "pluggy.plugin_manager" in out

    def test_filter_flag_version(self, capsys):
        vb.main([str(PLUGGY_SPEC_PATH), "--filter", "version", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(PLUGGY_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 13
        assert all(r["passed"] for r in data)
