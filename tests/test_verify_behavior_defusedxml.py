"""
Tests for the defusedxml behavioral spec (python_module backend).

Organized as:
  - TestDefusedxmlSpecLoader: spec loading and structural checks
  - TestDefusedxmlVersion: version category invariants (2)
  - TestDefusedxmlParse: parse category invariants (5)
  - TestDefusedxmlSecurity: security category invariants (3)
  - TestDefusedxmlExceptions: exceptions category invariants (4)
  - TestDefusedxmlAll: integration — all 14 invariants pass, per-category filters
  - TestDefusedxmlCLI: CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "defusedxml.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dx_spec():
    return vb.SpecLoader().load(SPEC_PATH)


@pytest.fixture(scope="module")
def dx_mod(dx_spec):
    return vb.LibraryLoader().load(dx_spec["library"])


@pytest.fixture(scope="module")
def constants_map(dx_spec):
    return vb.InvariantRunner().build_constants_map(dx_spec["constants"])


@pytest.fixture(scope="module")
def registry(dx_mod, constants_map):
    return vb.PatternRegistry(dx_mod, constants_map)


# ---------------------------------------------------------------------------
# TestDefusedxmlSpecLoader
# ---------------------------------------------------------------------------

class TestDefusedxmlSpecLoader:
    def test_loads_spec(self, dx_spec):
        assert isinstance(dx_spec, dict)

    def test_all_required_sections_present(self, dx_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in dx_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, dx_spec):
        assert dx_spec["library"]["backend"] == "python_module"

    def test_module_name_is_defusedxml(self, dx_spec):
        assert dx_spec["library"]["module_name"] == "defusedxml"

    def test_loads_defusedxml_module(self, dx_mod):
        import defusedxml
        assert dx_mod is defusedxml

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz_defusedxml",
            })

    def test_all_invariant_kinds_known(self, dx_spec):
        for inv in dx_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, dx_spec):
        ids = [inv["id"] for inv in dx_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestDefusedxmlVersion
# ---------------------------------------------------------------------------

class TestDefusedxmlVersion:
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

    def test_version_is_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__class__.__name__.__eq__",
                "args": ["str"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_direct_check(self, dx_mod):
        """Direct check: __version__ is a non-empty string containing a dot."""
        assert isinstance(dx_mod.__version__, str)
        assert "." in dx_mod.__version__


# ---------------------------------------------------------------------------
# TestDefusedxmlParse
# ---------------------------------------------------------------------------

class TestDefusedxmlParse:
    def test_fromstring_item_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": ["<item>hello</item>"],
                "method": "tag",
                "expected": "item",
            },
        })
        assert ok, msg

    def test_fromstring_item_text(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": ["<item>hello</item>"],
                "method": "text",
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_fromstring_root_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": ["<root><child/></root>"],
                "method": "tag",
                "expected": "root",
            },
        })
        assert ok, msg

    def test_fromstring_get_attribute(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": ['<el name="foo"/>'],
                "method": "get",
                "method_args": ["name"],
                "expected": "foo",
            },
        })
        assert ok, msg

    def test_fromstring_child_count(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": ["<root><a/><b/></root>"],
                "method": "__len__",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_fromstring_direct_check(self, dx_mod):
        """Direct check: ElementTree.fromstring parses XML and returns an Element."""
        et = dx_mod.ElementTree
        el = et.fromstring("<item>hello</item>")
        assert el.tag == "item"
        assert el.text == "hello"

    def test_wrong_tag_fails(self, registry):
        """Sanity check: expecting the wrong tag produces a failing result."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": ["<root/>"],
                "method": "tag",
                "expected": "wrong_tag",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestDefusedxmlSecurity
# ---------------------------------------------------------------------------

class TestDefusedxmlSecurity:
    def test_xxe_raises_entities_forbidden(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": [
                    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>'
                ],
                "expected_exception": "EntitiesForbidden",
            },
        })
        assert ok, msg

    def test_billion_laughs_raises_entities_forbidden(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": [
                    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]><root>&lol2;</root>'
                ],
                "expected_exception": "EntitiesForbidden",
            },
        })
        assert ok, msg

    def test_dtd_forbidden_with_flag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "ElementTree.fromstring",
                "args": [
                    '<?xml version="1.0"?><!DOCTYPE foo []><root>text</root>'
                ],
                "kwargs": {"forbid_dtd": True},
                "expected_exception": "DTDForbidden",
            },
        })
        assert ok, msg

    def test_xxe_direct_check(self, dx_mod):
        """Direct check: XXE attack raises EntitiesForbidden."""
        et = dx_mod.ElementTree
        xxe_xml = (
            '<?xml version="1.0"?><!DOCTYPE foo '
            '[<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            '<root>&xxe;</root>'
        )
        with pytest.raises(dx_mod.EntitiesForbidden):
            et.fromstring(xxe_xml)

    def test_valid_xml_not_blocked(self, dx_mod):
        """Direct check: valid XML without entities parses normally."""
        et = dx_mod.ElementTree
        el = et.fromstring("<safe>content</safe>")
        assert el.tag == "safe"
        assert el.text == "content"


# ---------------------------------------------------------------------------
# TestDefusedxmlExceptions
# ---------------------------------------------------------------------------

class TestDefusedxmlExceptions:
    def test_dtd_forbidden_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "DTDForbidden.__name__.__eq__",
                "args": ["DTDForbidden"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_entities_forbidden_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "EntitiesForbidden.__name__.__eq__",
                "args": ["EntitiesForbidden"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_external_reference_forbidden_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ExternalReferenceForbidden.__name__.__eq__",
                "args": ["ExternalReferenceForbidden"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_defused_xml_exception_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "DefusedXmlException.__name__.__eq__",
                "args": ["DefusedXmlException"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_exception_hierarchy(self, dx_mod):
        """Direct check: all security exceptions are subclasses of DefusedXmlException."""
        assert issubclass(dx_mod.DTDForbidden, dx_mod.DefusedXmlException)
        assert issubclass(dx_mod.EntitiesForbidden, dx_mod.DefusedXmlException)
        assert issubclass(dx_mod.ExternalReferenceForbidden, dx_mod.DefusedXmlException)

    def test_defused_xml_exception_is_value_error(self, dx_mod):
        """Direct check: DefusedXmlException inherits from ValueError."""
        assert issubclass(dx_mod.DefusedXmlException, ValueError)


# ---------------------------------------------------------------------------
# TestDefusedxmlAll — integration: all 14 invariants pass
# ---------------------------------------------------------------------------

class TestDefusedxmlAll:
    def test_all_pass(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod)
        assert len(results) == 14

    def test_no_skips(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_parse(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod, filter_category="parse")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_security(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod, filter_category="security")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_exceptions(self, dx_spec, dx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(dx_spec, dx_mod, filter_category="exceptions")
        assert len(results) == 4
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestDefusedxmlCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestDefusedxmlCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "14 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "defusedxml.version.contains_dot" in out
        assert "defusedxml.security.xxe_raises_entities_forbidden" in out

    def test_filter_flag_parse(self, capsys):
        vb.main([str(SPEC_PATH), "--filter", "parse", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_filter_flag_security(self, capsys):
        vb.main([str(SPEC_PATH), "--filter", "security", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 14
        assert all(r["passed"] for r in data)
