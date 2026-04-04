"""
Tests for datetime and pathlib Z-layer specs.

datetime.zspec.json — python_module backend, python_call_eq with method/method_args/method_chain
pathlib.zspec.json  — python_module backend, PurePosixPath pure operations
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT         = Path(__file__).resolve().parent.parent
DT_SPEC_PATH      = REPO_ROOT / "_build" / "zspecs" / "datetime.zspec.json"
PL_SPEC_PATH      = REPO_ROOT / "_build" / "zspecs" / "pathlib.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dt_spec():
    return vb.SpecLoader().load(DT_SPEC_PATH)


@pytest.fixture(scope="module")
def dt_lib(dt_spec):
    return vb.LibraryLoader().load(dt_spec["library"])


@pytest.fixture(scope="module")
def dt_registry(dt_lib):
    return vb.PatternRegistry(dt_lib, {})


@pytest.fixture(scope="module")
def pl_spec():
    return vb.SpecLoader().load(PL_SPEC_PATH)


@pytest.fixture(scope="module")
def pl_lib(pl_spec):
    return vb.LibraryLoader().load(pl_spec["library"])


@pytest.fixture(scope="module")
def pl_registry(pl_lib):
    return vb.PatternRegistry(pl_lib, {})


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(registry, invariant: dict):
    ok, msg = registry.run(invariant)
    return ok, msg


def inv_by_id(spec: dict, inv_id: str) -> dict:
    for inv in spec["invariants"]:
        if inv["id"] == inv_id:
            return inv
    raise KeyError(inv_id)


# ---------------------------------------------------------------------------
# datetime spec loading
# ---------------------------------------------------------------------------

class TestDatetimeSpecLoading:
    def test_spec_loads(self, dt_spec):
        assert dt_spec["identity"]["canonical_name"] == "datetime"

    def test_has_invariants(self, dt_spec):
        assert len(dt_spec["invariants"]) >= 15

    def test_categories_present(self, dt_spec):
        cats = {i["category"] for i in dt_spec["invariants"]}
        assert "date_construction" in cats
        assert "date_attributes" in cats
        assert "datetime_attributes" in cats
        assert "formatting" in cats
        assert "error" in cats

    def test_lib_loads(self, dt_lib):
        import datetime as _dt
        assert dt_lib is _dt


# ---------------------------------------------------------------------------
# datetime: date_construction
# ---------------------------------------------------------------------------

class TestDatetimeDateConstruction:
    def test_isoformat_roundtrip(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.isoformat")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_fromordinal_epoch(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.fromordinal_epoch")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_fromisoformat_roundtrip(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.fromisoformat_roundtrip")
        ok, msg = run(dt_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# datetime: date_attributes
# ---------------------------------------------------------------------------

class TestDatetimeDateAttributes:
    def test_year(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.year_attr")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_month(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.month_attr")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_day(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.day_attr")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_weekday(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.weekday")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_strftime(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.strftime")
        ok, msg = run(dt_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# datetime: datetime_construction and datetime_attributes
# ---------------------------------------------------------------------------

class TestDatetimeDatetimeAttributes:
    def test_isoformat(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.datetime.isoformat")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_hour(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.datetime.hour_attr")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_minute(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.datetime.minute_attr")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_second(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.datetime.second_attr")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_strftime(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.datetime.strftime")
        ok, msg = run(dt_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# datetime: error invariants
# ---------------------------------------------------------------------------

class TestDatetimeErrors:
    def test_invalid_month_raises(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.invalid_month_raises")
        ok, msg = run(dt_registry, inv)
        assert ok, msg

    def test_invalid_day_raises(self, dt_registry, dt_spec):
        inv = inv_by_id(dt_spec, "datetime.date.invalid_day_raises")
        ok, msg = run(dt_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# datetime: full spec integration
# ---------------------------------------------------------------------------

class TestDatetimeSpecIntegration:
    def test_all_pass(self, dt_registry, dt_spec):
        failures = []
        for inv in dt_spec["invariants"]:
            ok, msg = run(dt_registry, inv)
            if not ok:
                failures.append(f"{inv['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_category_counts(self, dt_spec):
        cats = {}
        for inv in dt_spec["invariants"]:
            cats[inv["category"]] = cats.get(inv["category"], 0) + 1
        assert cats.get("date_attributes", 0) >= 4
        # datetime_construction + datetime_attributes cover the time-component invariants
        assert cats.get("datetime_attributes", 0) + cats.get("datetime_construction", 0) >= 4
        assert cats.get("error", 0) >= 2

    def test_no_duplicate_ids(self, dt_spec):
        ids = [i["id"] for i in dt_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# pathlib spec loading
# ---------------------------------------------------------------------------

class TestPathlibSpecLoading:
    def test_spec_loads(self, pl_spec):
        assert pl_spec["identity"]["canonical_name"] == "pathlib"

    def test_has_invariants(self, pl_spec):
        assert len(pl_spec["invariants"]) >= 14

    def test_lib_loads(self, pl_lib):
        import pathlib as _pl
        assert pl_lib is _pl


# ---------------------------------------------------------------------------
# pathlib: construction
# ---------------------------------------------------------------------------

class TestPathlibConstruction:
    def test_str_coercion(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.str")
        ok, msg = run(pl_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# pathlib: components
# ---------------------------------------------------------------------------

class TestPathlibComponents:
    def test_name(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.name")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_stem(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.stem")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_suffix(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.suffix")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_suffixes(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.suffixes")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_parent(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.parent")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_parts(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.parts")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_root(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.root")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_no_suffix(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.no_suffix")
        ok, msg = run(pl_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# pathlib: predicates
# ---------------------------------------------------------------------------

class TestPathlibPredicates:
    def test_is_absolute_true(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.is_absolute")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_is_absolute_false(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.is_relative_false")
        ok, msg = run(pl_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# pathlib: manipulation
# ---------------------------------------------------------------------------

class TestPathlibManipulation:
    def test_with_suffix(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.with_suffix")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_with_name(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.with_name")
        ok, msg = run(pl_registry, inv)
        assert ok, msg

    def test_relative_to(self, pl_registry, pl_spec):
        inv = inv_by_id(pl_spec, "pathlib.purepath.relative_to")
        ok, msg = run(pl_registry, inv)
        assert ok, msg


# ---------------------------------------------------------------------------
# pathlib: full spec integration
# ---------------------------------------------------------------------------

class TestPathlibSpecIntegration:
    def test_all_pass(self, pl_registry, pl_spec):
        failures = []
        for inv in pl_spec["invariants"]:
            ok, msg = run(pl_registry, inv)
            if not ok:
                failures.append(f"{inv['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_no_duplicate_ids(self, pl_spec):
        ids = [i["id"] for i in pl_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_all_kinds_are_python_call_eq(self, pl_spec):
        for inv in pl_spec["invariants"]:
            assert inv["kind"] == "python_call_eq", f"{inv['id']} has unexpected kind {inv['kind']!r}"


# ---------------------------------------------------------------------------
# method chaining unit tests (tests the harness feature directly)
# ---------------------------------------------------------------------------

class TestMethodChaining:
    """Unit tests for the method/method_args/method_chain fields in python_call_eq."""

    def test_method_property(self, dt_registry):
        """Calling a property via 'method' works (year attr)."""
        spec = {
            "function": "date.fromisoformat",
            "args": [{"type": "str", "value": "2024-03-15"}],
            "expected": {"type": "int", "value": 2024},
            "method": "year",
        }
        ok, msg = dt_registry._python_call_eq(spec)
        assert ok, msg

    def test_method_callable_no_args(self, dt_registry):
        """Calling a zero-arg method via 'method' works (isoformat)."""
        spec = {
            "function": "date.fromisoformat",
            "args": [{"type": "str", "value": "2000-06-15"}],
            "expected": {"type": "str", "value": "2000-06-15"},
            "method": "isoformat",
        }
        ok, msg = dt_registry._python_call_eq(spec)
        assert ok, msg

    def test_method_callable_with_args(self, dt_registry):
        """Calling a method with args via 'method'+'method_args' works (strftime)."""
        spec = {
            "function": "date.fromisoformat",
            "args": [{"type": "str", "value": "2024-03-15"}],
            "expected": {"type": "str", "value": "2024/03/15"},
            "method": "strftime",
            "method_args": [{"type": "str", "value": "%Y/%m/%d"}],
        }
        ok, msg = dt_registry._python_call_eq(spec)
        assert ok, msg

    def test_method_chain(self, pl_registry):
        """Two-hop chain: method returns object, method_chain converts to string."""
        spec = {
            "function": "PurePosixPath",
            "args": [{"type": "str", "value": "/etc/passwd"}],
            "expected": {"type": "str", "value": "/etc"},
            "method": "parent",
            "method_chain": "__str__",
        }
        ok, msg = pl_registry._python_call_eq(spec)
        assert ok, msg

    def test_missing_method_fails(self, dt_registry):
        """Asking for a nonexistent method returns False."""
        spec = {
            "function": "date.fromisoformat",
            "args": [{"type": "str", "value": "2024-03-15"}],
            "expected": {"type": "str", "value": "anything"},
            "method": "nonexistent_method_xyz",
        }
        ok, msg = dt_registry._python_call_eq(spec)
        assert not ok
        assert "nonexistent_method_xyz" in msg
