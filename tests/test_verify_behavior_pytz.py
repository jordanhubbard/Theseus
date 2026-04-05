"""
Tests for the python_module backend and pytz-specific invariants
in tools/verify_behavior.py.

Organized as:
  - TestPytzLoader: loading the pytz spec and the pytz module
  - TestPytzVersion: __version__ attribute invariants
  - TestPytzUTC: pytz.utc / pytz.UTC singleton invariants
  - TestPytzTimezone: pytz.timezone() lookup invariants
  - TestPytzAllTimezones: all_timezones membership and size invariants
  - TestPytzCommonTimezones: common_timezones membership invariants
  - TestPytzExceptions: UnknownTimeZoneError invariants
  - TestPytzConstants: ZERO and HOUR constant invariants
  - TestPytzAll: all 16 pytz invariants pass
  - TestPytzCLI: verify_behavior CLI end-to-end
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

# Skip entire module if pytz is not installed
pytz = pytest.importorskip("pytz", reason="pytz not installed")

import verify_behavior as vb

PYTZ_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pytz.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pytz_spec():
    return vb.SpecLoader().load(PYTZ_SPEC_PATH)


@pytest.fixture(scope="module")
def pytz_mod(pytz_spec):
    return vb.LibraryLoader().load(pytz_spec["library"])


@pytest.fixture(scope="module")
def constants_map(pytz_spec):
    return vb.InvariantRunner().build_constants_map(pytz_spec["constants"])


@pytest.fixture(scope="module")
def registry(pytz_mod, constants_map):
    return vb.PatternRegistry(pytz_mod, constants_map)


# ---------------------------------------------------------------------------
# TestPytzLoader
# ---------------------------------------------------------------------------

class TestPytzLoader:
    def test_loads_spec(self, pytz_spec):
        assert isinstance(pytz_spec, dict)

    def test_all_required_sections_present(self, pytz_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pytz_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pytz_spec):
        assert pytz_spec["library"]["backend"] == "python_module"

    def test_module_name_is_pytz(self, pytz_spec):
        assert pytz_spec["library"]["module_name"] == "pytz"

    def test_loads_pytz_module(self, pytz_mod):
        import pytz as pytz_ref
        assert pytz_mod is pytz_ref

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_pytz_xyz",
            })

    def test_all_invariant_kinds_known(self, pytz_spec):
        for inv in pytz_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pytz_spec):
        ids = [inv["id"] for inv in pytz_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_16(self, pytz_spec):
        assert len(pytz_spec["invariants"]) == 16


# ---------------------------------------------------------------------------
# TestPytzVersion
# ---------------------------------------------------------------------------

class TestPytzVersion:
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

    def test_version_not_empty(self):
        import pytz as pytz_ref
        assert pytz_ref.__version__ != ""

    def test_wrong_contains_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["XXXNOTINVERSION"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPytzUTC
# ---------------------------------------------------------------------------

class TestPytzUTC:
    def test_utc_str_eq_UTC(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utc.__str__",
                "args": [],
                "expected": "UTC",
            },
        })
        assert ok, msg

    def test_utc_zone_eq_UTC(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utc.zone.__eq__",
                "args": ["UTC"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_UTC_alias_zone_eq_UTC(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "UTC.zone.__eq__",
                "args": ["UTC"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_utc_and_UTC_are_same_object(self):
        import pytz as pytz_ref
        assert pytz_ref.utc is pytz_ref.UTC

    def test_utc_zone_wrong_value_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "utc.zone.__eq__",
                "args": ["America/New_York"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPytzTimezone
# ---------------------------------------------------------------------------

class TestPytzTimezone:
    def test_utc_zone_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "timezone",
                "args": ["UTC"],
                "method": "zone",
                "expected": "UTC",
            },
        })
        assert ok, msg

    def test_america_new_york_zone_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "timezone",
                "args": ["America/New_York"],
                "method": "zone",
                "expected": "America/New_York",
            },
        })
        assert ok, msg

    def test_europe_london_zone_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "timezone",
                "args": ["Europe/London"],
                "method": "zone",
                "expected": "Europe/London",
            },
        })
        assert ok, msg

    def test_wrong_zone_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "timezone",
                "args": ["UTC"],
                "method": "zone",
                "expected": "America/New_York",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPytzAllTimezones
# ---------------------------------------------------------------------------

class TestPytzAllTimezones:
    def test_contains_UTC(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "all_timezones",
                "must_contain": ["UTC"],
            },
        })
        assert ok, msg

    def test_contains_america_new_york(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "all_timezones",
                "must_contain": ["America/New_York"],
            },
        })
        assert ok, msg

    def test_length_gt_400(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "all_timezones.__len__",
                "args": [],
                "method": "__gt__",
                "method_args": [400],
                "expected": True,
            },
        })
        assert ok, msg

    def test_missing_member_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "all_timezones",
                "must_contain": ["Not/A/Timezone"],
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPytzCommonTimezones
# ---------------------------------------------------------------------------

class TestPytzCommonTimezones:
    def test_contains_UTC(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "common_timezones",
                "must_contain": ["UTC"],
            },
        })
        assert ok, msg

    def test_common_is_subset_of_all(self):
        import pytz as pytz_ref
        common_set = set(pytz_ref.common_timezones)
        all_set = set(pytz_ref.all_timezones)
        assert common_set.issubset(all_set)

    def test_common_shorter_than_all(self):
        import pytz as pytz_ref
        assert len(pytz_ref.common_timezones) < len(pytz_ref.all_timezones)


# ---------------------------------------------------------------------------
# TestPytzExceptions
# ---------------------------------------------------------------------------

class TestPytzExceptions:
    def test_exception_name_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.UnknownTimeZoneError.__name__.__eq__",
                "args": ["UnknownTimeZoneError"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_invalid_timezone_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "timezone",
                "args": ["Not/A/Timezone"],
                "expected_exception": "pytz.exceptions.UnknownTimeZoneError",
            },
        })
        assert ok, msg

    def test_valid_timezone_does_not_raise(self):
        import pytz as pytz_ref
        tz = pytz_ref.timezone("UTC")
        assert tz is not None

    def test_exception_is_subclass_of_exception(self):
        import pytz as pytz_ref
        assert issubclass(pytz_ref.exceptions.UnknownTimeZoneError, Exception)

    def test_no_raise_fails_correctly(self, registry):
        # Valid zone should NOT raise — handler should return False for raises check
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "timezone",
                "args": ["UTC"],
                "expected_exception": "pytz.exceptions.UnknownTimeZoneError",
            },
        })
        assert not ok  # no exception was raised — handler returns False


# ---------------------------------------------------------------------------
# TestPytzConstants
# ---------------------------------------------------------------------------

class TestPytzConstants:
    def test_ZERO_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZERO.__str__",
                "args": [],
                "expected": "0:00:00",
            },
        })
        assert ok, msg

    def test_HOUR_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "HOUR.__str__",
                "args": [],
                "expected": "1:00:00",
            },
        })
        assert ok, msg

    def test_ZERO_is_timedelta(self):
        from datetime import timedelta
        import pytz as pytz_ref
        assert pytz_ref.ZERO == timedelta(0)

    def test_HOUR_is_timedelta(self):
        from datetime import timedelta
        import pytz as pytz_ref
        assert pytz_ref.HOUR == timedelta(hours=1)

    def test_ZERO_wrong_value_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ZERO.__str__",
                "args": [],
                "expected": "1:00:00",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPytzAll — full InvariantRunner integration
# ---------------------------------------------------------------------------

class TestPytzAll:
    def test_all_pass(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod)
        assert len(results) == 16

    def test_no_skips(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_version_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="version")
        # contains_dot, is_string = 2
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_utc_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="utc")
        # utc_str_eq_UTC, utc_zone_eq_UTC, UTC_alias_zone_eq_UTC = 3
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_timezone_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="timezone")
        # utc_zone, america_new_york_zone, europe_london_zone = 3
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_all_timezones_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="all_timezones")
        # contains_UTC, contains_america_new_york, length_gt_400 = 3
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_common_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="common")
        # contains_UTC = 1
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_exceptions_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="exceptions")
        # UnknownTimeZoneError.name, timezone_invalid_raises = 2
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_constants_category(self, pytz_spec, pytz_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pytz_spec, pytz_mod, filter_category="constants")
        # ZERO.str_eq, HOUR.str_eq = 2
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestPytzCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestPytzCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PYTZ_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(PYTZ_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "16 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PYTZ_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "pytz.utc.str_eq_UTC" in out
        assert "pytz.timezone.utc_zone" in out

    def test_filter_flag_utc(self, capsys):
        vb.main([str(PYTZ_SPEC_PATH), "--filter", "utc", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(PYTZ_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 16
        assert all(r["passed"] for r in data)
