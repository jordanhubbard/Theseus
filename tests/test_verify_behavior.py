"""
Tests for tools/verify_behavior.py.

Tests are organized into:
  - SpecLoader: loading and validation
  - LibraryLoader: finding and setting up zlib
  - build_constants_map: flattening grouped constants
  - Pattern handlers: one test class per invariant kind
  - InvariantRunner: integration against the real spec
  - CLI / main(): argument handling and exit codes
"""
import base64
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

ZSPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "zlib.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def zlib_spec():
    return vb.SpecLoader().load(ZSPEC_PATH)


@pytest.fixture(scope="module")
def zlib_lib(zlib_spec):
    try:
        return vb.LibraryLoader().load(zlib_spec["library"])
    except vb.LibraryNotFoundError:
        pytest.skip("zlib shared library not found on this system")


@pytest.fixture(scope="module")
def constants_map(zlib_spec):
    return vb.InvariantRunner().build_constants_map(zlib_spec["constants"])


@pytest.fixture(scope="module")
def registry(zlib_lib, constants_map):
    return vb.PatternRegistry(zlib_lib, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader
# ---------------------------------------------------------------------------

class TestSpecLoader:
    def test_loads_real_zspec(self):
        spec = vb.SpecLoader().load(ZSPEC_PATH)
        assert isinstance(spec, dict)

    def test_all_required_sections_present(self, zlib_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in zlib_spec, f"Missing required section: {section}"

    def test_invariants_is_list(self, zlib_spec):
        assert isinstance(zlib_spec["invariants"], list)

    def test_rejects_nonexistent_file(self, tmp_path):
        with pytest.raises(vb.SpecError, match="Cannot read"):
            vb.SpecLoader().load(tmp_path / "nope.json")

    def test_rejects_bad_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(vb.SpecError, match="Invalid JSON"):
            vb.SpecLoader().load(bad)

    def test_rejects_missing_section(self, tmp_path):
        minimal = {s: {} for s in vb.REQUIRED_SECTIONS if s != "invariants"}
        minimal["invariants"] = []
        spec_file = tmp_path / "missing.json"
        spec_file.write_text(json.dumps(minimal), encoding="utf-8")
        # Remove one required section
        del minimal["constants"]
        spec_file.write_text(json.dumps(minimal), encoding="utf-8")
        with pytest.raises(vb.SpecError, match="Missing required sections"):
            vb.SpecLoader().load(spec_file)

    def test_rejects_invariants_not_list(self, tmp_path):
        spec = {s: {} for s in vb.REQUIRED_SECTIONS}
        spec["invariants"] = {"not": "a list"}
        spec_file = tmp_path / "bad_inv.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")
        with pytest.raises(vb.SpecError, match="invariants.*array"):
            vb.SpecLoader().load(spec_file)

    def test_schema_version_present(self, zlib_spec):
        assert zlib_spec["schema_version"] == "0.1"

    def test_all_invariant_ids_unique(self, zlib_spec):
        ids = [inv["id"] for inv in zlib_spec["invariants"]]
        assert len(ids) == len(set(ids)), "Duplicate invariant IDs found"

    def test_all_invariant_kinds_known(self, zlib_spec):
        for inv in zlib_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariants_have_id(self, zlib_spec):
        for inv in zlib_spec["invariants"]:
            assert inv.get("id"), "Invariant missing 'id'"

    def test_all_constants_have_value(self, zlib_spec):
        for group in zlib_spec["constants"].values():
            for entry in group:
                assert "value" in entry, f"Constant entry {entry.get('name')!r} missing 'value'"


# ---------------------------------------------------------------------------
# LibraryLoader
# ---------------------------------------------------------------------------

class TestLibraryLoader:
    def test_finds_zlib(self, zlib_lib):
        assert zlib_lib is not None

    def test_raises_on_unknown_library(self):
        with pytest.raises(vb.LibraryNotFoundError):
            vb.LibraryLoader().load({"soname_patterns": ["__does_not_exist_xyz_99__"]})

    def test_zlibVersion_is_callable(self, zlib_lib):
        ver = zlib_lib.zlibVersion()
        assert ver is not None
        assert ver.startswith(b"1.")


# ---------------------------------------------------------------------------
# build_constants_map
# ---------------------------------------------------------------------------

class TestConstantsMap:
    def test_flat_map_has_known_names(self, constants_map):
        for name in ("Z_OK", "Z_STREAM_END", "Z_DATA_ERROR", "Z_MEM_ERROR",
                     "Z_BUF_ERROR", "Z_VERSION_ERROR", "Z_STREAM_ERROR",
                     "Z_NEED_DICT", "Z_ERRNO"):
            assert name in constants_map, f"Missing constant: {name}"

    def test_Z_OK_is_zero(self, constants_map):
        assert constants_map["Z_OK"] == 0

    def test_Z_STREAM_END_is_one(self, constants_map):
        assert constants_map["Z_STREAM_END"] == 1

    def test_Z_DATA_ERROR_is_minus_three(self, constants_map):
        assert constants_map["Z_DATA_ERROR"] == -3

    def test_empty_constants_yields_empty_map(self):
        result = vb.InvariantRunner().build_constants_map({})
        assert result == {}

    def test_ignores_non_list_groups(self):
        result = vb.InvariantRunner().build_constants_map({"bad_group": "not a list"})
        assert result == {}


# ---------------------------------------------------------------------------
# Pattern: constant_eq
# ---------------------------------------------------------------------------

class TestPatternConstantEq:
    def _inv(self, name, expected):
        return {
            "id": f"test.const.{name}",
            "description": "",
            "category": "constant",
            "kind": "constant_eq",
            "spec": {"name": name, "expected_value": expected},
        }

    def test_pass_Z_OK(self, registry):
        passed, _ = registry.run(self._inv("Z_OK", 0))
        assert passed

    def test_pass_Z_DATA_ERROR(self, registry):
        passed, _ = registry.run(self._inv("Z_DATA_ERROR", -3))
        assert passed

    def test_fail_wrong_value(self, registry):
        passed, msg = registry.run(self._inv("Z_OK", 99))
        assert not passed
        assert "99" in msg

    def test_fail_unknown_name(self, registry):
        passed, msg = registry.run(self._inv("DOES_NOT_EXIST", 0))
        assert not passed
        assert "not in spec" in msg


# ---------------------------------------------------------------------------
# Pattern: call_eq (checksums)
# ---------------------------------------------------------------------------

class TestPatternCallEq:
    def _inv(self, fn, args, atypes, expected):
        return {
            "id": "test.call_eq",
            "description": "",
            "category": "checksum",
            "kind": "call_eq",
            "spec": {"function": fn, "args": args, "arg_types": atypes, "expected": expected},
        }

    def test_crc32_empty_is_zero(self, registry):
        passed, _ = registry.run(self._inv("crc32", [0, None, 0], ["int", "null", "int"], 0))
        assert passed

    def test_crc32_hello_known_vector(self, registry):
        # crc32(0, "hello", 5) == 0x3610a686 == 907060870
        passed, msg = registry.run(
            self._inv("crc32", [0, "aGVsbG8=", 5], ["int", "bytes_b64", "int"], 907060870)
        )
        assert passed, msg

    def test_adler32_init_is_one(self, registry):
        passed, _ = registry.run(self._inv("adler32", [1, None, 0], ["int", "null", "int"], 1))
        assert passed

    def test_crc32_wrong_expected_fails(self, registry):
        passed, msg = registry.run(
            self._inv("crc32", [0, None, 0], ["int", "null", "int"], 42)
        )
        assert not passed
        assert "42" in msg


# ---------------------------------------------------------------------------
# Pattern: call_returns (compress2)
# ---------------------------------------------------------------------------

class TestPatternCallReturns:
    def _inv(self, fn, src_b64, level, cap, expected):
        return {
            "id": "test.call_returns",
            "description": "",
            "category": "compress",
            "kind": "call_returns",
            "spec": {
                "function": fn,
                "src_b64": src_b64,
                "level": level,
                "dst_capacity": cap,
                "expected_return": expected,
            },
        }

    def test_compress2_ok_on_valid(self, registry):
        passed, msg = registry.run(
            self._inv("compress2", "SGVsbG8gV29ybGQ=", -1, 100, "Z_OK")
        )
        assert passed, msg

    def test_compress2_stream_error_on_bad_level(self, registry):
        passed, msg = registry.run(
            self._inv("compress2", "aGVsbG8=", 10, 100, "Z_STREAM_ERROR")
        )
        assert passed, msg

    def test_compress2_wrong_expectation_fails(self, registry):
        passed, _ = registry.run(
            self._inv("compress2", "SGVsbG8=", -1, 100, "Z_DATA_ERROR")
        )
        assert not passed


# ---------------------------------------------------------------------------
# Pattern: version_prefix
# ---------------------------------------------------------------------------

class TestPatternVersionPrefix:
    def _inv(self, prefix_b64):
        return {
            "id": "test.version",
            "description": "",
            "category": "version",
            "kind": "version_prefix",
            "spec": {"function": "zlibVersion", "expected_prefix_b64": prefix_b64},
        }

    def test_version_starts_with_1_dot(self, registry):
        passed, msg = registry.run(self._inv("MS4="))  # base64("1.")
        assert passed, msg

    def test_version_wrong_prefix_fails(self, registry):
        passed, _ = registry.run(self._inv("OC4="))  # base64("8.")
        assert not passed


# ---------------------------------------------------------------------------
# Pattern: roundtrip
# ---------------------------------------------------------------------------

class TestPatternRoundtrip:
    def _inv(self, inputs):
        return {
            "id": "test.roundtrip",
            "description": "",
            "category": "roundtrip",
            "kind": "roundtrip",
            "spec": {"inputs": inputs},
        }

    def test_empty_roundtrip(self, registry):
        passed, msg = registry.run(self._inv([{"label": "empty", "data_b64": ""}]))
        assert passed, msg

    def test_hello_world_roundtrip(self, registry):
        passed, msg = registry.run(
            self._inv([{"label": "hw", "data_b64": "SGVsbG8gV29ybGQ="}])
        )
        assert passed, msg

    def test_repeated_bytes_roundtrip(self, registry):
        passed, msg = registry.run(
            self._inv([{"label": "rpt", "data_b64": "QQ==", "repeat": 1000}])
        )
        assert passed, msg

    def test_multiple_inputs_all_pass(self, registry):
        passed, msg = registry.run(self._inv([
            {"label": "empty", "data_b64": ""},
            {"label": "short", "data_b64": "SGVsbG8="},
            {"label": "repeated", "data_b64": "QQ==", "repeat": 500},
        ]))
        assert passed, msg


# ---------------------------------------------------------------------------
# Pattern: wire_bytes
# ---------------------------------------------------------------------------

class TestPatternWireBytes:
    def _inv(self, assertions):
        return {
            "id": "test.wire",
            "description": "",
            "category": "wire_format",
            "kind": "wire_bytes",
            "spec": {
                "produce_via": "compress2",
                "produce_args": {"data_b64": "SGVsbG8gV29ybGQ=", "level": 6},
                "assertions": assertions,
            },
        }

    def test_rfc1950_header_checksum(self, registry):
        passed, msg = registry.run(self._inv([{
            "description": "header check",
            "offset": 0,
            "length": 2,
            "python_check": "(data[0] * 256 + data[1]) % 31 == 0",
        }]))
        assert passed, msg

    def test_rfc1950_cm_field_is_8(self, registry):
        passed, msg = registry.run(self._inv([{
            "description": "CM == 8",
            "offset": 0,
            "length": 1,
            "python_check": "(data[0] & 0x0f) == 8",
        }]))
        assert passed, msg

    def test_rfc1950_adler32_trailer(self, registry):
        passed, msg = registry.run(self._inv([{
            "description": "Adler-32 trailer",
            "offset": -4,
            "length": 4,
            "python_check": "struct.unpack('>I', data)[0] == adler32_of_input",
        }]))
        assert passed, msg

    def test_failing_assertion_reported(self, registry):
        passed, msg = registry.run(self._inv([{
            "description": "deliberately false",
            "offset": 0,
            "length": 1,
            "python_check": "data[0] == 0xff",  # first byte of zlib stream is never 0xff
        }]))
        assert not passed

    def test_bad_check_expression_caught(self, registry):
        passed, msg = registry.run(self._inv([{
            "description": "syntax error in check",
            "offset": 0,
            "length": 1,
            "python_check": "this is not valid python !!!",
        }]))
        assert not passed
        assert "failed to evaluate" in msg


# ---------------------------------------------------------------------------
# Pattern: error_on_bad_input
# ---------------------------------------------------------------------------

class TestPatternErrorOnBadInput:
    def _inv(self, bad_b64, expected_return):
        return {
            "id": "test.bad_input",
            "description": "",
            "category": "error_handling",
            "kind": "error_on_bad_input",
            "spec": {
                "function": "uncompress",
                "bad_input_b64": bad_b64,
                "expected_return": expected_return,
            },
        }

    def test_junk_input_data_error(self, registry):
        # "not valid zlib data" in base64
        passed, msg = registry.run(
            self._inv("bm90IHZhbGlkIHpsaWIgZGF0YQ==", "Z_DATA_ERROR")
        )
        assert passed, msg

    def test_wrong_expected_code_fails(self, registry):
        passed, _ = registry.run(
            self._inv("bm90IHZhbGlkIHpsaWIgZGF0YQ==", "Z_OK")
        )
        assert not passed


# ---------------------------------------------------------------------------
# Pattern: incremental_eq_oneshot
# ---------------------------------------------------------------------------

class TestPatternIncrementalEqOneshot:
    def _inv(self, fn, init, chunks, full_b64):
        return {
            "id": "test.incremental",
            "description": "",
            "category": "checksum",
            "kind": "incremental_eq_oneshot",
            "spec": {
                "function": fn,
                "init_value": init,
                "chunks": chunks,
                "full_data_b64": full_b64,
            },
        }

    def test_crc32_incremental(self, registry):
        # "Hel" + "lo" == "Hello"
        passed, msg = registry.run(
            self._inv("crc32", 0, ["SGVs", "bG8="], "SGVsbG8=")
        )
        assert passed, msg

    def test_adler32_incremental(self, registry):
        passed, msg = registry.run(
            self._inv("adler32", 1, ["SGVs", "bG8="], "SGVsbG8=")
        )
        assert passed, msg

    def test_single_chunk(self, registry):
        passed, msg = registry.run(
            self._inv("crc32", 0, ["SGVsbG8="], "SGVsbG8=")
        )
        assert passed, msg


# ---------------------------------------------------------------------------
# Pattern: call_ge (compressBound)
# ---------------------------------------------------------------------------

class TestPatternCallGe:
    def _inv(self, src_b64, repeat, level):
        return {
            "id": "test.call_ge",
            "description": "",
            "category": "compress",
            "kind": "call_ge",
            "spec": {
                "function": "compressBound",
                "src_b64": src_b64,
                "src_repeat": repeat,
                "compare_level": level,
            },
        }

    def test_bound_sufficient_for_best_compression(self, registry):
        passed, msg = registry.run(self._inv("QQ==", 10000, 9))
        assert passed, msg

    def test_bound_sufficient_for_no_compression(self, registry):
        passed, msg = registry.run(self._inv("QQ==", 1000, 0))
        assert passed, msg

    def test_bound_sufficient_for_short_input(self, registry):
        passed, msg = registry.run(self._inv("SGVsbG8gV29ybGQ=", 1, -1))
        assert passed, msg


# ---------------------------------------------------------------------------
# InvariantRunner: integration against real zlib spec
# ---------------------------------------------------------------------------

class TestInvariantRunner:
    def test_all_invariants_pass(self, zlib_spec, zlib_lib):
        results = vb.InvariantRunner().run_all(zlib_spec, zlib_lib)
        failures = [r for r in results if not r.passed and not r.skip_reason]
        assert failures == [], \
            "Failing invariants:\n" + "\n".join(f"  {r.inv_id}: {r.message}" for r in failures)

    def test_filter_by_category_reduces_count(self, zlib_spec, zlib_lib):
        all_results = vb.InvariantRunner().run_all(zlib_spec, zlib_lib)
        checksum_results = vb.InvariantRunner().run_all(
            zlib_spec, zlib_lib, filter_category="checksum"
        )
        assert len(checksum_results) < len(all_results)
        assert all(r.inv_id.startswith("zlib.crc32") or r.inv_id.startswith("zlib.adler32")
                   for r in checksum_results)

    def test_skip_if_true_is_skipped(self, zlib_spec, zlib_lib):
        spec_copy = dict(zlib_spec)
        spec_copy["invariants"] = [
            dict(zlib_spec["invariants"][0], skip_if="True")
        ]
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib)
        assert results[0].skip_reason is not None

    def test_skip_if_lib_version_comparison(self, zlib_spec, zlib_lib):
        # skip_if using lib_version string comparison — real zlib is >=1.0
        spec_copy = dict(zlib_spec, invariants=[
            dict(zlib_spec["invariants"][0], skip_if='lib_version >= "1.0"')
        ])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib, lib_version="1.2.12")
        assert results[0].skip_reason is not None

    def test_skip_if_platform_variable(self, zlib_spec, zlib_lib):
        import sys
        expected_platform = sys.platform
        if expected_platform.startswith("linux"):
            expected_platform = "linux"
        spec_copy = dict(zlib_spec, invariants=[
            dict(zlib_spec["invariants"][0], skip_if=f'platform == "{expected_platform}"')
        ])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib, lib_version="1.2.12")
        assert results[0].skip_reason is not None  # should be skipped on this platform

    def test_skip_if_platform_other_does_not_skip(self, zlib_spec, zlib_lib):
        spec_copy = dict(zlib_spec, invariants=[
            dict(zlib_spec["invariants"][0], skip_if='platform == "nonexistent_os"')
        ])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib, lib_version="1.2.12")
        assert results[0].skip_reason is None  # not skipped — platform doesn't match

    def test_skip_if_semver_satisfies_true(self, zlib_spec, zlib_lib):
        spec_copy = dict(zlib_spec, invariants=[
            dict(zlib_spec["invariants"][0], skip_if='semver_satisfies(lib_version, ">=1.2")')
        ])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib, lib_version="1.2.12")
        assert results[0].skip_reason is not None  # 1.2.12 satisfies >=1.2

    def test_skip_if_semver_satisfies_false(self, zlib_spec, zlib_lib):
        spec_copy = dict(zlib_spec, invariants=[
            dict(zlib_spec["invariants"][0], skip_if='semver_satisfies(lib_version, ">=9.0")')
        ])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib, lib_version="1.2.12")
        assert results[0].skip_reason is None  # 1.2.12 does not satisfy >=9.0

    def test_result_count_with_skip(self, zlib_spec, zlib_lib):
        # skipped invariants still appear in results list
        spec_copy = dict(zlib_spec, invariants=[
            dict(zlib_spec["invariants"][0], skip_if="True"),
            zlib_spec["invariants"][1],
        ])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib, lib_version="1.2.12")
        assert len(results) == 2
        assert results[0].skip_reason is not None
        assert results[1].skip_reason is None

    def test_harness_error_produces_failed_result(self, zlib_spec, zlib_lib):
        bad_inv = {
            "id": "test.bad",
            "description": "",
            "category": "constant",
            "kind": "constant_eq",
            # Missing required "spec" key — will trigger KeyError in handler
        }
        spec_copy = dict(zlib_spec, invariants=[bad_inv])
        results = vb.InvariantRunner().run_all(spec_copy, zlib_lib)
        assert not results[0].passed
        assert "HARNESS ERROR" in results[0].message

    def test_result_count_matches_invariant_count(self, zlib_spec, zlib_lib):
        results = vb.InvariantRunner().run_all(zlib_spec, zlib_lib)
        assert len(results) == len(zlib_spec["invariants"])


