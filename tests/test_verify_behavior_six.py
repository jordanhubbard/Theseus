"""
Tests for the python_module backend and six-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestSixLoader: loading six via the python_module backend
  - TestSixVersion: version category invariants
  - TestSixConstants: constants category invariants (PY2/PY3)
  - TestSixByteUtils: byte_utils category invariants (byte2int, int2byte, indexbytes)
  - TestSixStringUtils: string_utils category invariants (ensure_binary, ensure_text, ensure_str)
  - TestSixBU: b_u category invariants (six.b, six.u)
  - TestSixAll: all 11 six invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

SIX_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "six.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def six_spec():
    return vb.SpecLoader().load(SIX_SPEC_PATH)


@pytest.fixture(scope="module")
def six_mod(six_spec):
    return vb.LibraryLoader().load(six_spec["library"])


@pytest.fixture(scope="module")
def constants_map(six_spec):
    return vb.InvariantRunner().build_constants_map(six_spec["constants"])


@pytest.fixture(scope="module")
def registry(six_mod, constants_map):
    return vb.PatternRegistry(six_mod, constants_map)


# ---------------------------------------------------------------------------
# TestSixLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestSixLoader:
    def test_loads_six_spec(self, six_spec):
        assert isinstance(six_spec, dict)

    def test_all_required_sections_present(self, six_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in six_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, six_spec):
        assert six_spec["library"]["backend"] == "python_module"

    def test_module_name_is_six(self, six_spec):
        assert six_spec["library"]["module_name"] == "six"

    def test_loads_six_module(self, six_mod):
        import six
        assert six_mod is six

    def test_all_invariant_kinds_known(self, six_spec):
        for inv in six_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, six_spec):
        ids = [inv["id"] for inv in six_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestSixVersion
# ---------------------------------------------------------------------------

class TestSixVersion:
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

    def test_version_is_string(self, six_mod):
        assert isinstance(six_mod.__version__, str)
        assert len(six_mod.__version__) > 0


# ---------------------------------------------------------------------------
# TestSixConstants
# ---------------------------------------------------------------------------

class TestSixConstants:
    def test_py2_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PY2.__eq__",
                "args": [False],
                "expected": True,
            },
        })
        assert ok, msg

    def test_py3_is_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PY3.__eq__",
                "args": [True],
                "expected": True,
            },
        })
        assert ok, msg

    def test_py2_and_py3_mutually_exclusive(self, six_mod):
        """PY2 and PY3 are mutually exclusive — only one can be True."""
        assert not (six_mod.PY2 and six_mod.PY3)
        assert six_mod.PY2 or six_mod.PY3

    def test_py2_wrong_value_fails(self, registry):
        """Sanity check: PY2.__eq__(True) should fail on Python 3."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PY2.__eq__",
                "args": [True],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestSixByteUtils
# ---------------------------------------------------------------------------

class TestSixByteUtils:
    def test_byte2int_A(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "byte2int",
                "args": [{"type": "bytes_b64", "value": "QQ=="}],
                "expected": 65,
            },
        })
        assert ok, msg

    def test_int2byte_65(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "int2byte",
                "args": [65],
                "expected": {"type": "bytes_b64", "value": "QQ=="},
            },
        })
        assert ok, msg

    def test_indexbytes_hello_0(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "indexbytes",
                "args": [{"type": "bytes_b64", "value": "aGVsbG8="}, 0],
                "expected": 104,
            },
        })
        assert ok, msg

    def test_byte2int_int2byte_roundtrip(self, six_mod):
        """Direct check: byte2int and int2byte are inverses."""
        assert six_mod.byte2int(six_mod.int2byte(65)) == 65
        assert six_mod.int2byte(six_mod.byte2int(b'A')) == b'A'


# ---------------------------------------------------------------------------
# TestSixStringUtils
# ---------------------------------------------------------------------------

class TestSixStringUtils:
    def test_ensure_binary_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ensure_binary",
                "args": ["hello"],
                "expected": {"type": "bytes_b64", "value": "aGVsbG8="},
            },
        })
        assert ok, msg

    def test_ensure_text_bytes(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ensure_text",
                "args": [{"type": "bytes_b64", "value": "aGVsbG8="}],
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_ensure_str_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ensure_str",
                "args": ["hello"],
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_ensure_binary_returns_bytes(self, six_mod):
        """Direct check: ensure_binary always returns bytes."""
        assert isinstance(six_mod.ensure_binary("hello"), bytes)
        assert isinstance(six_mod.ensure_binary(b"hello"), bytes)

    def test_ensure_text_returns_str(self, six_mod):
        """Direct check: ensure_text always returns str."""
        assert isinstance(six_mod.ensure_text("hello"), str)
        assert isinstance(six_mod.ensure_text(b"hello"), str)


# ---------------------------------------------------------------------------
# TestSixBU
# ---------------------------------------------------------------------------

class TestSixBU:
    def test_b_hello(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "b",
                "args": ["hello"],
                "expected": {"type": "bytes_b64", "value": "aGVsbG8="},
            },
        })
        assert ok, msg

    def test_u_hello(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "u",
                "args": ["hello"],
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_b_returns_bytes(self, six_mod):
        """Direct check: six.b() always returns bytes."""
        assert isinstance(six_mod.b("hello"), bytes)

    def test_u_returns_str(self, six_mod):
        """Direct check: six.u() always returns str."""
        assert isinstance(six_mod.u("hello"), str)


# ---------------------------------------------------------------------------
# TestSixAll — all 11 six invariants must pass
# ---------------------------------------------------------------------------

class TestSixAll:
    def test_all_pass(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod)
        assert len(results) == 11

    def test_filter_by_category_version(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod, filter_category="version")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_constants(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod, filter_category="constants")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_byte_utils(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod, filter_category="byte_utils")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_string_utils(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod, filter_category="string_utils")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_b_u(self, six_spec, six_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(six_spec, six_mod, filter_category="b_u")
        assert len(results) == 2
        assert all(r.passed for r in results)
