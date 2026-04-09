"""
Tests for the zstd Z-layer spec (zspecs/zstd.zspec.json).

Covers:
  - Library loading via ctypes backend
  - call_ge in simple (expected_min) mode
  - call_eq for ZSTD_maxCLevel, ZSTD_isError
  - version_prefix for ZSTD_versionString
  - Full spec integration (all 15 invariants pass)
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ZSTD_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "zstd.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def zstd_spec():
    return vb.SpecLoader().load(ZSTD_SPEC_PATH)


@pytest.fixture(scope="module")
def zstd_lib(zstd_spec):
    return vb.LibraryLoader().load(zstd_spec["library"])


@pytest.fixture(scope="module")
def registry(zstd_lib):
    return vb.PatternRegistry(zstd_lib, {})


def inv(spec, inv_id):
    for i in spec["invariants"]:
        if i["id"] == inv_id:
            return i
    raise KeyError(inv_id)


# ---------------------------------------------------------------------------
# Library loading
# ---------------------------------------------------------------------------

class TestZstdLoading:
    def test_spec_loads(self, zstd_spec):
        assert zstd_spec["identity"]["canonical_name"] == "zstd"

    def test_invariant_count(self, zstd_spec):
        assert len(zstd_spec["invariants"]) == 25

    def test_no_duplicate_ids(self, zstd_spec):
        ids = [i["id"] for i in zstd_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_lib_loads(self, zstd_lib):
        # Should have ZSTD_versionString callable
        import ctypes
        assert isinstance(zstd_lib, ctypes.CDLL)

    def test_all_kinds_known(self, zstd_spec):
        for i in zstd_spec["invariants"]:
            assert i["kind"] in vb.KNOWN_KINDS, f"Unknown kind {i['kind']!r}"


# ---------------------------------------------------------------------------
# version_prefix
# ---------------------------------------------------------------------------

class TestZstdVersionPrefix:
    def test_version_starts_with_1(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.version.prefix"))
        assert ok, msg


# ---------------------------------------------------------------------------
# call_eq — maxCLevel and isError
# ---------------------------------------------------------------------------

class TestZstdCallEq:
    def test_max_clevel_eq_22(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.maxCLevel.eq_22"))
        assert ok, msg

    def test_is_error_zero_not_error(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.isError.zero_not_error"))
        assert ok, msg

    def test_is_error_small_value_not_error(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.isError.small_values_not_error"))
        assert ok, msg

    def test_is_error_near_size_max(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.isError.near_size_max"))
        assert ok, msg

    def test_compress_bound_known_value(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.known_value"))
        assert ok, msg

    def test_compress_bound_not_error(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.not_error"))
        assert ok, msg

    def test_max_clevel_is_not_error(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.maxCLevel.is_not_error"))
        assert ok, msg

    def test_version_number_not_error(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.versionNumber.not_error"))
        assert ok, msg


# ---------------------------------------------------------------------------
# call_ge — compressBound and versionNumber monotonicity
# ---------------------------------------------------------------------------

class TestZstdCallGe:
    def test_compress_bound_nonzero_input(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.nonzero_input"))
        assert ok, msg

    def test_compress_bound_zero_input(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.zero_input"))
        assert ok, msg

    def test_compress_bound_large_input(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.large_input"))
        assert ok, msg

    def test_compress_bound_256bytes(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.256bytes"))
        assert ok, msg

    def test_compress_bound_monotone(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.compressBound.monotone"))
        assert ok, msg

    def test_version_number_range(self, registry, zstd_spec):
        ok, msg = registry.run(inv(zstd_spec, "zstd.versionNumber.range"))
        assert ok, msg


# ---------------------------------------------------------------------------
# Full spec integration
# ---------------------------------------------------------------------------

class TestZstdFullSpec:
    def test_all_pass(self, registry, zstd_spec):
        failures = []
        for i in zstd_spec["invariants"]:
            ok, msg = registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_invariant_count(self, registry, zstd_spec):
        runner = vb.InvariantRunner()
        results = runner.run_all(zstd_spec, zstd_lib := vb.LibraryLoader().load(zstd_spec["library"]))
        assert len(results) == 25

    def test_cli_exit_0(self):
        rc = vb.main([str(ZSTD_SPEC_PATH)])
        assert rc == 0

    def test_cli_verbose(self, capsys):
        vb.main([str(ZSTD_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "25 invariants" in out
