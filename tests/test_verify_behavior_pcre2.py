"""
Tests for the pcre2 Z-layer spec (zspecs/pcre2.zspec.json).

Covers:
  - Library loading via ctypes backend (libpcre2-8)
  - constant_eq for PCRE2_ERROR_NOMATCH and PCRE2_ERROR_BADOPTION
  - call_ge for pcre2_config_8 version and unicode version string sizes
  - call_eq for pcre2_config_8 integer config size and unknown config error
  - call_eq for pcre2_get_error_message_8 error message length
  - pcre2_match for compile+match, no-match, anchoring, capture groups, digit class, alternation
  - Full spec integration (all 16 invariants pass)
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PCRE2_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pcre2.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Skip entire module if libpcre2-8 is not available
# ---------------------------------------------------------------------------

def _pcre2_available() -> bool:
    try:
        import ctypes.util
        return ctypes.util.find_library("pcre2-8") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pcre2_available(),
    reason="libpcre2-8 not found on this system",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pcre2_spec():
    return vb.SpecLoader().load(PCRE2_SPEC_PATH)


@pytest.fixture(scope="module")
def pcre2_lib(pcre2_spec):
    return vb.LibraryLoader().load(pcre2_spec["library"])


@pytest.fixture(scope="module")
def registry(pcre2_lib, pcre2_spec):
    runner = vb.InvariantRunner()
    constants_map = runner.build_constants_map(pcre2_spec.get("constants", {}))
    return vb.PatternRegistry(pcre2_lib, constants_map)


def inv(spec, inv_id):
    for i in spec["invariants"]:
        if i["id"] == inv_id:
            return i
    raise KeyError(inv_id)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestPCRE2Loading:
    def test_spec_loads(self, pcre2_spec):
        assert pcre2_spec["identity"]["canonical_name"] == "pcre2"

    def test_invariant_count(self, pcre2_spec):
        assert len(pcre2_spec["invariants"]) == 16

    def test_no_duplicate_ids(self, pcre2_spec):
        ids = [i["id"] for i in pcre2_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_lib_loads(self, pcre2_lib):
        import ctypes
        assert isinstance(pcre2_lib, ctypes.CDLL)

    def test_all_kinds_known(self, pcre2_spec):
        for i in pcre2_spec["invariants"]:
            assert i["kind"] in vb.KNOWN_KINDS, f"Unknown kind {i['kind']!r}"


# ---------------------------------------------------------------------------
# constant (category: constant)
# ---------------------------------------------------------------------------

class TestPCRE2Constants:
    def test_error_nomatch(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.const.PCRE2_ERROR_NOMATCH"))
        assert ok, msg

    def test_error_badoption(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.const.PCRE2_ERROR_BADOPTION"))
        assert ok, msg


# ---------------------------------------------------------------------------
# version (category: version)
# ---------------------------------------------------------------------------

class TestPCRE2Version:
    def test_version_string_size(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.version.string_size_ge"))
        assert ok, msg

    def test_unicode_string_size(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.version.unicode_string_size_ge"))
        assert ok, msg


# ---------------------------------------------------------------------------
# config (category: config)
# ---------------------------------------------------------------------------

class TestPCRE2Config:
    def test_bsr_is_integer(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.config.bsr_is_integer"))
        assert ok, msg

    def test_jit_is_integer(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.config.jit_is_integer"))
        assert ok, msg

    def test_unicode_is_integer(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.config.unicode_is_integer"))
        assert ok, msg

    def test_unknown_returns_badoption(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.config.unknown_returns_badoption"))
        assert ok, msg


# ---------------------------------------------------------------------------
# error (category: error)
# ---------------------------------------------------------------------------

class TestPCRE2Error:
    def test_nomatch_message_size(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.error.nomatch_message_size"))
        assert ok, msg


# ---------------------------------------------------------------------------
# match (category: match)
# ---------------------------------------------------------------------------

class TestPCRE2Match:
    def test_simple_match(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.simple_match"))
        assert ok, msg

    def test_no_match(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.no_match"))
        assert ok, msg

    def test_anchor_match(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.anchor_match"))
        assert ok, msg

    def test_anchor_no_match(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.anchor_no_match"))
        assert ok, msg

    def test_capture_groups(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.capture_groups"))
        assert ok, msg

    def test_digit_pattern(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.digit_pattern"))
        assert ok, msg

    def test_alternation(self, registry, pcre2_spec):
        ok, msg = registry.run(inv(pcre2_spec, "pcre2.match.alternation"))
        assert ok, msg


# ---------------------------------------------------------------------------
# Full spec integration
# ---------------------------------------------------------------------------

class TestPCRE2All:
    def test_all_pass(self, registry, pcre2_spec):
        failures = []
        for i in pcre2_spec["invariants"]:
            ok, msg = registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_invariant_count(self, pcre2_spec):
        runner = vb.InvariantRunner()
        lib = vb.LibraryLoader().load(pcre2_spec["library"])
        results = runner.run_all(pcre2_spec, lib)
        assert len(results) == 16

    def test_cli_exit_0(self):
        rc = vb.main([str(PCRE2_SPEC_PATH)])
        assert rc == 0

    def test_cli_verbose(self, capsys):
        vb.main([str(PCRE2_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "16 invariants" in out
