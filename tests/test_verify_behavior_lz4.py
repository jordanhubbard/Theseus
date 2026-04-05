"""
Tests for the lz4 Z-layer spec (zspecs/lz4.zspec.json).

Covers:
  - Library loading via ctypes backend
  - version_prefix for LZ4_versionString
  - call_ge for LZ4_versionNumber and LZ4_compressBound
  - call_eq for LZ4_compressBound edge cases and error path
  - lz4_roundtrip for compress/decompress cycle
  - Full spec integration (all 8 invariants pass)
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LZ4_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "lz4.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Skip entire module if lz4 is not available
# ---------------------------------------------------------------------------

def _lz4_available() -> bool:
    try:
        import ctypes.util
        return ctypes.util.find_library("lz4") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _lz4_available(),
    reason="liblz4 not found on this system",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lz4_spec():
    return vb.SpecLoader().load(LZ4_SPEC_PATH)


@pytest.fixture(scope="module")
def lz4_lib(lz4_spec):
    return vb.LibraryLoader().load(lz4_spec["library"])


@pytest.fixture(scope="module")
def registry(lz4_lib):
    return vb.PatternRegistry(lz4_lib, {})


def inv(spec, inv_id):
    for i in spec["invariants"]:
        if i["id"] == inv_id:
            return i
    raise KeyError(inv_id)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestLZ4Loading:
    def test_spec_loads(self, lz4_spec):
        assert lz4_spec["identity"]["canonical_name"] == "lz4"

    def test_invariant_count(self, lz4_spec):
        assert len(lz4_spec["invariants"]) == 8

    def test_no_duplicate_ids(self, lz4_spec):
        ids = [i["id"] for i in lz4_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_lib_loads(self, lz4_lib):
        import ctypes
        assert isinstance(lz4_lib, ctypes.CDLL)

    def test_all_kinds_known(self, lz4_spec):
        for i in lz4_spec["invariants"]:
            assert i["kind"] in vb.KNOWN_KINDS, f"Unknown kind {i['kind']!r}"


# ---------------------------------------------------------------------------
# version (category: version)
# ---------------------------------------------------------------------------

class TestLZ4Version:
    def test_version_prefix(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.version.prefix"))
        assert ok, msg

    def test_version_number_ge_10000(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.version.number_ge_10000"))
        assert ok, msg

    def test_version_number_ge_10900(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.version.number_ge_10900"))
        assert ok, msg


# ---------------------------------------------------------------------------
# compress_bound (category: compress_bound)
# ---------------------------------------------------------------------------

class TestLZ4CompressBound:
    def test_zero_input(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.compress_bound.zero_input"))
        assert ok, msg

    def test_ge_100(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.compress_bound.ge_100"))
        assert ok, msg

    def test_ge_1000(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.compress_bound.ge_1000"))
        assert ok, msg


# ---------------------------------------------------------------------------
# error (category: error)
# ---------------------------------------------------------------------------

class TestLZ4Error:
    def test_compress_bound_negative(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.error.compress_bound_negative"))
        assert ok, msg


# ---------------------------------------------------------------------------
# roundtrip (category: roundtrip)
# ---------------------------------------------------------------------------

class TestLZ4Roundtrip:
    def test_roundtrip_basic(self, registry, lz4_spec):
        ok, msg = registry.run(inv(lz4_spec, "lz4.roundtrip.basic"))
        assert ok, msg


# ---------------------------------------------------------------------------
# Full spec integration
# ---------------------------------------------------------------------------

class TestLZ4All:
    def test_all_pass(self, registry, lz4_spec):
        failures = []
        for i in lz4_spec["invariants"]:
            ok, msg = registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_invariant_count(self, lz4_spec):
        runner = vb.InvariantRunner()
        lib = vb.LibraryLoader().load(lz4_spec["library"])
        results = runner.run_all(lz4_spec, lib)
        assert len(results) == 8

    def test_cli_exit_0(self):
        rc = vb.main([str(LZ4_SPEC_PATH)])
        assert rc == 0

    def test_cli_verbose(self, capsys):
        vb.main([str(LZ4_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "8 invariants" in out
