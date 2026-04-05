"""
Tests for the Python-module backend with the markupsafe behavioral spec.

Organized as:
  - TestMarkupSafeLoader: spec loading and validation
  - TestMarkupSafeEscape: python_call_eq for escape category (6 invariants)
  - TestMarkupSafeMarkup: python_call_eq for markup category (8 invariants)
  - TestMarkupSafeEscapeSilent: python_call_eq for escape_silent category (3 invariants)
  - TestMarkupSafeSoftStr: python_call_eq for soft_str category (4 invariants)
  - TestMarkupSafeAll: InvariantRunner integration — all 21 invariants pass
  - TestMarkupSafeCLI: CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "markupsafe.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ms_spec():
    return vb.SpecLoader().load(SPEC_PATH)


@pytest.fixture(scope="module")
def ms_mod(ms_spec):
    return vb.LibraryLoader().load(ms_spec["library"])


@pytest.fixture(scope="module")
def constants_map(ms_spec):
    return vb.InvariantRunner().build_constants_map(ms_spec["constants"])


@pytest.fixture(scope="module")
def registry(ms_mod, constants_map):
    return vb.PatternRegistry(ms_mod, constants_map)


# ---------------------------------------------------------------------------
# TestMarkupSafeLoader
# ---------------------------------------------------------------------------

class TestMarkupSafeLoader:
    def test_loads_spec(self, ms_spec):
        assert isinstance(ms_spec, dict)

    def test_all_required_sections_present(self, ms_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in ms_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, ms_spec):
        assert ms_spec["library"]["backend"] == "python_module"

    def test_module_name_is_markupsafe(self, ms_spec):
        assert ms_spec["library"]["module_name"] == "markupsafe"

    def test_loads_markupsafe_module(self, ms_mod):
        import markupsafe
        assert ms_mod is markupsafe

    def test_all_invariant_kinds_known(self, ms_spec):
        for inv in ms_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, ms_spec):
        ids = [inv["id"] for inv in ms_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestMarkupSafeEscape
# ---------------------------------------------------------------------------

class TestMarkupSafeEscape:
    def test_lt_gt(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": ["<b>hello</b>"],
                "expected": "&lt;b&gt;hello&lt;/b&gt;",
            },
        })
        assert ok, msg

    def test_ampersand(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": ["a & b"],
                "expected": "a &amp; b",
            },
        })
        assert ok, msg

    def test_double_quote(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": ['"quoted"'],
                "expected": "&#34;quoted&#34;",
            },
        })
        assert ok, msg

    def test_single_quote(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": ["'apostrophe'"],
                "expected": "&#39;apostrophe&#39;",
            },
        })
        assert ok, msg

    def test_plain_text_passthrough(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": ["no special chars"],
                "expected": "no special chars",
            },
        })
        assert ok, msg

    def test_empty_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": [""],
                "expected": "",
            },
        })
        assert ok, msg

    def test_wrong_expected_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape",
                "args": ["<b>"],
                "expected": "<b>",  # wrong: should be &lt;b&gt;
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestMarkupSafeMarkup
# ---------------------------------------------------------------------------

class TestMarkupSafeMarkup:
    def test_striptags_bold(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup",
                "args": ["<b>bold</b>"],
                "method": "striptags",
                "expected": "bold",
            },
        })
        assert ok, msg

    def test_striptags_nested(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup",
                "args": ["<em><b>x</b></em>"],
                "method": "striptags",
                "expected": "x",
            },
        })
        assert ok, msg

    def test_striptags_plain(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup",
                "args": ["no tags here"],
                "method": "striptags",
                "expected": "no tags here",
            },
        })
        assert ok, msg

    def test_unescape_lt_gt(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup",
                "args": ["&lt;b&gt;"],
                "method": "unescape",
                "expected": "<b>",
            },
        })
        assert ok, msg

    def test_unescape_amp(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup",
                "args": ["a &amp; b"],
                "method": "unescape",
                "expected": "a & b",
            },
        })
        assert ok, msg

    def test_unescape_plain(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup",
                "args": ["plain text"],
                "method": "unescape",
                "expected": "plain text",
            },
        })
        assert ok, msg

    def test_escape_classmethod(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup.escape",
                "args": ["<x>"],
                "expected": "&lt;x&gt;",
            },
        })
        assert ok, msg

    def test_escape_classmethod_amp(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Markup.escape",
                "args": ["hello & world"],
                "expected": "hello &amp; world",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMarkupSafeEscapeSilent
# ---------------------------------------------------------------------------

class TestMarkupSafeEscapeSilent:
    def test_none_returns_empty(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape_silent",
                "args": [None],
                "expected": "",
            },
        })
        assert ok, msg

    def test_html_chars_escaped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape_silent",
                "args": ["<b>"],
                "expected": "&lt;b&gt;",
            },
        })
        assert ok, msg

    def test_plain_passthrough(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape_silent",
                "args": ["hi"],
                "expected": "hi",
            },
        })
        assert ok, msg

    def test_fails_when_expecting_raw_on_none(self, registry):
        # escape_silent(None) returns '' not raises — wrong expected should fail
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape_silent",
                "args": [None],
                "expected": "None",  # wrong: should be ''
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestMarkupSafeSoftStr
# ---------------------------------------------------------------------------

class TestMarkupSafeSoftStr:
    def test_string_passthrough(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "soft_str",
                "args": ["hello"],
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_int_to_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "soft_str",
                "args": [42],
                "expected": "42",
            },
        })
        assert ok, msg

    def test_none_to_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "soft_str",
                "args": [None],
                "expected": "None",
            },
        })
        assert ok, msg

    def test_float_to_str(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "soft_str",
                "args": [3.14],
                "expected": "3.14",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestMarkupSafeAll — InvariantRunner integration
# ---------------------------------------------------------------------------

class TestMarkupSafeAll:
    def test_all_pass(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod)
        assert len(results) == 21

    def test_no_skips(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_escape_category(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod, filter_category="escape")
        # 6 escape invariants
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_markup_category(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod, filter_category="markup")
        # 3 striptags + 3 unescape + 2 Markup.escape = 8 invariants
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_filter_escape_silent_category(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod, filter_category="escape_silent")
        # 3 invariants
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_soft_str_category(self, ms_spec, ms_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(ms_spec, ms_mod, filter_category="soft_str")
        # 4 invariants
        assert len(results) == 4
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestMarkupSafeCLI — CLI end-to-end
# ---------------------------------------------------------------------------

class TestMarkupSafeCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "21 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "markupsafe.escape.lt_gt" in out
        assert "markupsafe.soft_str.none_to_str" in out

    def test_filter_flag(self, capsys):
        vb.main([str(SPEC_PATH), "--filter", "escape", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 21
        assert all(r["passed"] for r in data)
