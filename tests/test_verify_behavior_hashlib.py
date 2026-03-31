"""
Tests for the Python-module backend and hashlib-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - PythonModuleLoader: loading hashlib via the python_module backend
  - hashlib-specific pattern handlers (one test class per kind)
  - InvariantRunner integration: all 23 hashlib invariants pass
  - CLI: verify-behavior runs hashlib.zspec.json end-to-end
"""
import base64
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

HASHLIB_SPEC_PATH = REPO_ROOT / "zspecs" / "hashlib.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def hashlib_spec():
    return vb.SpecLoader().load(HASHLIB_SPEC_PATH)


@pytest.fixture(scope="module")
def hashlib_mod(hashlib_spec):
    return vb.LibraryLoader().load(hashlib_spec["library"])


@pytest.fixture(scope="module")
def constants_map(hashlib_spec):
    return vb.InvariantRunner().build_constants_map(hashlib_spec["constants"])


@pytest.fixture(scope="module")
def registry(hashlib_mod, constants_map):
    return vb.PatternRegistry(hashlib_mod, constants_map)


# ---------------------------------------------------------------------------
# PythonModuleLoader
# ---------------------------------------------------------------------------

class TestPythonModuleLoader:
    def test_loads_hashlib_spec(self, hashlib_spec):
        assert isinstance(hashlib_spec, dict)

    def test_all_required_sections_present(self, hashlib_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in hashlib_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, hashlib_spec):
        assert hashlib_spec["library"]["backend"] == "python_module"

    def test_loads_hashlib_module(self, hashlib_mod):
        import hashlib
        assert hashlib_mod is hashlib

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz",
            })

    def test_all_invariant_kinds_known(self, hashlib_spec):
        for inv in hashlib_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, hashlib_spec):
        ids = [inv["id"] for inv in hashlib_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# hash_known_vector
# ---------------------------------------------------------------------------

class TestHashKnownVector:
    def test_sha256_empty(self, registry):
        ok, msg = registry.run({
            "kind": "hash_known_vector",
            "spec": {
                "algorithm": "sha256",
                "data_b64": "",
                "expected_hex": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
        })
        assert ok, msg

    def test_sha256_abc(self, registry):
        ok, msg = registry.run({
            "kind": "hash_known_vector",
            "spec": {
                "algorithm": "sha256",
                "data_b64": "YWJj",
                "expected_hex": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            },
        })
        assert ok, msg

    def test_md5_empty(self, registry):
        ok, msg = registry.run({
            "kind": "hash_known_vector",
            "spec": {
                "algorithm": "md5",
                "data_b64": "",
                "expected_hex": "d41d8cd98f00b204e9800998ecf8427e",
            },
        })
        assert ok, msg

    def test_sha1_abc(self, registry):
        ok, msg = registry.run({
            "kind": "hash_known_vector",
            "spec": {
                "algorithm": "sha1",
                "data_b64": "YWJj",
                "expected_hex": "a9993e364706816aba3e25717850c26c9cd0d89d",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_expected_hex(self, registry):
        ok, msg = registry.run({
            "kind": "hash_known_vector",
            "spec": {
                "algorithm": "sha256",
                "data_b64": "",
                "expected_hex": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        })
        assert not ok

    def test_fails_on_unknown_algorithm(self, registry):
        ok, msg = registry.run({
            "kind": "hash_known_vector",
            "spec": {
                "algorithm": "nosuchthing",
                "data_b64": "",
                "expected_hex": "00",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# hash_incremental
# ---------------------------------------------------------------------------

class TestHashIncremental:
    def test_sha256_hello_chunks(self, registry):
        ok, msg = registry.run({
            "kind": "hash_incremental",
            "spec": {
                "algorithm": "sha256",
                "chunks": ["SGVs", "bG8="],
                "full_data_b64": "SGVsbG8=",
            },
        })
        assert ok, msg

    def test_sha1_incremental(self, registry):
        ok, msg = registry.run({
            "kind": "hash_incremental",
            "spec": {
                "algorithm": "sha1",
                "chunks": ["SGVs", "bG8="],
                "full_data_b64": "SGVsbG8=",
            },
        })
        assert ok, msg

    def test_md5_incremental(self, registry):
        ok, msg = registry.run({
            "kind": "hash_incremental",
            "spec": {
                "algorithm": "md5",
                "chunks": ["SGVs", "bG8="],
                "full_data_b64": "SGVsbG8=",
            },
        })
        assert ok, msg

    def test_single_chunk_equals_oneshot(self, registry):
        # A single chunk is still incremental; result must match oneshot
        ok, msg = registry.run({
            "kind": "hash_incremental",
            "spec": {
                "algorithm": "sha256",
                "chunks": ["YWJj"],
                "full_data_b64": "YWJj",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# hash_object_attr
# ---------------------------------------------------------------------------

class TestHashObjectAttr:
    def test_sha256_digest_size(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha256", "attr": "digest_size", "expected": 32},
        })
        assert ok, msg

    def test_sha256_block_size(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha256", "attr": "block_size", "expected": 64},
        })
        assert ok, msg

    def test_sha1_digest_size(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha1", "attr": "digest_size", "expected": 20},
        })
        assert ok, msg

    def test_md5_digest_size(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "md5", "attr": "digest_size", "expected": 16},
        })
        assert ok, msg

    def test_sha512_digest_size(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha512", "attr": "digest_size", "expected": 64},
        })
        assert ok, msg

    def test_sha256_name_attr(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha256", "attr": "name", "expected": "sha256"},
        })
        assert ok, msg

    def test_fails_on_wrong_value(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha256", "attr": "digest_size", "expected": 99},
        })
        assert not ok

    def test_fails_on_unknown_attr(self, registry):
        ok, msg = registry.run({
            "kind": "hash_object_attr",
            "spec": {"algorithm": "sha256", "attr": "no_such_attribute", "expected": 42},
        })
        assert not ok


# ---------------------------------------------------------------------------
# python_set_contains
# ---------------------------------------------------------------------------

class TestPythonSetContains:
    def test_algorithms_guaranteed_has_core_algorithms(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "algorithms_guaranteed",
                "must_contain": ["sha1", "sha256", "md5", "sha512"],
            },
        })
        assert ok, msg

    def test_algorithms_guaranteed_has_sha224_sha384(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "algorithms_guaranteed",
                "must_contain": ["sha224", "sha384"],
            },
        })
        assert ok, msg

    def test_fails_on_missing_algorithm(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "algorithms_guaranteed",
                "must_contain": ["no_such_algo_xyz"],
            },
        })
        assert not ok

    def test_fails_on_nonexistent_attribute(self, registry):
        ok, msg = registry.run({
            "kind": "python_set_contains",
            "spec": {
                "attribute": "no_such_attribute",
                "must_contain": ["sha256"],
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# hash_digest_consistency
# ---------------------------------------------------------------------------

class TestHashDigestConsistency:
    def test_sha256_digest_hexdigest_match(self, registry):
        ok, msg = registry.run({
            "kind": "hash_digest_consistency",
            "spec": {
                "algorithm": "sha256",
                "data_b64": "SGVsbG8gV29ybGQ=",
            },
        })
        assert ok, msg

    def test_sha1_digest_hexdigest_match(self, registry):
        ok, msg = registry.run({
            "kind": "hash_digest_consistency",
            "spec": {
                "algorithm": "sha1",
                "data_b64": "",
            },
        })
        assert ok, msg

    def test_md5_digest_hexdigest_match(self, registry):
        ok, msg = registry.run({
            "kind": "hash_digest_consistency",
            "spec": {
                "algorithm": "md5",
                "data_b64": "YWJj",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# hash_copy_independence
# ---------------------------------------------------------------------------

class TestHashCopyIndependence:
    def test_sha256_copy_does_not_affect_original(self, registry):
        ok, msg = registry.run({
            "kind": "hash_copy_independence",
            "spec": {
                "algorithm": "sha256",
                "initial_data_b64": "SGVs",
                "extra_data_b64": "bG8=",
            },
        })
        assert ok, msg

    def test_sha1_copy_does_not_affect_original(self, registry):
        ok, msg = registry.run({
            "kind": "hash_copy_independence",
            "spec": {
                "algorithm": "sha1",
                "initial_data_b64": "YWJj",
                "extra_data_b64": "ZGVm",
            },
        })
        assert ok, msg

    def test_empty_initial_data(self, registry):
        ok, msg = registry.run({
            "kind": "hash_copy_independence",
            "spec": {
                "algorithm": "sha256",
                "initial_data_b64": "",
                "extra_data_b64": "YWJj",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# hash_api_equivalence
# ---------------------------------------------------------------------------

class TestHashApiEquivalence:
    def test_sha256_new_equals_constructor(self, registry):
        ok, msg = registry.run({
            "kind": "hash_api_equivalence",
            "spec": {
                "algorithm": "sha256",
                "data_b64": "SGVsbG8gV29ybGQ=",
            },
        })
        assert ok, msg

    def test_sha1_new_equals_constructor(self, registry):
        ok, msg = registry.run({
            "kind": "hash_api_equivalence",
            "spec": {
                "algorithm": "sha1",
                "data_b64": "YWJj",
            },
        })
        assert ok, msg

    def test_md5_new_equals_constructor(self, registry):
        ok, msg = registry.run({
            "kind": "hash_api_equivalence",
            "spec": {
                "algorithm": "md5",
                "data_b64": "",
            },
        })
        assert ok, msg

    def test_fails_on_unknown_algorithm(self, registry):
        ok, msg = registry.run({
            "kind": "hash_api_equivalence",
            "spec": {
                "algorithm": "no_such_algo_xyz",
                "data_b64": "",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 23 hashlib invariants must pass
# ---------------------------------------------------------------------------

class TestHashlibInvariantRunner:
    def test_all_invariants_pass(self, hashlib_spec, hashlib_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(hashlib_spec, hashlib_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, hashlib_spec, hashlib_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(hashlib_spec, hashlib_mod)
        assert len(results) == 23

    def test_no_skips(self, hashlib_spec, hashlib_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(hashlib_spec, hashlib_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_category(self, hashlib_spec, hashlib_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(hashlib_spec, hashlib_mod, filter_category="known_vector")
        assert len(results) == 10  # 3 SHA-256, 2 SHA-1, 3 MD5, 2 SHA-512
        assert all(r.passed for r in results)

    def test_filter_incremental(self, hashlib_spec, hashlib_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(hashlib_spec, hashlib_mod, filter_category="incremental")
        assert len(results) == 3
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestHashlibCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(HASHLIB_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(HASHLIB_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "23 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(HASHLIB_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "hashlib.sha256.empty" in out
        assert "hashlib.sha256.abc" in out

    def test_filter_flag(self, capsys):
        vb.main([str(HASHLIB_SPEC_PATH), "--filter", "known_vector", "--verbose"])
        out = capsys.readouterr().out
        assert "known_vector" in out or "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(HASHLIB_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 23
        assert all(r["passed"] for r in data)
