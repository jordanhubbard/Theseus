"""
Tests for general Python-module pattern handlers in verify_behavior.py,
and integration tests for base64, json, and struct Z-layer specs.

Organized as:
  - _resolve_typed: typed value resolution
  - python_call_eq: general function call equality
  - python_call_raises: general exception checking (including re-exported classes)
  - python_encode_decode_roundtrip: base64 encode/decode cycle
  - python_struct_roundtrip: struct pack/unpack cycle
  - Base64 spec integration (20 invariants)
  - JSON spec integration (22 invariants)
  - Struct spec integration (24 invariants)
"""
import base64 as _base64
import json as _json
import struct as _struct
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

BASE64_SPEC = REPO_ROOT / "zspecs" / "base64.zspec.json"
JSON_SPEC   = REPO_ROOT / "zspecs" / "json.zspec.json"
STRUCT_SPEC = REPO_ROOT / "zspecs" / "struct.zspec.json"


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def base64_spec():
    return vb.SpecLoader().load(BASE64_SPEC)

@pytest.fixture(scope="module")
def json_spec():
    return vb.SpecLoader().load(JSON_SPEC)

@pytest.fixture(scope="module")
def struct_spec():
    return vb.SpecLoader().load(STRUCT_SPEC)

@pytest.fixture(scope="module")
def base64_mod(base64_spec):
    return vb.LibraryLoader().load(base64_spec["library"])

@pytest.fixture(scope="module")
def json_mod(json_spec):
    return vb.LibraryLoader().load(json_spec["library"])

@pytest.fixture(scope="module")
def struct_mod(struct_spec):
    return vb.LibraryLoader().load(struct_spec["library"])

@pytest.fixture(scope="module")
def b64_registry(base64_mod):
    return vb.PatternRegistry(base64_mod, {})

@pytest.fixture(scope="module")
def json_registry(json_mod):
    return vb.PatternRegistry(json_mod, {})

@pytest.fixture(scope="module")
def struct_registry(struct_mod):
    return vb.PatternRegistry(struct_mod, {})


# ---------------------------------------------------------------------------
# _resolve_typed
# ---------------------------------------------------------------------------

class TestResolveTyped:
    """Unit tests for the typed-value resolver used by python_call_eq."""

    @pytest.fixture(scope="class")
    def reg(self, base64_mod):
        return vb.PatternRegistry(base64_mod, {})

    def test_bytes_b64(self, reg):
        assert reg._resolve_typed({"type": "bytes_b64", "value": "Zm9v"}) == b"foo"

    def test_bytes_b64_empty(self, reg):
        assert reg._resolve_typed({"type": "bytes_b64", "value": ""}) == b""

    def test_bytes_ascii(self, reg):
        assert reg._resolve_typed({"type": "bytes_ascii", "value": "hello"}) == b"hello"

    def test_bytes_ascii_empty(self, reg):
        assert reg._resolve_typed({"type": "bytes_ascii", "value": ""}) == b""

    def test_bytes_hex(self, reg):
        assert reg._resolve_typed({"type": "bytes_hex", "value": "deadbeef"}) == b"\xde\xad\xbe\xef"

    def test_bytes_hex_empty(self, reg):
        assert reg._resolve_typed({"type": "bytes_hex", "value": ""}) == b""

    def test_str(self, reg):
        assert reg._resolve_typed({"type": "str", "value": "hello"}) == "hello"

    def test_int(self, reg):
        assert reg._resolve_typed({"type": "int", "value": 42}) == 42

    def test_float(self, reg):
        assert reg._resolve_typed({"type": "float", "value": 3.14}) == 3.14

    def test_bool_true(self, reg):
        assert reg._resolve_typed({"type": "bool", "value": True}) is True

    def test_null(self, reg):
        assert reg._resolve_typed({"type": "null"}) is None

    def test_tuple(self, reg):
        assert reg._resolve_typed({"type": "tuple", "value": [1, 2, 3]}) == (1, 2, 3)

    def test_tuple_empty(self, reg):
        assert reg._resolve_typed({"type": "tuple", "value": []}) == ()

    def test_json_passthrough(self, reg):
        v = [1, "a", None]
        assert reg._resolve_typed({"type": "json", "value": v}) == v

    def test_raw_int_passthrough(self, reg):
        assert reg._resolve_typed(42) == 42

    def test_raw_str_passthrough(self, reg):
        assert reg._resolve_typed("hello") == "hello"

    def test_raw_none_passthrough(self, reg):
        assert reg._resolve_typed(None) is None

    def test_raw_bool_passthrough(self, reg):
        assert reg._resolve_typed(True) is True

    def test_raw_list_passthrough(self, reg):
        assert reg._resolve_typed([1, 2]) == [1, 2]


