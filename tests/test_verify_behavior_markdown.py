"""
Tests for the markdown Z-layer behavioral spec (markdown.zspec.zsdl).

Covers:
  - SpecLoader: loading markdown spec via python_module backend
  - python_call_eq handler with markdown-specific patterns
  - InvariantRunner integration: all 14 invariants pass
  - CLI: verify-behavior runs markdown.zspec.json end-to-end

Categories verified:
  version (2)  — __version__ is a string and contains a dot
  convert (5)  — markdown() converts h1, bold, italic, inline-code, plain paragraph
  links (2)    — link syntax produces <a href=...>
  lists (2)    — unordered list produces <ul><li> structure
  class (3)    — Markdown class name and instance convert()
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

MARKDOWN_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "markdown.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def markdown_spec():
    return vb.SpecLoader().load(MARKDOWN_SPEC_PATH)


@pytest.fixture(scope="module")
def markdown_mod(markdown_spec):
    return vb.LibraryLoader().load(markdown_spec["library"])


@pytest.fixture(scope="module")
def constants_map(markdown_spec):
    return vb.InvariantRunner().build_constants_map(markdown_spec["constants"])


@pytest.fixture(scope="module")
def registry(markdown_mod, constants_map):
    return vb.PatternRegistry(markdown_mod, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader / module loader
# ---------------------------------------------------------------------------

class TestMarkdownSpecLoader:
    def test_loads_markdown_spec(self, markdown_spec):
        assert isinstance(markdown_spec, dict)

    def test_all_required_sections_present(self, markdown_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in markdown_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, markdown_spec):
        assert markdown_spec["library"]["backend"] == "python_module"

    def test_module_name_is_markdown(self, markdown_spec):
        assert markdown_spec["library"]["module_name"] == "markdown"

    def test_loads_markdown_module(self, markdown_mod):
        import markdown
        assert markdown_mod is markdown

    def test_all_invariant_kinds_known(self, markdown_spec):
        for inv in markdown_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, markdown_spec):
        ids = [inv["id"] for inv in markdown_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version — __version__ is a string and contains a dot
# ---------------------------------------------------------------------------

class TestMarkdownVersion:
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


# ---------------------------------------------------------------------------
# convert — markdown() converts Markdown constructs to HTML
# ---------------------------------------------------------------------------

class TestMarkdownConvert:
    def test_h1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["# Hello"],
                "expected": "<h1>Hello</h1>",
            },
        })
        assert ok, msg

    def test_bold_contains_strong(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["**bold**"],
                "method": "__contains__",
                "method_args": ["<strong>"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_italic_contains_em(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["*italic*"],
                "method": "__contains__",
                "method_args": ["<em>"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_inline_code(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["`code`"],
                "expected": "<p><code>code</code></p>",
            },
        })
        assert ok, msg

    def test_paragraph(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["plain text"],
                "expected": "<p>plain text</p>",
            },
        })
        assert ok, msg

    def test_wrong_expected_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["# Hello"],
                "expected": "<h2>Hello</h2>",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# links — link syntax produces <a href="...">
# ---------------------------------------------------------------------------

class TestMarkdownLinks:
    def test_link_contains_a_href(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["[link](http://example.com)"],
                "method": "__contains__",
                "method_args": ["<a href="],
                "expected": True,
            },
        })
        assert ok, msg

    def test_link_exact_output(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["[link](http://example.com)"],
                "expected": '<p><a href="http://example.com">link</a></p>',
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# lists — unordered list produces <ul><li> structure
# ---------------------------------------------------------------------------

class TestMarkdownLists:
    def test_unordered_contains_ul(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["- item1\n- item2"],
                "method": "__contains__",
                "method_args": ["<ul>"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_unordered_contains_li(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "markdown",
                "args": ["- item1\n- item2"],
                "method": "__contains__",
                "method_args": ["<li>item1</li>"],
                "expected": True,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# class — Markdown class name and instance convert()
# ---------------------------------------------------------------------------

class TestMarkdownClass:
    def test_class_name_is_Markdown(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markdown.__name__.__eq__",
                "args": ["Markdown"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_convert_produces_p(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markdown",
                "args": [],
                "method": "convert",
                "method_args": ["text"],
                "expected": "<p>text</p>",
            },
        })
        assert ok, msg

    def test_convert_h1(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markdown",
                "args": [],
                "method": "convert",
                "method_args": ["# Title"],
                "expected": "<h1>Title</h1>",
            },
        })
        assert ok, msg

    def test_wrong_class_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markdown.__name__.__eq__",
                "args": ["NotMarkdown"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 14 markdown invariants must pass
# ---------------------------------------------------------------------------

class TestMarkdownAll:
    def test_all_pass(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod)
        assert len(results) == 14

    def test_no_skips(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_convert_category(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod, filter_category="convert")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_links_category(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod, filter_category="links")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_lists_category(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod, filter_category="lists")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_class_category(self, markdown_spec, markdown_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(markdown_spec, markdown_mod, filter_category="class")
        assert len(results) == 3
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestMarkdownCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(MARKDOWN_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(MARKDOWN_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "14 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(MARKDOWN_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "markdown.version" in out
        assert "markdown.convert" in out

    def test_filter_flag(self, capsys):
        vb.main([str(MARKDOWN_SPEC_PATH), "--filter", "convert", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(MARKDOWN_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 14
        assert all(r["passed"] for r in data)
