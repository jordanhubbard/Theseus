"""
Tests for re and sqlite3 Z-layer specs.

re.zspec.json    — python_module backend, pure functions (sub, findall, split, escape, error)
sqlite3.zspec.json — python_module backend with new python_sqlite_roundtrip kind
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT       = Path(__file__).resolve().parent.parent
RE_SPEC_PATH    = REPO_ROOT / "_build" / "zspecs" / "re.zspec.json"
SQ_SPEC_PATH    = REPO_ROOT / "_build" / "zspecs" / "sqlite3.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def re_spec():
    return vb.SpecLoader().load(RE_SPEC_PATH)


@pytest.fixture(scope="module")
def re_lib(re_spec):
    return vb.LibraryLoader().load(re_spec["library"])


@pytest.fixture(scope="module")
def re_registry(re_lib):
    return vb.PatternRegistry(re_lib, {})


@pytest.fixture(scope="module")
def sq_spec():
    return vb.SpecLoader().load(SQ_SPEC_PATH)


@pytest.fixture(scope="module")
def sq_lib(sq_spec):
    return vb.LibraryLoader().load(sq_spec["library"])


@pytest.fixture(scope="module")
def sq_registry(sq_lib):
    return vb.PatternRegistry(sq_lib, {})


# ---------------------------------------------------------------------------
# re — unit tests
# ---------------------------------------------------------------------------

class TestReBackend:
    def test_loads_as_python_module(self, re_lib):
        import re
        assert re_lib is re

    def test_spec_backend(self, re_spec):
        assert re_spec["library"]["backend"] == "python_module"
        assert re_spec["library"]["module_name"] == "re"

    def test_all_kinds_known(self, re_spec):
        for inv in re_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


class TestReSubstitution:
    def test_whitespace_to_dash(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "sub",
                "args": [
                    {"type": "str", "value": r"\s+"},
                    {"type": "str", "value": "-"},
                    {"type": "str", "value": "hello world foo"},
                ],
                "expected": {"type": "str", "value": "hello-world-foo"},
            },
        })
        assert ok, msg

    def test_digit_replacement(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "sub",
                "args": [
                    {"type": "str", "value": r"\d"},
                    {"type": "str", "value": "X"},
                    {"type": "str", "value": "a1b2c3"},
                ],
                "expected": {"type": "str", "value": "aXbXcX"},
            },
        })
        assert ok, msg

    def test_noop_no_match(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "sub",
                "args": [
                    {"type": "str", "value": "x"},
                    {"type": "str", "value": "y"},
                    {"type": "str", "value": "no match here"},
                ],
                "expected": {"type": "str", "value": "no match here"},
            },
        })
        assert ok, msg


class TestReFindall:
    def test_digits(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "findall",
                "args": [
                    {"type": "str", "value": r"\d+"},
                    {"type": "str", "value": "a1b22c333"},
                ],
                "expected": {"type": "json", "value": ["1", "22", "333"]},
            },
        })
        assert ok, msg

    def test_no_match_empty_list(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "findall",
                "args": [
                    {"type": "str", "value": r"\d+"},
                    {"type": "str", "value": "no digits"},
                ],
                "expected": {"type": "json", "value": []},
            },
        })
        assert ok, msg


class TestReSplit:
    def test_whitespace(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "split",
                "args": [
                    {"type": "str", "value": r"\s+"},
                    {"type": "str", "value": "hello world foo"},
                ],
                "expected": {"type": "json", "value": ["hello", "world", "foo"]},
            },
        })
        assert ok, msg

    def test_comma(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "split",
                "args": [
                    {"type": "str", "value": ","},
                    {"type": "str", "value": "a,b,c"},
                ],
                "expected": {"type": "json", "value": ["a", "b", "c"]},
            },
        })
        assert ok, msg


class TestReEscape:
    def test_dot_parens(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": [{"type": "str", "value": "foo.bar(baz)"}],
                "expected": {"type": "str", "value": r"foo\.bar\(baz\)"},
            },
        })
        assert ok, msg

    def test_plain_alphanumeric_unchanged(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": [{"type": "str", "value": "abc123"}],
                "expected": {"type": "str", "value": "abc123"},
            },
        })
        assert ok, msg


class TestReError:
    def test_invalid_pattern_raises(self, re_registry):
        ok, msg = re_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "compile",
                "args": [{"type": "str", "value": "[invalid"}],
                "expected_exception": "re.error",
            },
        })
        assert ok, msg


class TestReSpecIntegration:
    def test_all_invariants_pass(self, re_spec, re_lib):
        runner  = vb.InvariantRunner()
        results = runner.run_all(re_spec, re_lib)
        failed  = [r for r in results if not r.passed and not r.skip_reason]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, re_spec, re_lib):
        assert len(vb.InvariantRunner().run_all(re_spec, re_lib)) == 22

    def test_cli_exit_0(self):
        assert vb.main([str(RE_SPEC_PATH)]) == 0

    def test_all_ids_unique(self, re_spec):
        ids = [inv["id"] for inv in re_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# sqlite3 — unit tests
# ---------------------------------------------------------------------------

class TestSqlite3Backend:
    def test_loads_as_python_module(self, sq_lib):
        import sqlite3
        assert sq_lib is sqlite3

    def test_spec_backend(self, sq_spec):
        assert sq_spec["library"]["backend"] == "python_module"
        assert sq_spec["library"]["module_name"] == "sqlite3"

    def test_all_kinds_known(self, sq_spec):
        for inv in sq_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


class TestSqliteCompleteStatement:
    def test_complete_with_semicolon(self, sq_registry):
        ok, msg = sq_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "complete_statement",
                "args": [{"type": "str", "value": "SELECT 1;"}],
                "expected": {"type": "bool", "value": True},
            },
        })
        assert ok, msg

    def test_incomplete_without_semicolon(self, sq_registry):
        ok, msg = sq_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "complete_statement",
                "args": [{"type": "str", "value": "SELECT 1"}],
                "expected": {"type": "bool", "value": False},
            },
        })
        assert ok, msg


class TestSqliteRoundtrip:
    def _run_roundtrip(self, registry, setup_sql, query_sql, expected_rows):
        return registry.run({
            "kind": "python_sqlite_roundtrip",
            "spec": {
                "setup_sql": setup_sql,
                "query_sql": query_sql,
                "expected_rows": expected_rows,
            },
        })

    def test_integer_and_text(self, sq_registry):
        ok, msg = self._run_roundtrip(
            sq_registry,
            setup_sql=[
                "CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)",
                "INSERT INTO t VALUES (1, 'foo')",
                "INSERT INTO t VALUES (2, 'bar')",
            ],
            query_sql="SELECT id, val FROM t ORDER BY id",
            expected_rows=[[1, "foo"], [2, "bar"]],
        )
        assert ok, msg

    def test_null_value(self, sq_registry):
        ok, msg = self._run_roundtrip(
            sq_registry,
            setup_sql=[
                "CREATE TABLE t (id INTEGER, val TEXT)",
                "INSERT INTO t VALUES (1, NULL)",
            ],
            query_sql="SELECT id, val FROM t",
            expected_rows=[[1, None]],
        )
        assert ok, msg

    def test_aggregation_count(self, sq_registry):
        ok, msg = self._run_roundtrip(
            sq_registry,
            setup_sql=[
                "CREATE TABLE t (x INTEGER)",
                "INSERT INTO t VALUES (1)",
                "INSERT INTO t VALUES (2)",
                "INSERT INTO t VALUES (3)",
            ],
            query_sql="SELECT COUNT(*) FROM t",
            expected_rows=[[3]],
        )
        assert ok, msg

    def test_empty_result(self, sq_registry):
        ok, msg = self._run_roundtrip(
            sq_registry,
            setup_sql=["CREATE TABLE t (x INTEGER)"],
            query_sql="SELECT * FROM t",
            expected_rows=[],
        )
        assert ok, msg

    def test_wrong_expected_fails(self, sq_registry):
        ok, _ = self._run_roundtrip(
            sq_registry,
            setup_sql=["CREATE TABLE t (x INTEGER)", "INSERT INTO t VALUES (1)"],
            query_sql="SELECT x FROM t",
            expected_rows=[[999]],
        )
        assert not ok

    def test_bad_sql_is_error(self, sq_registry):
        ok, msg = sq_registry.run({
            "kind": "python_sqlite_roundtrip",
            "spec": {
                "setup_sql": ["NOT VALID SQL"],
                "query_sql": "SELECT 1",
                "expected_rows": [[1]],
            },
        })
        assert not ok
        assert "raised" in msg


class TestSqliteSpecIntegration:
    def test_all_invariants_pass(self, sq_spec, sq_lib):
        runner  = vb.InvariantRunner()
        results = runner.run_all(sq_spec, sq_lib)
        failed  = [r for r in results if not r.passed and not r.skip_reason]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, sq_spec, sq_lib):
        assert len(vb.InvariantRunner().run_all(sq_spec, sq_lib)) == 20

    def test_cli_exit_0(self):
        assert vb.main([str(SQ_SPEC_PATH)]) == 0

    def test_all_ids_unique(self, sq_spec):
        ids = [inv["id"] for inv in sq_spec["invariants"]]
        assert len(ids) == len(set(ids))
