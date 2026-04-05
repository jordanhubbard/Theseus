"""
Tests for the python_module backend and numpy-specific pattern handling
in tools/verify_behavior.py.

Organized as:
  - PythonModuleLoader: loading numpy via the python_module backend
  - TestNumpyDtype: dtype / itemsize invariants (category: dtype)
  - TestNumpyArray: shape, ndim, size invariants (category: array)
  - TestNumpyConstants: pi and e via deterministic function calls (category: constants)
  - TestNumpyArithmetic: add, multiply, power, abs (category: arithmetic)
  - TestNumpyOps: sum, max, min, mean with plain list args (category: ops)
  - TestNumpyErrors: reshape raises ValueError (category: errors)
  - TestNumpyAll: integration — all 20 invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

NUMPY_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "numpy.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def numpy_spec():
    pytest.importorskip("numpy", reason="numpy not installed — skipping all numpy spec tests")
    return vb.SpecLoader().load(NUMPY_SPEC_PATH)


@pytest.fixture(scope="module")
def numpy_mod(numpy_spec):
    return vb.LibraryLoader().load(numpy_spec["library"])


@pytest.fixture(scope="module")
def constants_map(numpy_spec):
    return vb.InvariantRunner().build_constants_map(numpy_spec["constants"])


@pytest.fixture(scope="module")
def registry(numpy_mod, constants_map):
    return vb.PatternRegistry(numpy_mod, constants_map)


# ---------------------------------------------------------------------------
# Spec loading / metadata checks
# ---------------------------------------------------------------------------

class TestNumpySpecLoader:
    def test_loads_numpy_spec(self, numpy_spec):
        assert isinstance(numpy_spec, dict)

    def test_all_required_sections_present(self, numpy_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in numpy_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, numpy_spec):
        assert numpy_spec["library"]["backend"] == "python_module"

    def test_module_name_is_numpy(self, numpy_spec):
        assert numpy_spec["library"]["module_name"] == "numpy"

    def test_all_invariant_ids_unique(self, numpy_spec):
        ids = [inv["id"] for inv in numpy_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_all_invariant_kinds_known(self, numpy_spec):
        for inv in numpy_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_loads_numpy_module(self, numpy_mod):
        import numpy
        assert numpy_mod is numpy


# ---------------------------------------------------------------------------
# dtype / itemsize (category: dtype)
# ---------------------------------------------------------------------------

class TestNumpyDtype:
    def test_float64_itemsize(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dtype",
                "args": ["float64"],
                "method": "itemsize",
                "expected": 8,
            },
        })
        assert ok, msg

    def test_int32_itemsize(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dtype",
                "args": ["int32"],
                "method": "itemsize",
                "expected": 4,
            },
        })
        assert ok, msg

    def test_bool_itemsize(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dtype",
                "args": ["bool"],
                "method": "itemsize",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_complex128_itemsize(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dtype",
                "args": ["complex128"],
                "method": "itemsize",
                "expected": 16,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_itemsize(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dtype",
                "args": ["float64"],
                "method": "itemsize",
                "expected": 999,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# array shape / ndim (category: array)
# ---------------------------------------------------------------------------

class TestNumpyArray:
    def test_shape_1d(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "shape",
                "args": [[1, 2, 3]],
                "expected": [3],
            },
        })
        assert ok, msg

    def test_shape_2d(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "shape",
                "args": [[[1, 2, 3], [4, 5, 6]]],
                "expected": [2, 3],
            },
        })
        assert ok, msg

    def test_ndim_2d(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ndim",
                "args": [[[1, 2], [3, 4]]],
                "expected": 2,
            },
        })
        assert ok, msg

    def test_ndim_1d(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ndim",
                "args": [[1, 2, 3]],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_size_empty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "size",
                "args": [[]],
                "expected": 0,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# math constants (category: constants)
# ---------------------------------------------------------------------------

class TestNumpyConstants:
    def test_pi_via_arccos(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "arccos",
                "args": [-1.0],
                "expected": 3.141592653589793,
            },
        })
        assert ok, msg

    def test_e_via_exp(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exp",
                "args": [1.0],
                "expected": 2.718281828459045,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# arithmetic (category: arithmetic)
# ---------------------------------------------------------------------------

class TestNumpyArithmetic:
    def test_add_3_4(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "add",
                "args": [3, 4],
                "expected": 7,
            },
        })
        assert ok, msg

    def test_multiply_6_7(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "multiply",
                "args": [6, 7],
                "expected": 42,
            },
        })
        assert ok, msg

    def test_power_2_10(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "power",
                "args": [2, 10],
                "expected": 1024,
            },
        })
        assert ok, msg

    def test_abs_neg5(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "abs",
                "args": [-5],
                "expected": 5,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# array ops (category: ops)
# ---------------------------------------------------------------------------

class TestNumpyOps:
    def test_sum_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "sum",
                "args": [[1, 2, 3, 4, 5]],
                "expected": 15,
            },
        })
        assert ok, msg

    def test_max_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "max",
                "args": [[3, 1, 4, 1, 5]],
                "expected": 5,
            },
        })
        assert ok, msg

    def test_min_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "min",
                "args": [[3, 1, 4, 1, 5]],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_mean_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "mean",
                "args": [[1, 2, 3, 4, 5]],
                "expected": 3.0,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# error cases (category: errors)
# ---------------------------------------------------------------------------

class TestNumpyErrors:
    def test_reshape_size_mismatch_raises_value_error(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "reshape",
                "args": [[1, 2, 3], [2, 2]],
                "expected_exception": "ValueError",
            },
        })
        assert ok, msg

    def test_reshape_wrong_exception_type_does_not_match(self, registry):
        # Sanity: a TypeError is not a ValueError — should fail to match
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "reshape",
                "args": [[1, 2, 3], [2, 2]],
                "expected_exception": "TypeError",
            },
        })
        # reshape raises ValueError, not TypeError — so this should NOT match
        assert not ok


# ---------------------------------------------------------------------------
# Integration — all 20 numpy invariants must pass
# ---------------------------------------------------------------------------

class TestNumpyAll:
    def test_all_pass(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod)
        assert len(results) == 20

    def test_no_skips(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_dtype_category(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod, filter_category="dtype")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_arithmetic_category(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod, filter_category="arithmetic")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_ops_category(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod, filter_category="ops")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_errors_category(self, numpy_spec, numpy_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(numpy_spec, numpy_mod, filter_category="errors")
        assert len(results) == 1
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestNumpyCLI:
    def test_exit_code_0_all_pass(self, numpy_spec):
        rc = vb.main([str(NUMPY_SPEC_PATH)])
        assert rc == 0

    def test_verbose_shows_pass_and_count(self, numpy_spec, capsys):
        vb.main([str(NUMPY_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "20 invariants" in out

    def test_list_flag_shows_ids(self, numpy_spec, capsys):
        rc = vb.main([str(NUMPY_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "numpy.dtype.float64" in out
        assert "numpy.arithmetic.add_3_4" in out
