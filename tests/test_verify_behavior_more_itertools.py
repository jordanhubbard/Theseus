"""
Tests for the python_module backend and more_itertools-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestMoreItertoolsLoader: loading more_itertools via the python_module backend
  - TestMoreItertoolsVersion: version category invariants
  - TestMoreItertoolsChunked: chunked iterator invariants
  - TestMoreItertoolsFirstLast: first/last scalar invariants
  - TestMoreItertoolsFlatten: flatten iterator invariants
  - TestMoreItertoolsTakeTail: take (list) and tail (iterator) invariants
  - TestMoreItertoolsOne: one() and nth() scalar invariants
  - TestMoreItertoolsUnique: unique_everseen iterator invariants
  - TestMoreItertoolsBatched: batched iterator invariants
  - TestMoreItertoolsAll: all 14 invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

MI_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "more_itertools.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mi_spec():
    return vb.SpecLoader().load(MI_SPEC_PATH)


@pytest.fixture(scope="module")
def mi_mod(mi_spec):
    return vb.LibraryLoader().load(mi_spec["library"])


@pytest.fixture(scope="module")
def constants_map(mi_spec):
    return vb.InvariantRunner().build_constants_map(mi_spec["constants"])


@pytest.fixture(scope="module")
def registry(mi_mod, constants_map):
    return vb.PatternRegistry(mi_mod, constants_map)


# ---------------------------------------------------------------------------
# TestMoreItertoolsLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestMoreItertoolsLoader:
    def test_loads_spec(self, mi_spec):
        assert isinstance(mi_spec, dict)

    def test_all_required_sections_present(self, mi_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in mi_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, mi_spec):
        assert mi_spec["library"]["backend"] == "python_module"

    def test_module_name_is_more_itertools(self, mi_spec):
        assert mi_spec["library"]["module_name"] == "more_itertools"

    def test_loads_more_itertools_module(self, mi_mod):
        import more_itertools
        assert mi_mod is more_itertools

    def test_all_invariant_kinds_known(self, mi_spec):
        for inv in mi_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, mi_spec):
        ids = [inv["id"] for inv in mi_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_14(self, mi_spec):
        assert len(mi_spec["invariants"]) == 14


# ---------------------------------------------------------------------------
# TestMoreItertoolsVersion
# ---------------------------------------------------------------------------

class TestMoreItertoolsVersion:
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

    def test_version_nonempty(self, mi_mod):
        assert isinstance(mi_mod.__version__, str)
        assert len(mi_mod.__version__) > 0

    def test_version_has_numeric_major(self, mi_mod):
        major = mi_mod.__version__.split(".")[0]
        assert major.isdigit(), f"Major version {major!r} is not numeric"


# ---------------------------------------------------------------------------
# TestMoreItertoolsChunked
# ---------------------------------------------------------------------------

class TestMoreItertoolsChunked:
    def test_first_chunk_two_elements(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "chunked",
                "args": [[1, 2, 3, 4], 2],
                "method": "__next__",
                "expected": [1, 2],
            },
        })
        assert ok, msg

    def test_even_split_first_chunk(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "chunked",
                "args": [[0, 1, 2, 3, 4, 5], 3],
                "method": "__next__",
                "expected": [0, 1, 2],
            },
        })
        assert ok, msg

    def test_chunked_yields_lists(self, mi_mod):
        result = list(mi_mod.chunked([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_chunked_last_chunk_can_be_shorter(self, mi_mod):
        result = list(mi_mod.chunked([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]


# ---------------------------------------------------------------------------
# TestMoreItertoolsFirstLast
# ---------------------------------------------------------------------------

class TestMoreItertoolsFirstLast:
    def test_first_of_three(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "first",
                "args": [[10, 20, 30]],
                "kwargs": {},
                "expected": 10,
            },
        })
        assert ok, msg

    def test_last_of_three(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "last",
                "args": [[10, 20, 30]],
                "kwargs": {},
                "expected": 30,
            },
        })
        assert ok, msg

    def test_first_default(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "first",
                "args": [[]],
                "kwargs": {"default": 99},
                "expected": 99,
            },
        })
        assert ok, msg

    def test_first_and_last_agree_on_singleton(self, mi_mod):
        assert mi_mod.first([7]) == mi_mod.last([7]) == 7


# ---------------------------------------------------------------------------
# TestMoreItertoolsFlatten
# ---------------------------------------------------------------------------

class TestMoreItertoolsFlatten:
    def test_flatten_first_element(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "flatten",
                "args": [[[1, 2], [3, 4]]],
                "method": "__next__",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_flatten_full_output(self, mi_mod):
        result = list(mi_mod.flatten([[1, 2], [3, 4]]))
        assert result == [1, 2, 3, 4]

    def test_flatten_empty_sublists(self, mi_mod):
        result = list(mi_mod.flatten([[], [1], [], [2, 3]]))
        assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# TestMoreItertoolsTakeTail
# ---------------------------------------------------------------------------

class TestMoreItertoolsTakeTail:
    def test_take_returns_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "take",
                "args": [3, [0, 1, 2, 3, 4]],
                "expected": [0, 1, 2],
            },
        })
        assert ok, msg

    def test_tail_first_of_last_three(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "tail",
                "args": [3, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]],
                "method": "__next__",
                "expected": 7,
            },
        })
        assert ok, msg

    def test_take_is_list_type(self, mi_mod):
        result = mi_mod.take(3, range(10))
        assert isinstance(result, list)
        assert result == [0, 1, 2]

    def test_tail_last_three(self, mi_mod):
        result = list(mi_mod.tail(3, range(10)))
        assert result == [7, 8, 9]


# ---------------------------------------------------------------------------
# TestMoreItertoolsOne
# ---------------------------------------------------------------------------

class TestMoreItertoolsOne:
    def test_one_single_element(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "one",
                "args": [[42]],
                "expected": 42,
            },
        })
        assert ok, msg

    def test_nth_second_element(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nth",
                "args": [[10, 20, 30], 1],
                "expected": 20,
            },
        })
        assert ok, msg

    def test_one_raises_on_empty(self, mi_mod):
        with pytest.raises(ValueError):
            mi_mod.one([])

    def test_one_raises_on_multiple(self, mi_mod):
        with pytest.raises(ValueError):
            mi_mod.one([1, 2])

    def test_nth_first_element(self, mi_mod):
        assert mi_mod.nth([10, 20, 30], 0) == 10


# ---------------------------------------------------------------------------
# TestMoreItertoolsUnique
# ---------------------------------------------------------------------------

class TestMoreItertoolsUnique:
    def test_unique_everseen_first_element(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unique_everseen",
                "args": [[1, 2, 1, 3]],
                "method": "__next__",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_unique_everseen_deduplicates(self, mi_mod):
        result = list(mi_mod.unique_everseen([1, 2, 1, 3, 2]))
        assert result == [1, 2, 3]

    def test_unique_everseen_preserves_order(self, mi_mod):
        result = list(mi_mod.unique_everseen([3, 1, 2, 1, 3]))
        assert result == [3, 1, 2]


# ---------------------------------------------------------------------------
# TestMoreItertoolsBatched
# ---------------------------------------------------------------------------

class TestMoreItertoolsBatched:
    def test_batched_first_chunk(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "batched",
                "args": [[1, 2, 3, 4], 2],
                "method": "__next__",
                "expected": [1, 2],
            },
        })
        assert ok, msg

    def test_batched_yields_tuples(self, mi_mod):
        result = list(mi_mod.batched([1, 2, 3, 4], 2))
        assert result == [(1, 2), (3, 4)]

    def test_batched_last_chunk_shorter(self, mi_mod):
        result = list(mi_mod.batched([1, 2, 3, 4, 5], 2))
        assert result == [(1, 2), (3, 4), (5,)]


# ---------------------------------------------------------------------------
# TestMoreItertoolsAll — all 14 invariants must pass
# ---------------------------------------------------------------------------

class TestMoreItertoolsAll:
    def test_all_pass(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod)
        assert len(results) == 14

    def test_filter_by_category_version(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_chunked(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="chunked")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_first_last(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="first_last")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_flatten(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="flatten")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_take_tail(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="take_tail")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_one(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="one")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_unique(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="unique")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_batched(self, mi_spec, mi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(mi_spec, mi_mod, filter_category="batched")
        assert len(results) == 1
        assert all(r.passed for r in results)