# ---------------------------------------------------------------------------
# python_call_eq
# ---------------------------------------------------------------------------

class TestPythonCallEq:
    def test_b64encode_foo(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "b64encode",
                "args": [{"type": "bytes_ascii", "value": "foo"}],
                "expected": {"type": "bytes_ascii", "value": "Zm9v"},
            },
        })
        assert ok, msg

    def test_b64decode_foo(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "b64decode",
                "args": ["Zm9v"],
                "expected": {"type": "bytes_ascii", "value": "foo"},
            },
        })
        assert ok, msg

    def test_json_dumps_null(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "dumps", "args": [None], "expected": "null"},
        })
        assert ok, msg

    def test_json_loads_integer(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "loads", "args": ["42"], "expected": 42},
        })
        assert ok, msg

    def test_struct_pack_uint16(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pack",
                "args": [">H", 256],
                "expected": {"type": "bytes_hex", "value": "0100"},
            },
        })
        assert ok, msg

    def test_struct_unpack_returns_tuple_compared_to_list(self, struct_registry):
        """struct.unpack returns a tuple; spec uses a list; must compare equal."""
        ok, msg = struct_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpack",
                "args": [">H", {"type": "bytes_hex", "value": "0100"}],
                "expected": [256],
            },
        })
        assert ok, msg

    def test_struct_calcsize(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "calcsize", "args": [">H"], "expected": 2},
        })
        assert ok, msg

    def test_fails_on_wrong_expected(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "dumps", "args": [42], "expected": "99"},
        })
        assert not ok

    def test_fails_on_unknown_function(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "no_such_fn", "args": [], "expected": None},
        })
        assert not ok

    def test_kwargs_separators(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dumps",
                "args": [[1, 2, 3]],
                "kwargs": {"separators": {"type": "tuple", "value": [",", ":"]}},
                "expected": "[1,2,3]",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# python_call_raises
# ---------------------------------------------------------------------------

class TestPythonCallRaises:
    def test_json_loads_empty_raises(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": [""],
                "expected_exception": "json.JSONDecodeError",
            },
        })
        assert ok, msg

    def test_json_loads_nan_raises(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": ["nan"],
                "expected_exception": "json.JSONDecodeError",
            },
        })
        assert ok, msg

    def test_json_loads_truncated_raises(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": ["{"],
                "expected_exception": "json.JSONDecodeError",
            },
        })
        assert ok, msg

    def test_b64decode_invalid_raises(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "b64decode",
                "args": ["not!valid@base64"],
                "kwargs": {"validate": True},
                "expected_exception": "binascii.Error",
            },
        })
        assert ok, msg

    def test_struct_unpack_wrong_size_raises(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "unpack",
                "args": [">H", {"type": "bytes_hex", "value": "00"}],
                "expected_exception": "struct.error",
            },
        })
        assert ok, msg

    def test_fails_when_no_exception_raised(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": ["42"],
                "expected_exception": "json.JSONDecodeError",
            },
        })
        assert not ok

    def test_fails_on_wrong_exception_type(self, json_registry):
        ok, msg = json_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": [""],
                "expected_exception": "AttributeError",
            },
        })
        assert not ok

    def test_re_exported_exception_class(self, json_registry):
        """json.JSONDecodeError is a re-export of json.decoder.JSONDecodeError; isinstance must work."""
        ok, msg = json_registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": [""],
                "expected_exception": "json.JSONDecodeError",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# python_encode_decode_roundtrip
# ---------------------------------------------------------------------------

