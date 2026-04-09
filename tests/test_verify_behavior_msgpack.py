"""
Tests for the msgpack Z-layer behavioral spec.

Organized as:
  - TestMsgpackLoader: loading msgpack via the python_module backend
  - TestMsgpackVersion: version invariants (2)
  - TestMsgpackPack: pack_scalars invariants (7)
  - TestMsgpackPackStrings: pack_strings invariants (3)
  - TestMsgpackPackCollections: pack_collections invariants (2)
  - TestMsgpackUnpack: unpack invariants (4)
  - TestMsgpackRoundtrip: roundtrip invariants (4)
  - TestMsgpackAll: integration — all 22 invariants pass, count check
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

MSGPACK_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "msgpack.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def msgpack_spec():
    return vb.SpecLoader().load(MSGPACK_SPEC_PATH)


@pytest.fixture(scope="module")
def msgpack_mod(msgpack_spec):
    return vb.LibraryLoader().load(msgpack_spec["library"])


@pytest.fixture(scope="module")
def constants_map(msgpack_spec):
    return vb.InvariantRunner().build_constants_map(msgpack_spec.get("constants", {}))


@pytest.fixture(scope="module")
def registry(msgpack_mod, constants_map):
    return vb.PatternRegistry(msgpack_mod, constants_map)


# ---------------------------------------------------------------------------
# TestMsgpackLoader
# ---------------------------------------------------------------------------

class TestMsgpackLoader:
    def test_loads_msgpack_spec(self, msgpack_spec):
        assert isinstance(msgpack_spec, dict)

    def test_all_required_sections_present(self, msgpack_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in msgpack_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, msgpack_spec):
        assert msgpack_spec["library"]["backend"] == "python_module"

    def test_module_name_is_msgpack(self, msgpack_spec):
        assert msgpack_spec["library"]["module_name"] == "msgpack"

    def test_loads_msgpack_module(self, msgpack_mod):
        import msgpack
        assert msgpack_mod is msgpack

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz",
            })

    def test_all_invariant_kinds_known(self, msgpack_spec):
        for inv in msgpack_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, msgpack_spec):
        ids = [inv["id"] for inv in msgpack_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestMsgpackVersion
# ---------------------------------------------------------------------------

class TestMsgpackVersion:
    def test_version_major(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.__getitem__",
                "args": [0],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_version_length(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.__len__",
                "args": [],
                "expected": 3,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMsgpackPack
# ---------------------------------------------------------------------------

class TestMsgpackPack:
    def test_packb_none(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [None],
                "expected": {"type": "bytes_b64", "value": "wA=="},
            },
        })
        assert ok, msg

    def test_packb_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [False],
                "expected": {"type": "bytes_b64", "value": "wg=="},
            },
        })
        assert ok, msg

    def test_packb_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [True],
                "expected": {"type": "bytes_b64", "value": "ww=="},
            },
        })
        assert ok, msg

    def test_packb_zero(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [0],
                "expected": {"type": "bytes_b64", "value": "AA=="},
            },
        })
        assert ok, msg

    def test_packb_127(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [127],
                "expected": {"type": "bytes_b64", "value": "fw=="},
            },
        })
        assert ok, msg

    def test_packb_minus1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [-1],
                "expected": {"type": "bytes_b64", "value": "/w=="},
            },
        })
        assert ok, msg

    def test_packb_wrong_expected_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [0],
                "expected": {"type": "bytes_b64", "value": "wA=="},  # None's encoding, not 0
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestMsgpackPackStrings
# ---------------------------------------------------------------------------

class TestMsgpackPackStrings:
    def test_packb_empty_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [""],
                "expected": {"type": "bytes_b64", "value": "oA=="},
            },
        })
        assert ok, msg

    def test_packb_single_char(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": ["a"],
                "expected": {"type": "bytes_b64", "value": "oWE="},
            },
        })
        assert ok, msg

    def test_packb_hello(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": ["hello"],
                "expected": {"type": "bytes_b64", "value": "pWhlbGxv"},
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMsgpackPackCollections
# ---------------------------------------------------------------------------

class TestMsgpackPackCollections:
    def test_packb_empty_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [[]],
                "expected": {"type": "bytes_b64", "value": "kA=="},
            },
        })
        assert ok, msg

    def test_packb_list_one(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "packb",
                "args": [[1]],
                "expected": {"type": "bytes_b64", "value": "kQE="},
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMsgpackUnpack
# ---------------------------------------------------------------------------

class TestMsgpackUnpack:
    def test_unpackb_none(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "wA=="}],
                "expected": None,
            },
        })
        assert ok, msg

    def test_unpackb_true(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "ww=="}],
                "expected": True,
            },
        })
        assert ok, msg

    def test_unpackb_one(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "AQ=="}],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_unpackb_string_raw_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "pWhlbGxv"}],
                "kwargs": {"raw": False},
                "expected": "hello",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMsgpackRoundtrip
# ---------------------------------------------------------------------------

class TestMsgpackRoundtrip:
    def test_roundtrip_integer_42(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "Kg=="}],
                "expected": 42,
            },
        })
        assert ok, msg

    def test_roundtrip_integer_negative(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "0IA="}],
                "expected": -128,
            },
        })
        assert ok, msg

    def test_roundtrip_string_world(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "pXdvcmxk"}],
                "kwargs": {"raw": False},
                "expected": "world",
            },
        })
        assert ok, msg

    def test_roundtrip_list_1_2_3(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "unpackb",
                "args": [{"type": "bytes_b64", "value": "kwECAw=="}],
                "kwargs": {"raw": False},
                "expected": [1, 2, 3],
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMsgpackAll — integration: all 22 invariants pass, count check
# ---------------------------------------------------------------------------

class TestMsgpackAll:
    def test_all_pass(self, msgpack_spec, msgpack_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(msgpack_spec, msgpack_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, msgpack_spec, msgpack_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(msgpack_spec, msgpack_mod)
        assert len(results) == 32
