"""
Tests for the lxml.etree behavioral spec (python_module backend).

Organized as:
  - TestLxmlSpecLoader: spec loading and structural checks
  - TestLxmlVersion: version category invariants (3)
  - TestLxmlParse: parse category invariants (8)
  - TestLxmlTostring: tostring category invariants (3)
  - TestLxmlElement: element category invariants (5)
  - TestLxmlXpath: xpath category invariants (3)
  - TestLxmlErrors: errors category invariants (3)
  - TestLxmlAll: integration — all 25 invariants pass, per-category filters
  - TestLxmlCLI: CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

LXML_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "lxml.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lxml_spec():
    return vb.SpecLoader().load(LXML_SPEC_PATH)


@pytest.fixture(scope="module")
def lxml_mod(lxml_spec):
    return vb.LibraryLoader().load(lxml_spec["library"])


@pytest.fixture(scope="module")
def constants_map(lxml_spec):
    return vb.InvariantRunner().build_constants_map(lxml_spec["constants"])


@pytest.fixture(scope="module")
def registry(lxml_mod, constants_map):
    return vb.PatternRegistry(lxml_mod, constants_map)


# ---------------------------------------------------------------------------
# TestLxmlSpecLoader
# ---------------------------------------------------------------------------

class TestLxmlSpecLoader:
    def test_loads_lxml_spec(self, lxml_spec):
        assert isinstance(lxml_spec, dict)

    def test_all_required_sections_present(self, lxml_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in lxml_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, lxml_spec):
        assert lxml_spec["library"]["backend"] == "python_module"

    def test_module_name_is_lxml_etree(self, lxml_spec):
        assert lxml_spec["library"]["module_name"] == "lxml.etree"

    def test_loads_lxml_module(self, lxml_mod):
        from lxml import etree
        assert lxml_mod is etree

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz_lxml",
            })

    def test_all_invariant_kinds_known(self, lxml_spec):
        for inv in lxml_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, lxml_spec):
        ids = [inv["id"] for inv in lxml_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestLxmlVersion
# ---------------------------------------------------------------------------

class TestLxmlVersion:
    def test_version_contains_dot(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["."],
                "expected": True,
            },
        })
        assert ok, msg

    def test_libxml_version_len_is_3(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "LIBXML_VERSION.__len__",
                "args": [],
                "expected": 3,
            },
        })
        assert ok, msg

    def test_libxml_major_ge_2(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "LIBXML_VERSION.__getitem__",
                "args": [0],
                "method": "__ge__",
                "method_args": [2],
                "expected": True,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestLxmlParse
# ---------------------------------------------------------------------------

class TestLxmlParse:
    def test_fromstring_root_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<root/>"],
                "method": "tag",
                "expected": "root",
            },
        })
        assert ok, msg

    def test_fromstring_child_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<child/>"],
                "method": "tag",
                "expected": "child",
            },
        })
        assert ok, msg

    def test_fromstring_text(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<el>text</el>"],
                "method": "text",
                "expected": "text",
            },
        })
        assert ok, msg

    def test_fromstring_text_upper(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<el>hello</el>"],
                "method": "text",
                "method_chain": "upper",
                "expected": "HELLO",
            },
        })
        assert ok, msg

    def test_fromstring_get_attribute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ['<el id="42"/>'],
                "method": "get",
                "method_args": ["id"],
                "expected": "42",
            },
        })
        assert ok, msg

    def test_fromstring_child_count(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<r><a/><b/></r>"],
                "method": "__len__",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_fromstring_namespace_clark(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ['<ns:root xmlns:ns="http://example.com"/>'],
                "method": "tag",
                "expected": "{http://example.com}root",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_expected_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<root/>"],
                "method": "tag",
                "expected": "wrong_tag",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestLxmlTostring
# ---------------------------------------------------------------------------

class TestLxmlTostring:
    def test_roundtrip_root(self, registry):
        import base64
        ok, msg = registry.run({
            "kind": "python_encode_decode_roundtrip",
            "spec": {
                "encode_fn": "fromstring",
                "decode_fn": "tostring",
                "inputs_b64": [
                    base64.b64encode(b"<root/>").decode(),
                    base64.b64encode(b"<foo/>").decode(),
                ],
            },
        })
        assert ok, msg

    def test_element_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Element",
                "args": ["foo"],
                "method": "tag",
                "expected": "foo",
            },
        })
        assert ok, msg

    def test_element_no_children(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Element",
                "args": ["bar"],
                "method": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestLxmlElement
# ---------------------------------------------------------------------------

class TestLxmlElement:
    def test_element_alpha_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Element",
                "args": ["alpha"],
                "method": "tag",
                "expected": "alpha",
            },
        })
        assert ok, msg

    def test_element_beta_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Element",
                "args": ["beta"],
                "method": "tag",
                "expected": "beta",
            },
        })
        assert ok, msg

    def test_element_gamma_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Element",
                "args": ["gamma"],
                "method": "tag",
                "expected": "gamma",
            },
        })
        assert ok, msg

    def test_child_count_two(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<r><a/><b/></r>"],
                "method": "__len__",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_child_count_one(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<r><a/></r>"],
                "method": "__len__",
                "expected": 1,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestLxmlXpath
# ---------------------------------------------------------------------------

class TestLxmlXpath:
    def test_attribute_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ['<r><c id="1"/></r>'],
                "method": "xpath",
                "method_args": ["c/@id"],
                "expected": ["1"],
            },
        })
        assert ok, msg

    def test_count_returns_float(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<r><a/><b/></r>"],
                "method": "xpath",
                "method_args": ["count(*)"],
                "expected": 2.0,
            },
        })
        assert ok, msg

    def test_no_match_empty_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<r/>"],
                "method": "xpath",
                "method_args": ["child/@id"],
                "expected": [],
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestLxmlErrors
# ---------------------------------------------------------------------------

class TestLxmlErrors:
    def test_unclosed_tag_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "fromstring",
                "args": ["<unclosed"],
                "expected_exception": "lxml.etree.XMLSyntaxError",
            },
        })
        assert ok, msg

    def test_mismatched_tags_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "fromstring",
                "args": ["<a></b>"],
                "expected_exception": "lxml.etree.XMLSyntaxError",
            },
        })
        assert ok, msg

    def test_empty_string_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "fromstring",
                "args": [""],
                "expected_exception": "lxml.etree.XMLSyntaxError",
            },
        })
        assert ok, msg

    def test_valid_xml_does_not_raise(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "fromstring",
                "args": ["<valid/>"],
                "method": "tag",
                "expected": "valid",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestLxmlAll — integration: all 25 invariants pass
# ---------------------------------------------------------------------------

class TestLxmlAll:
    def test_all_pass(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod)
        assert len(results) == 25

    def test_no_skips(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod, filter_category="version")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_parse(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod, filter_category="parse")
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_filter_by_tostring(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod, filter_category="tostring")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_element(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod, filter_category="element")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_xpath(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod, filter_category="xpath")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_errors(self, lxml_spec, lxml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(lxml_spec, lxml_mod, filter_category="errors")
        assert len(results) == 3
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestLxmlCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestLxmlCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(LXML_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(LXML_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "25 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(LXML_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "lxml.version.contains_dot" in out
        assert "lxml.errors.unclosed_tag" in out

    def test_filter_flag_parse(self, capsys):
        vb.main([str(LXML_SPEC_PATH), "--filter", "parse", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(LXML_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 25
        assert all(r["passed"] for r in data)