class TestEncodeDecodeRoundtrip:
    def test_standard_b64_roundtrip(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_encode_decode_roundtrip",
            "spec": {
                "encode_fn": "b64encode",
                "decode_fn": "b64decode",
                "inputs_b64": ["", "Zg==", "Zm9v", "Zm9vYmFy"],
            },
        })
        assert ok, msg

    def test_urlsafe_b64_roundtrip(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_encode_decode_roundtrip",
            "spec": {
                "encode_fn": "urlsafe_b64encode",
                "decode_fn": "urlsafe_b64decode",
                "inputs_b64": ["", "+//+", "Zm9v"],
            },
        })
        assert ok, msg

    def test_binary_data_roundtrip(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_encode_decode_roundtrip",
            "spec": {
                "encode_fn": "b64encode",
                "decode_fn": "b64decode",
                "inputs_b64": ["/wEB", "+//+"],
            },
        })
        assert ok, msg

    def test_empty_input_list(self, b64_registry):
        ok, msg = b64_registry.run({
            "kind": "python_encode_decode_roundtrip",
            "spec": {
                "encode_fn": "b64encode",
                "decode_fn": "b64decode",
                "inputs_b64": [],
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# python_struct_roundtrip
# ---------------------------------------------------------------------------

class TestStructRoundtrip:
    def test_single_uint16(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_struct_roundtrip",
            "spec": {"format": ">H", "test_cases": [[0], [256], [65535]]},
        })
        assert ok, msg

    def test_single_uint32_little_endian(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_struct_roundtrip",
            "spec": {"format": "<I", "test_cases": [[0], [1], [4294967295]]},
        })
        assert ok, msg

    def test_multi_field_BHI(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_struct_roundtrip",
            "spec": {"format": ">BHI", "values": [255, 1000, 305419896]},
        })
        assert ok, msg

    def test_fails_on_range_overflow(self, struct_registry):
        ok, msg = struct_registry.run({
            "kind": "python_struct_roundtrip",
            "spec": {"format": ">B", "test_cases": [[256]]},  # >B max is 255
        })
        assert not ok


# ---------------------------------------------------------------------------
# Base64 spec integration
# ---------------------------------------------------------------------------

class TestBase64SpecIntegration:
    def test_all_invariants_pass(self, base64_spec, base64_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(base64_spec, base64_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, [r.inv_id for r in failed]

    def test_invariant_count(self, base64_spec, base64_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(base64_spec, base64_mod)
        assert len(results) == 20

    def test_encode_vector_category(self, base64_spec, base64_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(base64_spec, base64_mod, filter_category="encode_vector")
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_roundtrip_category(self, base64_spec, base64_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(base64_spec, base64_mod, filter_category="roundtrip")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_all_invariant_kinds_known(self, base64_spec):
        for inv in base64_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS

    def test_all_ids_unique(self, base64_spec):
        ids = [inv["id"] for inv in base64_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_cli_exit_0(self):
        rc = vb.main([str(BASE64_SPEC)])
        assert rc == 0


# ---------------------------------------------------------------------------
# JSON spec integration
# ---------------------------------------------------------------------------

class TestJsonSpecIntegration:
    def test_all_invariants_pass(self, json_spec, json_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(json_spec, json_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, [r.inv_id for r in failed]

    def test_invariant_count(self, json_spec, json_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(json_spec, json_mod)
        assert len(results) == 22

    def test_dumps_category(self, json_spec, json_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(json_spec, json_mod, filter_category="dumps_primitives")
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_error_category(self, json_spec, json_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(json_spec, json_mod, filter_category="error")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_all_invariant_kinds_known(self, json_spec):
        for inv in json_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS

    def test_cli_exit_0(self):
        rc = vb.main([str(JSON_SPEC)])
        assert rc == 0


# ---------------------------------------------------------------------------
# Struct spec integration
# ---------------------------------------------------------------------------

class TestStructSpecIntegration:
    def test_all_invariants_pass(self, struct_spec, struct_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(struct_spec, struct_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, [r.inv_id for r in failed]

    def test_invariant_count(self, struct_spec, struct_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(struct_spec, struct_mod)
        assert len(results) == 24

    def test_pack_vector_category(self, struct_spec, struct_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(struct_spec, struct_mod, filter_category="pack_vector")
        assert len(results) == 9
        assert all(r.passed for r in results)

    def test_calcsize_category(self, struct_spec, struct_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(struct_spec, struct_mod, filter_category="calcsize")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_roundtrip_category(self, struct_spec, struct_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(struct_spec, struct_mod, filter_category="roundtrip")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_error_category(self, struct_spec, struct_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(struct_spec, struct_mod, filter_category="error")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_all_invariant_kinds_known(self, struct_spec):
        for inv in struct_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS

    def test_cli_exit_0(self):
        rc = vb.main([str(STRUCT_SPEC)])
        assert rc == 0