# ---------------------------------------------------------------------------
# skip_if expression language
# ---------------------------------------------------------------------------

class TestSkipIfContext:
    def test_semver_satisfies_ge(self):
        assert vb._semver_satisfies("1.2.12", ">=1.2") is True

    def test_semver_satisfies_lt(self):
        assert vb._semver_satisfies("1.1.0", ">=1.2") is False

    def test_semver_satisfies_range(self):
        assert vb._semver_satisfies("1.5.0", ">=1.2 <2.0") is True
        assert vb._semver_satisfies("2.0.0", ">=1.2 <2.0") is False

    def test_semver_satisfies_empty_version(self):
        assert vb._semver_satisfies("", ">=1.2") is False

    def test_semver_satisfies_empty_constraint(self):
        assert vb._semver_satisfies("1.2.0", "") is False

    def test_semver_satisfies_unparseable(self):
        # Unparseable version string — should not raise, return False
        assert vb._semver_satisfies("not-a-version", ">=1.0") is False

    def test_build_skip_context_keys(self):
        ctx = vb._build_skip_context("1.2.12")
        assert ctx["lib_version"] == "1.2.12"
        assert "platform" in ctx
        assert callable(ctx["semver_satisfies"])

    def test_build_skip_context_platform_normalized(self):
        import sys
        ctx = vb._build_skip_context("1.0")
        if sys.platform.startswith("linux"):
            assert ctx["platform"] == "linux"
        else:
            assert ctx["platform"] == sys.platform

    def test_build_skip_context_semver_callable(self):
        ctx = vb._build_skip_context("2.5.0")
        assert ctx["semver_satisfies"]("2.5.0", ">=2.0") is True
        assert ctx["semver_satisfies"]("2.5.0", ">=3.0") is False


