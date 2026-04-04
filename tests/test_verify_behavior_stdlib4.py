"""
Tests for hashlib extensions (sha3_256, blake2b, blake2s),
urllib_parse, and difflib Z-layer specs.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT         = Path(__file__).resolve().parent.parent
HL_SPEC_PATH      = REPO_ROOT / "_build" / "zspecs" / "hashlib.zspec.json"
URL_SPEC_PATH     = REPO_ROOT / "_build" / "zspecs" / "urllib_parse.zspec.json"
DL_SPEC_PATH      = REPO_ROOT / "_build" / "zspecs" / "difflib.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def hl_spec():
    return vb.SpecLoader().load(HL_SPEC_PATH)

@pytest.fixture(scope="module")
def hl_lib(hl_spec):
    return vb.LibraryLoader().load(hl_spec["library"])

@pytest.fixture(scope="module")
def hl_registry(hl_lib):
    return vb.PatternRegistry(hl_lib, {})


@pytest.fixture(scope="module")
def url_spec():
    return vb.SpecLoader().load(URL_SPEC_PATH)

@pytest.fixture(scope="module")
def url_lib(url_spec):
    return vb.LibraryLoader().load(url_spec["library"])

@pytest.fixture(scope="module")
def url_registry(url_lib):
    return vb.PatternRegistry(url_lib, {})


@pytest.fixture(scope="module")
def dl_spec():
    return vb.SpecLoader().load(DL_SPEC_PATH)

@pytest.fixture(scope="module")
def dl_lib(dl_spec):
    return vb.LibraryLoader().load(dl_spec["library"])

@pytest.fixture(scope="module")
def dl_registry(dl_lib):
    return vb.PatternRegistry(dl_lib, {})


def inv(spec, inv_id):
    for i in spec["invariants"]:
        if i["id"] == inv_id:
            return i
    raise KeyError(inv_id)


# ---------------------------------------------------------------------------
# hashlib — sha3_256 extensions
# ---------------------------------------------------------------------------

class TestHashlibSha3_256:
    def test_empty_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_256.empty"))
        assert ok, msg

    def test_abc_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_256.abc"))
        assert ok, msg

    def test_fox_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_256.quick_brown_fox"))
        assert ok, msg

    def test_digest_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_256.digest_size"))
        assert ok, msg

    def test_block_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_256.block_size"))
        assert ok, msg

    def test_incremental(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_256.incremental"))
        assert ok, msg


# ---------------------------------------------------------------------------
# hashlib — sha3_512
# ---------------------------------------------------------------------------

class TestHashlibSha3_512:
    def test_abc_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_512.abc"))
        assert ok, msg

    def test_digest_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.sha3_512.digest_size"))
        assert ok, msg


# ---------------------------------------------------------------------------
# hashlib — blake2b
# ---------------------------------------------------------------------------

class TestHashlibBlake2b:
    def test_empty_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2b.empty"))
        assert ok, msg

    def test_abc_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2b.abc"))
        assert ok, msg

    def test_digest_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2b.digest_size"))
        assert ok, msg

    def test_block_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2b.block_size"))
        assert ok, msg

    def test_incremental(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2b.incremental"))
        assert ok, msg


# ---------------------------------------------------------------------------
# hashlib — blake2s
# ---------------------------------------------------------------------------

class TestHashlibBlake2s:
    def test_empty_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2s.empty"))
        assert ok, msg

    def test_abc_vector(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2s.abc"))
        assert ok, msg

    def test_digest_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2s.digest_size"))
        assert ok, msg

    def test_block_size(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.blake2s.block_size"))
        assert ok, msg


# ---------------------------------------------------------------------------
# hashlib — algorithms_guaranteed sha3/blake2 extension
# ---------------------------------------------------------------------------

class TestHashlibAlgorithmsGuaranteedExtended:
    def test_sha3_blake2_in_guaranteed(self, hl_registry, hl_spec):
        ok, msg = hl_registry.run(inv(hl_spec, "hashlib.algorithms_guaranteed.sha3"))
        assert ok, msg


# ---------------------------------------------------------------------------
# hashlib — full spec integration (all 41 invariants)
# ---------------------------------------------------------------------------

class TestHashlibFullSpec:
    def test_all_pass(self, hl_registry, hl_spec):
        failures = []
        for i in hl_spec["invariants"]:
            ok, msg = hl_registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_total_invariant_count(self, hl_spec):
        assert len(hl_spec["invariants"]) == 41

    def test_no_duplicate_ids(self, hl_spec):
        ids = [i["id"] for i in hl_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# urllib_parse — spec loading
# ---------------------------------------------------------------------------

class TestUrllibParseLoading:
    def test_loads(self, url_spec):
        assert url_spec["identity"]["canonical_name"] == "urllib_parse"

    def test_invariant_count(self, url_spec):
        assert len(url_spec["invariants"]) == 18

    def test_lib_loads(self, url_lib):
        import urllib.parse
        assert url_lib is urllib.parse


# ---------------------------------------------------------------------------
# urllib_parse — urlparse
# ---------------------------------------------------------------------------

class TestUrllibParseUrlparse:
    def test_scheme(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.scheme"))
        assert ok, msg

    def test_netloc(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.netloc"))
        assert ok, msg

    def test_path(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.path"))
        assert ok, msg

    def test_query(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.query"))
        assert ok, msg

    def test_fragment(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.fragment"))
        assert ok, msg

    def test_port_is_int(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.port"))
        assert ok, msg

    def test_userinfo(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlparse.userinfo"))
        assert ok, msg


# ---------------------------------------------------------------------------
# urllib_parse — quoting
# ---------------------------------------------------------------------------

class TestUrllibParseQuoting:
    def test_quote_spaces(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.quote.spaces"))
        assert ok, msg

    def test_quote_empty_safe(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.quote.empty_safe"))
        assert ok, msg

    def test_quote_plus(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.quote_plus.spaces"))
        assert ok, msg

    def test_unquote(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.unquote.percent_encoded"))
        assert ok, msg

    def test_unquote_plus(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.unquote_plus.plus_to_space"))
        assert ok, msg

    def test_roundtrip(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.quote_unquote_roundtrip"))
        assert ok, msg


# ---------------------------------------------------------------------------
# urllib_parse — joining and encoding
# ---------------------------------------------------------------------------

class TestUrllibParseJoining:
    def test_urljoin_relative(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urljoin.relative"))
        assert ok, msg

    def test_urljoin_absolute_overrides(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urljoin.absolute_overrides"))
        assert ok, msg

    def test_urlencode(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.urlencode.simple"))
        assert ok, msg

    def test_parse_qs_multi_value(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.parse_qs.multi_value"))
        assert ok, msg

    def test_parse_qs_single(self, url_registry, url_spec):
        ok, msg = url_registry.run(inv(url_spec, "urllib_parse.parse_qs.single_value"))
        assert ok, msg


# ---------------------------------------------------------------------------
# urllib_parse — full spec integration
# ---------------------------------------------------------------------------

class TestUrllibParseFullSpec:
    def test_all_pass(self, url_registry, url_spec):
        failures = []
        for i in url_spec["invariants"]:
            ok, msg = url_registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_no_duplicate_ids(self, url_spec):
        ids = [i["id"] for i in url_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# difflib — spec loading
# ---------------------------------------------------------------------------

class TestDifflibLoading:
    def test_loads(self, dl_spec):
        assert dl_spec["identity"]["canonical_name"] == "difflib"

    def test_invariant_count(self, dl_spec):
        assert len(dl_spec["invariants"]) == 17

    def test_lib_loads(self, dl_lib):
        import difflib
        assert dl_lib is difflib


# ---------------------------------------------------------------------------
# difflib — SequenceMatcher ratio
# ---------------------------------------------------------------------------

class TestDifflibRatio:
    def test_ratio_identical(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.ratio_identical"))
        assert ok, msg

    def test_ratio_disjoint(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.ratio_disjoint"))
        assert ok, msg

    def test_ratio_empty(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.ratio_empty"))
        assert ok, msg

    def test_quick_ratio_identical(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.quick_ratio_identical"))
        assert ok, msg

    def test_real_quick_ratio_identical(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.real_quick_ratio_identical"))
        assert ok, msg


# ---------------------------------------------------------------------------
# difflib — find_longest_match
# ---------------------------------------------------------------------------

class TestDifflibFindLongestMatch:
    def test_size(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.find_longest_match_size"))
        assert ok, msg

    def test_b_index(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.sequence_matcher.find_longest_match_b_index"))
        assert ok, msg


# ---------------------------------------------------------------------------
# difflib — get_close_matches
# ---------------------------------------------------------------------------

class TestDifflibCloseMatches:
    def test_match_found(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.get_close_matches.match_found"))
        assert ok, msg

    def test_no_match(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.get_close_matches.no_match"))
        assert ok, msg

    def test_n_limits(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.get_close_matches.n_limits_results"))
        assert ok, msg

    def test_exact_match(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.get_close_matches.exact_match"))
        assert ok, msg


# ---------------------------------------------------------------------------
# difflib — junk predicates
# ---------------------------------------------------------------------------

class TestDifflibJunk:
    def test_is_char_junk_space(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.is_character_junk.space"))
        assert ok, msg

    def test_is_char_junk_tab(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.is_character_junk.tab"))
        assert ok, msg

    def test_is_char_junk_letter(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.is_character_junk.letter"))
        assert ok, msg

    def test_is_line_junk_blank(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.is_line_junk.blank"))
        assert ok, msg

    def test_is_line_junk_hash_only(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.is_line_junk.hash_only"))
        assert ok, msg

    def test_is_line_junk_code(self, dl_registry, dl_spec):
        ok, msg = dl_registry.run(inv(dl_spec, "difflib.is_line_junk.code_line"))
        assert ok, msg


# ---------------------------------------------------------------------------
# difflib — full spec integration
# ---------------------------------------------------------------------------

class TestDifflibFullSpec:
    def test_all_pass(self, dl_registry, dl_spec):
        failures = []
        for i in dl_spec["invariants"]:
            ok, msg = dl_registry.run(i)
            if not ok:
                failures.append(f"{i['id']}: {msg}")
        assert not failures, "\n".join(failures)

    def test_no_duplicate_ids(self, dl_spec):
        ids = [i["id"] for i in dl_spec["invariants"]]
        assert len(ids) == len(set(ids))
