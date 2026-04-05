"""
Integration tests for the idna Z-layer behavioral spec.

Covers:
  - version  (2 invariants) — __version__ is a string, contains a dot
  - encode   (4 invariants) — unicode domains → ACE bytes
  - decode   (3 invariants) — ACE bytes → unicode domains
  - core     (5 invariants) — alabel, ulabel, valid_label_length
  - error    (1 invariant)  — IDNAError on invalid input
  Total: 16 invariants
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDNA_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "idna.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def idna_spec():
    return vb.SpecLoader().load(IDNA_SPEC_PATH)

@pytest.fixture(scope="module")
def idna_lib(idna_spec):
    return vb.LibraryLoader().load(idna_spec["library"])

@pytest.fixture(scope="module")
def idna_registry(idna_lib):
    return vb.PatternRegistry(idna_lib, {})


def inv(spec, inv_id):
    for i in spec["invariants"]:
        if i["id"] == inv_id:
            return i
    raise KeyError(inv_id)


# ---------------------------------------------------------------------------
# Spec loading
# ---------------------------------------------------------------------------

class TestIdnaSpecLoading:
    def test_spec_loads(self, idna_spec):
        assert idna_spec["identity"]["canonical_name"] == "idna"

    def test_invariant_count(self, idna_spec):
        assert len(idna_spec["invariants"]) == 16

    def test_no_duplicate_ids(self, idna_spec):
        ids = [i["id"] for i in idna_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_lib_loads(self, idna_lib):
        import idna
        assert idna_lib is idna


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

class TestIdnaVersion:
    def test_version_is_string(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.version.is_string"))
        assert ok, msg

    def test_version_contains_dot(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.version.contains_dot"))
        assert ok, msg


# ---------------------------------------------------------------------------
# encode
# ---------------------------------------------------------------------------

class TestIdnaEncode:
    def test_ascii_passthrough(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.encode.ascii_passthrough"))
        assert ok, msg

    def test_umlaut_german(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.encode.umlaut_german"))
        assert ok, msg

    def test_cjk_japanese(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.encode.cjk_japanese"))
        assert ok, msg

    def test_ace_passthrough(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.encode.ace_passthrough"))
        assert ok, msg


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------

class TestIdnaDecode:
    def test_ascii_passthrough(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.decode.ascii_passthrough"))
        assert ok, msg

    def test_umlaut_german(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.decode.umlaut_german"))
        assert ok, msg

    def test_cjk_japanese(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.decode.cjk_japanese"))
        assert ok, msg


# ---------------------------------------------------------------------------
# core
# ---------------------------------------------------------------------------

class TestIdnaCore:
    def test_alabel_ascii_passthrough(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.core.alabel.ascii_passthrough"))
        assert ok, msg

    def test_alabel_unicode_to_ace(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.core.alabel.unicode_to_ace"))
        assert ok, msg

    def test_ulabel_ascii_passthrough(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.core.ulabel.ascii_passthrough"))
        assert ok, msg

    def test_ulabel_ace_to_unicode(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.core.ulabel.ace_to_unicode"))
        assert ok, msg

    def test_valid_label_length_short(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.core.valid_label_length.short_label"))
        assert ok, msg

    def test_valid_label_length_overlength(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.core.valid_label_length.overlength_label"))
        assert ok, msg


# ---------------------------------------------------------------------------
# error
# ---------------------------------------------------------------------------

class TestIdnaError:
    def test_trailing_hyphen_raises(self, idna_registry, idna_spec):
        ok, msg = idna_registry.run(inv(idna_spec, "idna.error.trailing_hyphen_in_ace_label"))
        assert ok, msg


# ---------------------------------------------------------------------------
# Full spec integration
# ---------------------------------------------------------------------------

class TestIdnaFullSpec:
    def test_all_pass(self, idna_registry, idna_spec):
        failures = []
        for i in idna_spec["invariants"]:
            ok, msg = idna_registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_total_invariant_count(self, idna_spec):
        assert len(idna_spec["invariants"]) == 16

    def test_no_duplicate_ids(self, idna_spec):
        ids = [i["id"] for i in idna_spec["invariants"]]
        assert len(ids) == len(set(ids))
