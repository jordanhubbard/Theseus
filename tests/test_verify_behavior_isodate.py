"""
Tests for the python_module backend and isodate-specific invariants
in tools/verify_behavior.py.

Organized as:
  - TestISODateLoader: loading isodate spec and module
  - TestISODateVersion: __version__ attribute invariants
  - TestISODateParseDateTime: parse_datetime category invariants
  - TestISODateParseDate: parse_date category invariants
  - TestISODateParseDuration: parse_duration category invariants
  - TestISODateISOFormat: isoformat / parse_time category invariants
  - TestISODateAll: all 16 isodate invariants pass
  - TestISODateCLI: verify_behavior CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
# When running from the worktree (.claude/worktrees/<id>/tests/), walk up to the
# actual repository root (which has _build/ and tools/).
_candidate = _HERE.parent.parent.parent.parent.parent
REPO_ROOT = _candidate if (_candidate / "tools" / "verify_behavior.py").exists() else _HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Skip entire module if isodate is not installed
isodate = pytest.importorskip("isodate", reason="isodate not installed")

import verify_behavior as vb

ISODATE_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "isodate.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def isodate_spec():
    return vb.SpecLoader().load(ISODATE_SPEC_PATH)


@pytest.fixture(scope="module")
def isodate_mod(isodate_spec):
    return vb.LibraryLoader().load(isodate_spec["library"])


@pytest.fixture(scope="module")
def constants_map(isodate_spec):
    return vb.InvariantRunner().build_constants_map(isodate_spec["constants"])


@pytest.fixture(scope="module")
def registry(isodate_mod, constants_map):
    return vb.PatternRegistry(isodate_mod, constants_map)


# ---------------------------------------------------------------------------
# TestISODateLoader
# ---------------------------------------------------------------------------

class TestISODateLoader:
    def test_loads_spec(self, isodate_spec):
        assert isinstance(isodate_spec, dict)

    def test_all_required_sections_present(self, isodate_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in isodate_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, isodate_spec):
        assert isodate_spec["library"]["backend"] == "python_module"

    def test_module_name_is_isodate(self, isodate_spec):
        assert isodate_spec["library"]["module_name"] == "isodate"

    def test_loads_isodate_module(self, isodate_mod):
        import isodate as isodate_ref
        assert isodate_mod is isodate_ref

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_isodate_xyz",
            })

    def test_all_invariant_kinds_known(self, isodate_spec):
        for inv in isodate_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, isodate_spec):
        ids = [inv["id"] for inv in isodate_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_16(self, isodate_spec):
        assert len(isodate_spec["invariants"]) == 16


# ---------------------------------------------------------------------------
# TestISODateVersion
# ---------------------------------------------------------------------------

class TestISODateVersion:
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
        import isodate as isodate_ref
        assert isinstance(isodate_ref.__version__, str)
        assert len(isodate_ref.__version__) > 0

    def test_wrong_contains_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["XXXNOTINVERSION"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestISODateParseDateTime
# ---------------------------------------------------------------------------

class TestISODateParseDateTime:
    _DT_STR = "2023-01-15T10:30:00"

    def test_year(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_datetime",
                "args": [self._DT_STR],
                "method": "year",
                "expected": 2023,
            },
        })
        assert ok, msg

    def test_month(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_datetime",
                "args": [self._DT_STR],
                "method": "month",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_day(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_datetime",
                "args": [self._DT_STR],
                "method": "day",
                "expected": 15,
            },
        })
        assert ok, msg

    def test_hour(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_datetime",
                "args": [self._DT_STR],
                "method": "hour",
                "expected": 10,
            },
        })
        assert ok, msg

    def test_isoformat_roundtrip(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_datetime",
                "args": [self._DT_STR],
                "method": "isoformat",
                "expected": self._DT_STR,
            },
        })
        assert ok, msg

    def test_wrong_year_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_datetime",
                "args": [self._DT_STR],
                "method": "year",
                "expected": 9999,
            },
        })
        assert not ok

    def test_returns_datetime_object(self):
        from datetime import datetime
        import isodate as isodate_ref
        dt = isodate_ref.parse_datetime(self._DT_STR)
        assert isinstance(dt, datetime)


# ---------------------------------------------------------------------------
# TestISODateParseDate
# ---------------------------------------------------------------------------

class TestISODateParseDate:
    _DATE_STR = "2023-06-21"

    def test_year(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_date",
                "args": [self._DATE_STR],
                "method": "year",
                "expected": 2023,
            },
        })
        assert ok, msg

    def test_month(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_date",
                "args": [self._DATE_STR],
                "method": "month",
                "expected": 6,
            },
        })
        assert ok, msg

    def test_day(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_date",
                "args": [self._DATE_STR],
                "method": "day",
                "expected": 21,
            },
        })
        assert ok, msg

    def test_isoformat_roundtrip(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_date",
                "args": [self._DATE_STR],
                "method": "isoformat",
                "expected": self._DATE_STR,
            },
        })
        assert ok, msg

    def test_wrong_month_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_date",
                "args": [self._DATE_STR],
                "method": "month",
                "expected": 99,
            },
        })
        assert not ok

    def test_returns_date_object(self):
        from datetime import date
        import isodate as isodate_ref
        d = isodate_ref.parse_date(self._DATE_STR)
        assert isinstance(d, date)


# ---------------------------------------------------------------------------
# TestISODateParseDuration
# ---------------------------------------------------------------------------

class TestISODateParseDuration:
    def test_one_day_days(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_duration",
                "args": ["P1D"],
                "method": "days",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_one_hour_seconds(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_duration",
                "args": ["PT1H"],
                "method": "seconds",
                "expected": 3600,
            },
        })
        assert ok, msg

    def test_P1D_returns_timedelta(self):
        from datetime import timedelta
        import isodate as isodate_ref
        dur = isodate_ref.parse_duration("P1D")
        assert isinstance(dur, timedelta)
        assert dur.days == 1

    def test_PT1H_returns_timedelta(self):
        from datetime import timedelta
        import isodate as isodate_ref
        dur = isodate_ref.parse_duration("PT1H")
        assert isinstance(dur, timedelta)
        assert dur.seconds == 3600

    def test_wrong_days_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_duration",
                "args": ["P1D"],
                "method": "days",
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestISODateISOFormat
# ---------------------------------------------------------------------------

class TestISODateISOFormat:
    _TIME_STR = "10:30:45"

    def test_parse_time_hour(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_time",
                "args": [self._TIME_STR],
                "method": "hour",
                "expected": 10,
            },
        })
        assert ok, msg

    def test_parse_time_minute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_time",
                "args": [self._TIME_STR],
                "method": "minute",
                "expected": 30,
            },
        })
        assert ok, msg

    def test_parse_time_second(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "parse_time",
                "args": [self._TIME_STR],
                "method": "second",
                "expected": 45,
            },
        })
        assert ok, msg

    def test_parse_time_returns_time_object(self):
        from datetime import time
        import isodate as isodate_ref
        t = isodate_ref.parse_time(self._TIME_STR)
        assert isinstance(t, time)

    def test_duration_isoformat_roundtrip(self):
        import isodate as isodate_ref
        dur = isodate_ref.parse_duration("P1D")
        assert isodate_ref.duration_isoformat(dur) == "P1D"

    def test_date_isoformat_roundtrip(self):
        import isodate as isodate_ref
        d = isodate_ref.parse_date("2023-06-21")
        assert isodate_ref.date_isoformat(d) == "2023-06-21"

    def test_datetime_isoformat_roundtrip(self):
        import isodate as isodate_ref
        dt = isodate_ref.parse_datetime("2023-01-15T10:30:00")
        assert isodate_ref.datetime_isoformat(dt) == "2023-01-15T10:30:00"


# ---------------------------------------------------------------------------
# TestISODateAll — full InvariantRunner integration
# ---------------------------------------------------------------------------

class TestISODateAll:
    def test_all_pass(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod)
        assert len(results) == 16

    def test_no_skips(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_version_category(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod, filter_category="version")
        # contains_dot, is_string = 2
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_parse_datetime_category(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod, filter_category="parse_datetime")
        # year, month, day, hour, isoformat_roundtrip = 5
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_parse_date_category(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod, filter_category="parse_date")
        # year, month, day, isoformat_roundtrip = 4
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_parse_duration_category(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod, filter_category="parse_duration")
        # one_day, one_hour = 2
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_isoformat_category(self, isodate_spec, isodate_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(isodate_spec, isodate_mod, filter_category="isoformat")
        # parse_time: hour, minute, second = 3
        assert len(results) == 3
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestISODateCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestISODateCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(ISODATE_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(ISODATE_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "16 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(ISODATE_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "isodate.version.contains_dot" in out
        assert "isodate.parse_datetime.year" in out

    def test_filter_flag_parse_datetime(self, capsys):
        vb.main([str(ISODATE_SPEC_PATH), "--filter", "parse_datetime", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(ISODATE_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 16
        assert all(r["passed"] for r in data)
