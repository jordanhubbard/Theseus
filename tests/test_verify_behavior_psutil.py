"""
Tests for the python_module backend and psutil-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestPsutilLoader: loading psutil via the python_module backend
  - TestPsutilVersion: version category invariants
  - TestPsutilCpu: cpu category invariants
  - TestPsutilMemory: memory category invariants
  - TestPsutilDisk: disk category invariants
  - TestPsutilProcess: process category invariants
  - TestPsutilConstants: constants category invariants
  - TestPsutilPlatform: platform category invariants
  - TestPsutilAll: all 17 psutil invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PSUTIL_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "psutil.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def psutil_spec():
    return vb.SpecLoader().load(PSUTIL_SPEC_PATH)


@pytest.fixture(scope="module")
def psutil_mod(psutil_spec):
    return vb.LibraryLoader().load(psutil_spec["library"])


@pytest.fixture(scope="module")
def constants_map(psutil_spec):
    return vb.InvariantRunner().build_constants_map(psutil_spec["constants"])


@pytest.fixture(scope="module")
def registry(psutil_mod, constants_map):
    return vb.PatternRegistry(psutil_mod, constants_map)


# ---------------------------------------------------------------------------
# TestPsutilLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestPsutilLoader:
    def test_loads_psutil_spec(self, psutil_spec):
        assert isinstance(psutil_spec, dict)

    def test_all_required_sections_present(self, psutil_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in psutil_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, psutil_spec):
        assert psutil_spec["library"]["backend"] == "python_module"

    def test_module_name_is_psutil(self, psutil_spec):
        assert psutil_spec["library"]["module_name"] == "psutil"

    def test_loads_psutil_module(self, psutil_mod):
        import psutil
        assert psutil_mod is psutil

    def test_all_invariant_kinds_known(self, psutil_spec):
        for inv in psutil_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, psutil_spec):
        ids = [inv["id"] for inv in psutil_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestPsutilVersion
# ---------------------------------------------------------------------------

class TestPsutilVersion:
    def test_version_starts_with_digit(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["7"],
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


# ---------------------------------------------------------------------------
# TestPsutilCpu
# ---------------------------------------------------------------------------

class TestPsutilCpu:
    def test_cpu_count_ge_1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "cpu_count",
                "args": [],
                "method": "__ge__",
                "method_args": [1],
                "expected": True,
            },
        })
        assert ok, msg

    def test_cpu_count_has_bit_length(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "cpu_count",
                "args": [],
                "method": "bit_length",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_cpu_count_is_positive(self, psutil_mod):
        """Direct check: cpu_count() is a positive integer."""
        assert psutil_mod.cpu_count() >= 1

    def test_cpu_count_fails_on_zero_threshold(self, registry):
        """__ge__(0) should also be True; sanity check the method chain."""
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "cpu_count",
                "args": [],
                "method": "__ge__",
                "method_args": [0],
                "expected": True,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestPsutilMemory
# ---------------------------------------------------------------------------

class TestPsutilMemory:
    def test_memory_total_bool_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "virtual_memory",
                "args": [],
                "method": "total",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_memory_available_bool_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "virtual_memory",
                "args": [],
                "method": "available",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_memory_used_bool_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "virtual_memory",
                "args": [],
                "method": "used",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_memory_namedtuple_has_total(self, psutil_mod):
        """Direct check: virtual_memory() namedtuple has 'total' field."""
        vm = psutil_mod.virtual_memory()
        assert hasattr(vm, "total")
        assert hasattr(vm, "available")
        assert hasattr(vm, "percent")


# ---------------------------------------------------------------------------
# TestPsutilDisk
# ---------------------------------------------------------------------------

class TestPsutilDisk:
    def test_disk_total_bool_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "disk_usage",
                "args": ["/"],
                "method": "total",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_disk_used_bool_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "disk_usage",
                "args": ["/"],
                "method": "used",
                "method_chain": "__bool__",
                "expected": True,
            },
        })
        assert ok, msg

    def test_disk_namedtuple_has_fields(self, psutil_mod):
        """Direct check: disk_usage('/') has total, used, free, percent."""
        du = psutil_mod.disk_usage("/")
        assert hasattr(du, "total")
        assert hasattr(du, "used")
        assert hasattr(du, "free")
        assert hasattr(du, "percent")


# ---------------------------------------------------------------------------
# TestPsutilProcess
# ---------------------------------------------------------------------------

class TestPsutilProcess:
    def test_pid_zero_exists(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pid_exists",
                "args": [0],
                "expected": True,
            },
        })
        assert ok, msg

    def test_negative_pid_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pid_exists",
                "args": [-1],
                "expected": False,
            },
        })
        assert ok, msg

    def test_huge_pid_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pid_exists",
                "args": [99999999],
                "expected": False,
            },
        })
        assert ok, msg

    def test_negative_large_pid_false(self, registry):
        """Extra check: another large negative PID is also invalid."""
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pid_exists",
                "args": [-999999],
                "expected": False,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestPsutilConstants
# ---------------------------------------------------------------------------

class TestPsutilConstants:
    def test_status_running(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "STATUS_RUNNING.__eq__",
                "args": ["running"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_status_sleeping(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "STATUS_SLEEPING.__eq__",
                "args": ["sleeping"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_conn_established(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "CONN_ESTABLISHED.__eq__",
                "args": ["ESTABLISHED"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_status_running_wrong_value_fails(self, registry):
        """Sanity check: wrong constant value fails."""
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "STATUS_RUNNING.__eq__",
                "args": ["stopped"],
                "expected": True,
            },
        })
        assert not ok

    def test_status_constants_are_strings(self, psutil_mod):
        """Direct check: constant values are plain strings."""
        assert isinstance(psutil_mod.STATUS_RUNNING, str)
        assert isinstance(psutil_mod.STATUS_SLEEPING, str)
        assert isinstance(psutil_mod.CONN_ESTABLISHED, str)


# ---------------------------------------------------------------------------
# TestPsutilPlatform
# ---------------------------------------------------------------------------

class TestPsutilPlatform:
    def test_posix_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "POSIX.__eq__",
                "args": [True],
                "expected": True,
            },
        })
        assert ok, msg

    def test_windows_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "WINDOWS.__eq__",
                "args": [False],
                "expected": True,
            },
        })
        assert ok, msg

    def test_posix_and_windows_are_mutually_exclusive(self, psutil_mod):
        """Direct check: POSIX and WINDOWS cannot both be True."""
        assert not (psutil_mod.POSIX and psutil_mod.WINDOWS)


# ---------------------------------------------------------------------------
# TestPsutilAll — all 17 psutil invariants must pass
# ---------------------------------------------------------------------------

class TestPsutilAll:
    def test_all_pass(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod)
        assert len(results) == 17

    def test_filter_by_category_version(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_cpu(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="cpu")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_memory(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="memory")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_disk(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="disk")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_process(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="process")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_constants(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="constants")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_platform(self, psutil_spec, psutil_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(psutil_spec, psutil_mod, filter_category="platform")
        assert len(results) == 2
        assert all(r.passed for r in results)
