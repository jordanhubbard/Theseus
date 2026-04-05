"""
Tests for the python_module(zoneinfo) backend and tzdata-backed invariants
in tools/verify_behavior.py.

tzdata provides IANA timezone data for the Python stdlib zoneinfo module.
The spec targets zoneinfo as the consumer interface; tzdata version checks
are performed directly via importlib.metadata.

Organized as:
  - TestTzdataLoader: loading the tzdata spec and the zoneinfo module
  - TestTzdataVersion: tzdata version checks via importlib.metadata
  - TestTzdataZoneinfoKeys: available_timezones() membership invariants
  - TestTzdataZoneinfoCreate: ZoneInfo object .key attribute invariants
  - TestTzdataCount: ZoneInfo key length invariants
  - TestTzdataError: ZoneInfoNotFoundError invariants
  - TestTzdataAll: all 13 invariants pass
  - TestTzdataCLI: verify_behavior CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
# When running from the worktree (.claude/worktrees/<id>/tests/), walk up to the
# actual repository root (which has _build/ and tools/).
# Structure: <repo>/.claude/worktrees/<id>/tests/test_*.py
_candidate = _HERE.parent.parent.parent.parent.parent
REPO_ROOT = _candidate if (_candidate / "tools" / "verify_behavior.py").exists() else _HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Skip entire module if zoneinfo is not available (Python < 3.9)
zoneinfo = pytest.importorskip("zoneinfo", reason="zoneinfo not available (requires Python 3.9+)")

import verify_behavior as vb

TZDATA_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "tzdata.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tzdata_spec():
    return vb.SpecLoader().load(TZDATA_SPEC_PATH)


@pytest.fixture(scope="module")
def zoneinfo_mod(tzdata_spec):
    return vb.LibraryLoader().load(tzdata_spec["library"])


@pytest.fixture(scope="module")
def constants_map(tzdata_spec):
    return vb.InvariantRunner().build_constants_map(tzdata_spec["constants"])


@pytest.fixture(scope="module")
def registry(zoneinfo_mod, constants_map):
    return vb.PatternRegistry(zoneinfo_mod, constants_map)


# ---------------------------------------------------------------------------
# TestTzdataLoader
# ---------------------------------------------------------------------------

class TestTzdataLoader:
    def test_loads_spec(self, tzdata_spec):
        assert isinstance(tzdata_spec, dict)

    def test_all_required_sections_present(self, tzdata_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in tzdata_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, tzdata_spec):
        assert tzdata_spec["library"]["backend"] == "python_module"

    def test_module_name_is_zoneinfo(self, tzdata_spec):
        assert tzdata_spec["library"]["module_name"] == "zoneinfo"

    def test_loads_zoneinfo_module(self, zoneinfo_mod):
        import zoneinfo as zi_ref
        assert zoneinfo_mod is zi_ref

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_tzdata_xyz",
            })

    def test_all_invariant_kinds_known(self, tzdata_spec):
        for inv in tzdata_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, tzdata_spec):
        ids = [inv["id"] for inv in tzdata_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_13(self, tzdata_spec):
        assert len(tzdata_spec["invariants"]) == 13


# ---------------------------------------------------------------------------
# TestTzdataVersion — tzdata version checks via importlib.metadata
# ---------------------------------------------------------------------------

class TestTzdataVersion:
    def test_tzdata_is_installed(self):
        import importlib.metadata
        v = importlib.metadata.version("tzdata")
        assert v is not None
        assert isinstance(v, str)

    def test_tzdata_version_contains_dot(self):
        import importlib.metadata
        v = importlib.metadata.version("tzdata")
        assert "." in v, f"tzdata version {v!r} does not contain a dot"

    def test_tzdata_version_starts_with_digit(self):
        import importlib.metadata
        v = importlib.metadata.version("tzdata")
        assert v[0].isdigit(), f"tzdata version {v!r} does not start with a digit"

    def test_tzdata_version_format(self):
        import importlib.metadata
        v = importlib.metadata.version("tzdata")
        # tzdata uses YEAR.N format, e.g. "2026.1"
        parts = v.split(".")
        assert len(parts) == 2, f"Expected YEAR.N format, got {v!r}"
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_tzdata_iana_version(self):
        import tzdata as td
        assert hasattr(td, "IANA_VERSION")
        assert isinstance(td.IANA_VERSION, str)
        assert td.IANA_VERSION.startswith("2"), \
            f"IANA_VERSION {td.IANA_VERSION!r} should start with '2'"

    def test_tzdata_module_version_attr(self):
        import tzdata as td
        assert hasattr(td, "__version__")
        v = td.__version__
        assert isinstance(v, str)
        assert "." in v


# ---------------------------------------------------------------------------
# TestTzdataZoneinfoKeys — available_timezones() membership invariants
# ---------------------------------------------------------------------------

class TestTzdataZoneinfoKeys:
    def test_contains_utc(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["UTC"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_contains_america_new_york(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["America/New_York"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_contains_europe_london(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["Europe/London"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_contains_asia_tokyo(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["Asia/Tokyo"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_contains_america_los_angeles(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["America/Los_Angeles"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_contains_pacific_auckland(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["Pacific/Auckland"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_does_not_contain_invalid_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_timezones",
                "args": [],
                "method": "__contains__",
                "method_args": ["Not/A/Timezone"],
                "expected": True,
            },
        })
        assert not ok  # invalid key should not be in the set

    def test_returns_set_directly(self):
        import zoneinfo as zi
        tz_set = zi.available_timezones()
        assert isinstance(tz_set, set)
        assert len(tz_set) > 400


# ---------------------------------------------------------------------------
# TestTzdataZoneinfoCreate — ZoneInfo object .key attribute invariants
# ---------------------------------------------------------------------------

class TestTzdataZoneinfoCreate:
    def test_utc_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["UTC"],
                "method": "key",
                "expected": "UTC",
            },
        })
        assert ok, msg

    def test_america_new_york_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["America/New_York"],
                "method": "key",
                "expected": "America/New_York",
            },
        })
        assert ok, msg

    def test_europe_london_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["Europe/London"],
                "method": "key",
                "expected": "Europe/London",
            },
        })
        assert ok, msg

    def test_asia_tokyo_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["Asia/Tokyo"],
                "method": "key",
                "expected": "Asia/Tokyo",
            },
        })
        assert ok, msg

    def test_wrong_key_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["UTC"],
                "method": "key",
                "expected": "America/New_York",
            },
        })
        assert not ok

    def test_zoneinfo_obj_type(self):
        import zoneinfo as zi
        utc = zi.ZoneInfo("UTC")
        assert type(utc).__name__ == "ZoneInfo"


# ---------------------------------------------------------------------------
# TestTzdataCount — ZoneInfo key length invariants
# ---------------------------------------------------------------------------

class TestTzdataCount:
    def test_utc_key_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["UTC"],
                "method": "key",
                "method_chain": "__len__",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_america_new_york_key_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["America/New_York"],
                "method": "key",
                "method_chain": "__len__",
                "expected": 16,
            },
        })
        assert ok, msg

    def test_available_timezones_count_gt_400(self):
        import zoneinfo as zi
        assert len(zi.available_timezones()) > 400

    def test_available_timezones_count_gt_500(self):
        import zoneinfo as zi
        assert len(zi.available_timezones()) > 500

    def test_wrong_len_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZoneInfo",
                "args": ["UTC"],
                "method": "key",
                "method_chain": "__len__",
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestTzdataError — ZoneInfoNotFoundError invariants
# ---------------------------------------------------------------------------

class TestTzdataError:
    def test_unknown_key_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "ZoneInfo",
                "args": ["Not/A/Timezone"],
                "expected_exception": "zoneinfo.ZoneInfoNotFoundError",
            },
        })
        assert ok, msg

    def test_known_key_does_not_raise(self):
        import zoneinfo as zi
        tz = zi.ZoneInfo("UTC")
        assert tz is not None

    def test_error_class_exists(self):
        import zoneinfo as zi
        assert hasattr(zi, "ZoneInfoNotFoundError")
        assert issubclass(zi.ZoneInfoNotFoundError, Exception)

    def test_no_raise_fails_correctly(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "ZoneInfo",
                "args": ["UTC"],
                "expected_exception": "zoneinfo.ZoneInfoNotFoundError",
            },
        })
        assert not ok  # no exception raised — handler returns False


# ---------------------------------------------------------------------------
# TestTzdataAll — full InvariantRunner integration
# ---------------------------------------------------------------------------

class TestTzdataAll:
    def test_all_pass(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod)
        assert len(results) == 13

    def test_no_skips(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_zoneinfo_keys_category(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod, filter_category="zoneinfo_keys")
        # UTC, America/New_York, Europe/London, Asia/Tokyo, America/Los_Angeles,
        # Pacific/Auckland = 6
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_zoneinfo_create_category(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod, filter_category="zoneinfo_create")
        # utc_key, america_new_york_key, europe_london_key, asia_tokyo_key = 4
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_count_category(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod, filter_category="count")
        # utc_key_len, america_new_york_key_len = 2
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_error_category(self, tzdata_spec, zoneinfo_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tzdata_spec, zoneinfo_mod, filter_category="error")
        # unknown_key_raises = 1
        assert len(results) == 1
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestTzdataCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestTzdataCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(TZDATA_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(TZDATA_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "13 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(TZDATA_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "tzdata.zoneinfo_keys.contains_utc" in out
        assert "tzdata.zoneinfo_create.utc_key" in out

    def test_filter_flag_zoneinfo_keys(self, capsys):
        vb.main([str(TZDATA_SPEC_PATH), "--filter", "zoneinfo_keys", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(TZDATA_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 13
        assert all(r["passed"] for r in data)
