"""
Tests for the docutils Z-layer behavioral spec (docutils.zspec.zsdl).

Covers:
  - SpecLoader: loading docutils spec via python_module backend
  - python_call_eq handler with dotted-path attribute access
  - InvariantRunner integration: all 12 invariants pass
  - CLI: verify-behavior runs docutils.zspec.json end-to-end

Categories verified:
  version (2)      — __version__ dot check; __version_info__[0] >= 0
  version_info (3) — length 6; major >= 0; minor >= 0
  core (1)         — core.publish_string.__name__ == 'publish_string'
  nodes (6)        — Text, paragraph, section, title, Node, Element class names
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

DOCUTILS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "docutils.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def docutils_spec():
    return vb.SpecLoader().load(DOCUTILS_SPEC_PATH)


@pytest.fixture(scope="module")
def docutils_mod(docutils_spec):
    return vb.LibraryLoader().load(docutils_spec["library"])


@pytest.fixture(scope="module")
def constants_map(docutils_spec):
    return vb.InvariantRunner().build_constants_map(docutils_spec["constants"])


@pytest.fixture(scope="module")
def registry(docutils_mod, constants_map):
    return vb.PatternRegistry(docutils_mod, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader / module loader
# ---------------------------------------------------------------------------

class TestDocutilsSpecLoader:
    def test_loads_docutils_spec(self, docutils_spec):
        assert isinstance(docutils_spec, dict)

    def test_all_required_sections_present(self, docutils_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in docutils_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, docutils_spec):
        assert docutils_spec["library"]["backend"] == "python_module"

    def test_module_name_is_docutils(self, docutils_spec):
        assert docutils_spec["library"]["module_name"] == "docutils"

    def test_loads_docutils_module(self, docutils_mod):
        import docutils
        assert docutils_mod is docutils

    def test_all_invariant_kinds_known(self, docutils_spec):
        for inv in docutils_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, docutils_spec):
        ids = [inv["id"] for inv in docutils_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version — __version__ dot check and version_info first element
# ---------------------------------------------------------------------------

class TestDocutilsVersion:
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

    def test_version_info_major_ge_0(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version_info__.__getitem__",
                "args": [0],
                "method": "__ge__",
                "method_args": [0],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_contains_dot_fails_for_empty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["XYZZY"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# version_info — tuple length, major, minor
# ---------------------------------------------------------------------------

class TestDocutilsVersionInfo:
    def test_version_info_length_is_6(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version_info__.__len__",
                "args": [],
                "expected": 6,
            },
        })
        assert ok, msg

    def test_version_info_major_ge_0(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version_info__.major.__ge__",
                "args": [0],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_info_minor_ge_0(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version_info__.minor.__ge__",
                "args": [0],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_info_wrong_length_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version_info__.__len__",
                "args": [],
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# core — core.publish_string function name
# ---------------------------------------------------------------------------

class TestDocutilsCore:
    def test_publish_string_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "core.publish_string.__name__.__eq__",
                "args": ["publish_string"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_publish_string_wrong_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "core.publish_string.__name__.__eq__",
                "args": ["wrong_name"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# nodes — class name attributes
# ---------------------------------------------------------------------------

class TestDocutilsNodes:
    def test_text_classname(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.Text.__name__.__eq__",
                "args": ["Text"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_paragraph_classname(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.paragraph.__name__.__eq__",
                "args": ["paragraph"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_section_classname(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.section.__name__.__eq__",
                "args": ["section"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_title_classname(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.title.__name__.__eq__",
                "args": ["title"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_node_base_classname(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.Node.__name__.__eq__",
                "args": ["Node"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_element_classname(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.Element.__name__.__eq__",
                "args": ["Element"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrong_classname_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "nodes.Text.__name__.__eq__",
                "args": ["NotText"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 12 docutils invariants must pass
# ---------------------------------------------------------------------------

class TestDocutilsAll:
    def test_all_pass(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod)
        assert len(results) == 12

    def test_no_skips(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_version_info_category(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod, filter_category="version_info")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_core_category(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod, filter_category="core")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_nodes_category(self, docutils_spec, docutils_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(docutils_spec, docutils_mod, filter_category="nodes")
        assert len(results) == 6
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestDocutilsCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(DOCUTILS_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(DOCUTILS_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "12 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(DOCUTILS_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "docutils.version" in out
        assert "docutils.nodes" in out

    def test_filter_flag(self, capsys):
        vb.main([str(DOCUTILS_SPEC_PATH), "--filter", "version", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(DOCUTILS_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 12
        assert all(r["passed"] for r in data)