# ---------------------------------------------------------------------------
# CLI / main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_exit_0_on_all_pass(self):
        ret = vb.main([str(ZSPEC_PATH)])
        assert ret == 0

    def test_list_flag_exits_0(self):
        ret = vb.main([str(ZSPEC_PATH), "--list"])
        assert ret == 0

    def test_filter_flag_runs_subset(self, capsys):
        ret = vb.main([str(ZSPEC_PATH), "--filter", "checksum", "--verbose"])
        out = capsys.readouterr().out
        assert ret == 0
        assert "invariants:" in out

    def test_nonexistent_spec_exits_2(self, tmp_path):
        ret = vb.main([str(tmp_path / "nope.zspec.json")])
        assert ret == 2

    def test_exit_1_on_failure(self, tmp_path, zlib_spec):
        bad_inv = dict(zlib_spec["invariants"][0])
        bad_inv = dict(bad_inv, spec={"name": "Z_OK", "expected_value": 999})
        spec_copy = dict(zlib_spec, invariants=[bad_inv])
        spec_file = tmp_path / "bad.zspec.json"
        spec_file.write_text(json.dumps(spec_copy), encoding="utf-8")
        ret = vb.main([str(spec_file)])
        assert ret == 1

    def test_json_out_written(self, tmp_path):
        out_file = tmp_path / "results.json"
        ret = vb.main([str(ZSPEC_PATH), "--json-out", str(out_file)])
        assert ret == 0
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert all("id" in r and "passed" in r for r in data)
