"""
Tests for the python_module backend and platformdirs-specific invariants
in tools/verify_behavior.py.

Organized as:
  - TestPlatformdirsLoader: loading the platformdirs spec and module
  - TestPlatformdirsVersion: version category invariants
  - TestPlatformdirsPaths: paths category invariants
  - TestPlatformdirsAppName: app_name category invariants
  - TestPlatformdirsTypes: types category invariants
  - TestPlatformdirsAttrs: attrs category invariants
  - TestPlatformdirsAll: all 14 platformdirs invariants pass
  - TestPlatformdirsCLI: verify_behavior CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
# When running from the worktree (.claude/worktrees/<id>/tests/), walk up to the
# actual repository root (which has _build/ and tools/).
# Structure: <repo>/.claude/worktrees/<id>/tests/test_*.py
_candidate = _HERE.parent.parent.parent.parent.parent
REPO_ROOT = (
    _candidate
    if (_candidate / "tools" / "verify_behavior.py").exists()
    else _HERE.parent.parent
)
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Skip entire module if platformdirs is not installed
platformdirs = pytest.importorskip("platformdirs", reason="platformdirs not installed")

import verify_behavior as vb

PLATFORMDIRS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "platformdirs.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def platformdirs_spec():
    return vb.SpecLoader().load(PLATFORMDIRS_SPEC_PATH)


@pytest.fixture(scope="module")
def platformdirs_mod(platformdirs_spec):
    return vb.LibraryLoader().load(platformdirs_spec["library"])


@pytest.fixture(scope="module")
def constants_map(platformdirs_spec):
    return vb.InvariantRunner().build_constants_map(platformdirs_spec["constants"])


@pytest.fixture(scope="module")
def registry(platformdirs_mod, constants_map):
    return vb.PatternRegistry(platformdirs_mod, constants_map)


# ---------------------------------------------------------------------------
# TestPlatformdirsLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestPlatformdirsLoader:
    def test_loads_spec(self, platformdirs_spec):
        assert isinstance(platformdirs_spec, dict)

    def test_all_required_sections_present(self, platformdirs_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in platformdirs_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, platformdirs_spec):
        assert platformdirs_spec["library"]["backend"] == "python_module"

    def test_module_name_is_platformdirs(self, platformdirs_spec):
        assert platformdirs_spec["library"]["module_name"] == "platformdirs"

    def test_loads_platformdirs_module(self, platformdirs_mod):
        import platformdirs as pd
        assert platformdirs_mod is pd

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_platformdirs_xyz",
            })

    def test_all_invariant_kinds_known(self, platformdirs_spec):
        for inv in platformdirs_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, platformdirs_spec):
        ids = [inv["id"] for inv in platformdirs_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_13(self, platformdirs_spec):
        assert len(platformdirs_spec["invariants"]) == 13


# ---------------------------------------------------------------------------
# TestPlatformdirsVersion
# ---------------------------------------------------------------------------

class TestPlatformdirsVersion:
    def test_version_is_str(self, registry):
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

    def test_version_starts_with_digit(self, platformdirs_mod):
        """Direct check: __version__ is a non-empty string starting with a digit."""
        v = platformdirs_mod.__version__
        assert isinstance(v, str)
        assert v and v[0].isdigit(), f"__version__ = {v!r} does not start with a digit"


# ---------------------------------------------------------------------------
# TestPlatformdirsPaths
# ---------------------------------------------------------------------------

class TestPlatformdirsPaths:
    def test_user_data_dir_contains_app(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_data_dir",
                "args": ["myapp"],
                "method": "__contains__",
                "method_args": ["myapp"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_cache_dir_contains_app(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_cache_dir",
                "args": ["myapp"],
                "method": "__contains__",
                "method_args": ["myapp"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_log_dir_contains_app(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_log_dir",
                "args": ["myapp"],
                "method": "__contains__",
                "method_args": ["myapp"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_config_dir_contains_app(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_config_dir",
                "args": ["myapp"],
                "method": "__contains__",
                "method_args": ["myapp"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_site_data_dir_nonempty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "site_data_dir",
                "args": ["myapp"],
                "method": "__len__",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_all_path_functions_return_str(self, platformdirs_mod):
        """Direct check: all convenience functions return str instances."""
        for fn_name in ("user_data_dir", "user_cache_dir", "user_log_dir",
                        "user_config_dir", "site_data_dir"):
            result = getattr(platformdirs_mod, fn_name)("testapp")
            assert isinstance(result, str), \
                f"{fn_name}('testapp') returned {type(result).__name__}, expected str"
            assert len(result) > 0, f"{fn_name}('testapp') returned empty string"


# ---------------------------------------------------------------------------
# TestPlatformdirsAppName
# ---------------------------------------------------------------------------

class TestPlatformdirsAppName:
    def test_user_data_dir_has_app_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_data_dir",
                "args": ["uniqueappname123"],
                "method": "__contains__",
                "method_args": ["uniqueappname123"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_cache_dir_has_app_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_cache_dir",
                "args": ["uniqueappname123"],
                "method": "__contains__",
                "method_args": ["uniqueappname123"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_log_dir_has_app_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_log_dir",
                "args": ["uniqueappname123"],
                "method": "__contains__",
                "method_args": ["uniqueappname123"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_different_apps_different_paths(self, platformdirs_mod):
        """Direct check: two different app names produce different paths."""
        p1 = platformdirs_mod.user_data_dir("appone")
        p2 = platformdirs_mod.user_data_dir("apptwo")
        assert p1 != p2, "Different app names should produce different paths"

    def test_platformdirs_class_app_name_in_path(self, platformdirs_mod):
        """Direct check: PlatformDirs('myapp').user_data_dir contains 'myapp'."""
        pd = platformdirs_mod.PlatformDirs("myapp")
        assert "myapp" in pd.user_data_dir
        assert "myapp" in pd.user_cache_dir


# ---------------------------------------------------------------------------
# TestPlatformdirsTypes
# ---------------------------------------------------------------------------

class TestPlatformdirsTypes:
    def test_user_data_dir_nonempty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_data_dir",
                "args": ["testapp"],
                "method": "__len__",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_cache_dir_nonempty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_cache_dir",
                "args": ["testapp"],
                "method": "__len__",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_platformdirs_user_data_path_is_path_object(self, platformdirs_mod):
        """Direct check: PlatformDirs('x').user_data_path returns a pathlib.Path."""
        from pathlib import Path
        pd = platformdirs_mod.PlatformDirs("testapp")
        assert isinstance(pd.user_data_path, Path), \
            f"user_data_path is {type(pd.user_data_path).__name__}, expected Path"

    def test_platformdirs_user_cache_path_is_path_object(self, platformdirs_mod):
        """Direct check: PlatformDirs('x').user_cache_path returns a pathlib.Path."""
        from pathlib import Path
        pd = platformdirs_mod.PlatformDirs("testapp")
        assert isinstance(pd.user_cache_path, Path), \
            f"user_cache_path is {type(pd.user_cache_path).__name__}, expected Path"


# ---------------------------------------------------------------------------
# TestPlatformdirsAttrs
# ---------------------------------------------------------------------------

class TestPlatformdirsAttrs:
    def test_user_config_dir_nonempty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_config_dir",
                "args": ["testapp"],
                "method": "__len__",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_user_log_dir_nonempty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_log_dir",
                "args": ["testapp"],
                "method": "__len__",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_platformdirs_class_has_expected_attributes(self, platformdirs_mod):
        """Direct check: PlatformDirs instance has all expected dir attributes."""
        pd = platformdirs_mod.PlatformDirs("testapp")
        for attr in ("user_data_dir", "user_cache_dir", "user_log_dir",
                     "user_config_dir", "user_data_path", "user_cache_path"):
            assert hasattr(pd, attr), f"PlatformDirs has no attribute {attr!r}"

    def test_wrong_app_name_not_in_result_fails(self, registry):
        """Sanity check: wrong app name does not appear in another app's path."""
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "user_data_dir",
                "args": ["myapp"],
                "method": "__contains__",
                "method_args": ["totallydifferentapp"],
                "expected": True,
            },
        })
        assert not ok, "Wrong app name should not appear in path — spec sanity check failed"


# ---------------------------------------------------------------------------
# TestPlatformdirsAll — all 14 invariants pass
# ---------------------------------------------------------------------------

class TestPlatformdirsAll:
    def test_all_pass(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod)
        assert len(results) == 13

    def test_no_skips(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_category_version(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod,
                                 filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_paths(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod,
                                 filter_category="paths")
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_by_category_path_objects(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod,
                                 filter_category="path_objects")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_site_dirs(self, platformdirs_spec, platformdirs_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(platformdirs_spec, platformdirs_mod,
                                 filter_category="site_dirs")
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestPlatformdirsCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestPlatformdirsCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PLATFORMDIRS_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(PLATFORMDIRS_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "13 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PLATFORMDIRS_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "platformdirs.version.is_str" in out
        assert "platformdirs.paths.user_data_dir_contains_app" in out

    def test_filter_flag_paths(self, capsys):
        vb.main([str(PLATFORMDIRS_SPEC_PATH), "--filter", "paths", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(PLATFORMDIRS_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 13
        assert all(r["passed"] for r in data)
