"""
Tests for the Python-module backend and pygments behavioral spec
in tools/verify_behavior.py.

Organized as:
  - PythonModuleLoader: loading pygments via the python_module backend
  - TestPygmentsVersion: version invariants
  - TestPygmentsHighlight: highlight/formatter structural defaults
  - TestPygmentsLexers: lexer name resolution via get_lexer_by_name
  - TestPygmentsFormatters: formatter class-level properties
  - TestPygmentsTokens: Token type string representations
  - TestPygmentsStyles: style class name and background_color
  - TestPygmentsAll: all-pass integration + invariant count
  - TestPygmentsCLI: CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Pre-import pygments submodules so the harness can resolve dotted attribute paths.
import pygments.lexers       # noqa: F401 — side-effect: sets pygments.lexers
import pygments.formatters   # noqa: F401 — side-effect: sets pygments.formatters
import pygments.token        # noqa: F401 — side-effect: sets pygments.token
import pygments.styles       # noqa: F401 — side-effect: sets pygments.styles

import verify_behavior as vb

PYGMENTS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pygments.zspec.json"

# Total number of invariants in the spec (update if spec grows)
EXPECTED_INVARIANT_COUNT = 19


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pygments_spec():
    return vb.SpecLoader().load(PYGMENTS_SPEC_PATH)


@pytest.fixture(scope="module")
def pygments_mod(pygments_spec):
    return vb.LibraryLoader().load(pygments_spec["library"])


@pytest.fixture(scope="module")
def constants_map(pygments_spec):
    return vb.InvariantRunner().build_constants_map(pygments_spec["constants"])


@pytest.fixture(scope="module")
def registry(pygments_mod, constants_map):
    return vb.PatternRegistry(pygments_mod, constants_map)


# ---------------------------------------------------------------------------
# PythonModuleLoader
# ---------------------------------------------------------------------------

class TestPythonModuleLoader:
    def test_loads_pygments_spec(self, pygments_spec):
        assert isinstance(pygments_spec, dict)

    def test_all_required_sections_present(self, pygments_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pygments_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pygments_spec):
        assert pygments_spec["library"]["backend"] == "python_module"

    def test_module_name_is_pygments(self, pygments_spec):
        assert pygments_spec["library"]["module_name"] == "pygments"

    def test_loads_pygments_module(self, pygments_mod):
        import pygments as _pygments
        assert pygments_mod is _pygments

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz",
            })

    def test_all_invariant_kinds_known(self, pygments_spec):
        for inv in pygments_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pygments_spec):
        ids = [inv["id"] for inv in pygments_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

class TestPygmentsVersion:
    def test_version_starts_with_digit(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["2"],
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

    def test_fails_on_wrong_prefix(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["99"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# highlight
# ---------------------------------------------------------------------------

class TestPygmentsHighlight:
    def test_html_formatter_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "formatters.HtmlFormatter",
                "args": [],
                "method": "name",
                "expected": "HTML",
            },
        })
        assert ok, msg

    def test_html_formatter_cssclass(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "formatters.HtmlFormatter",
                "args": [],
                "method": "cssclass",
                "expected": "highlight",
            },
        })
        assert ok, msg

    def test_null_formatter_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "formatters.NullFormatter",
                "args": [],
                "method": "name",
                "expected": "Text only",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_formatter_name(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "formatters.HtmlFormatter",
                "args": [],
                "method": "name",
                "expected": "NotAFormatter",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# lexers
# ---------------------------------------------------------------------------

class TestPygmentsLexers:
    def test_python_lexer_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "lexers.get_lexer_by_name",
                "args": ["python"],
                "method": "name",
                "expected": "Python",
            },
        })
        assert ok, msg

    def test_json_lexer_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "lexers.get_lexer_by_name",
                "args": ["json"],
                "method": "name",
                "expected": "JSON",
            },
        })
        assert ok, msg

    def test_bash_lexer_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "lexers.get_lexer_by_name",
                "args": ["bash"],
                "method": "name",
                "expected": "Bash",
            },
        })
        assert ok, msg

    def test_javascript_lexer_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "lexers.get_lexer_by_name",
                "args": ["javascript"],
                "method": "name",
                "expected": "JavaScript",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_lexer_name(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "lexers.get_lexer_by_name",
                "args": ["python"],
                "method": "name",
                "expected": "NotPython",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# formatters
# ---------------------------------------------------------------------------

class TestPygmentsFormatters:
    def test_html_formatter_linenostart_default(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "formatters.HtmlFormatter",
                "args": [],
                "method": "linenostart",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_linenostart(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "formatters.HtmlFormatter",
                "args": [],
                "method": "linenostart",
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# tokens
# ---------------------------------------------------------------------------

class TestPygmentsTokens:
    def test_token_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "token.Token.__str__",
                "args": [],
                "expected": "Token",
            },
        })
        assert ok, msg

    def test_keyword_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "token.Token.Keyword.__str__",
                "args": [],
                "expected": "Token.Keyword",
            },
        })
        assert ok, msg

    def test_name_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "token.Token.Name.__str__",
                "args": [],
                "expected": "Token.Name",
            },
        })
        assert ok, msg

    def test_comment_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "token.Token.Comment.__str__",
                "args": [],
                "expected": "Token.Comment",
            },
        })
        assert ok, msg

    def test_text_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "token.Token.Text.__str__",
                "args": [],
                "expected": "Token.Text",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_token_string(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "token.Token.Keyword.__str__",
                "args": [],
                "expected": "Token.NotKeyword",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# styles
# ---------------------------------------------------------------------------

class TestPygmentsStyles:
    def test_default_style_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "styles.get_style_by_name",
                "args": ["default"],
                "method": "__name__",
                "expected": "DefaultStyle",
            },
        })
        assert ok, msg

    def test_default_style_background(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "styles.get_style_by_name",
                "args": ["default"],
                "method": "background_color",
                "expected": "#f8f8f8",
            },
        })
        assert ok, msg

    def test_monokai_style_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "styles.get_style_by_name",
                "args": ["monokai"],
                "method": "__name__",
                "expected": "MonokaiStyle",
            },
        })
        assert ok, msg

    def test_monokai_style_background(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "styles.get_style_by_name",
                "args": ["monokai"],
                "method": "background_color",
                "expected": "#272822",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_style_name(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "styles.get_style_by_name",
                "args": ["default"],
                "method": "__name__",
                "expected": "WrongStyle",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPygmentsAll — InvariantRunner integration
# ---------------------------------------------------------------------------

class TestPygmentsAll:
    def test_all_pass(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod)
        assert len(results) == EXPECTED_INVARIANT_COUNT

    def test_no_skips(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_lexers_category(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod, filter_category="lexers")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_tokens_category(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod, filter_category="tokens")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_styles_category(self, pygments_spec, pygments_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pygments_spec, pygments_mod, filter_category="styles")
        assert len(results) == 4
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestPygmentsCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PYGMENTS_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(PYGMENTS_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert f"{EXPECTED_INVARIANT_COUNT} invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PYGMENTS_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "pygments.version.starts_with_digit" in out
        assert "pygments.token.keyword" in out

    def test_filter_flag_version(self, capsys):
        vb.main([str(PYGMENTS_SPEC_PATH), "--filter", "version", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(PYGMENTS_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == EXPECTED_INVARIANT_COUNT
        assert all(r["passed"] for r in data)
