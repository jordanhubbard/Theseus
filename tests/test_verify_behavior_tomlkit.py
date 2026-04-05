"""
Tests for the python_module backend and tomlkit behavioral spec
in tools/verify_behavior.py.

Organized as:
  - TestTomlkitLoader: loading the tomlkit spec and module
  - TestTomlkitVersion: version invariants
  - TestTomlkitLoads: loads() scalar and structure invariants
  - TestTomlkitDumps: dumps() invariants
  - TestTomlkitDocument: document() and table() invariants
  - TestTomlkitErrors: error/exception invariants
  - TestTomlkitAll: all 16 invariants pass (integration runner)
  - TestTomlkitCLI: verify_behavior CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
# When running from the worktree (.claude/worktrees/<id>/tests/), walk up to the
# actual repository root (which has _build/ and tools/).
# Structure: <repo>/.claude/worktrees/<id>/tests/test_*.py
_candidate = _HERE.parent.parent.parent.parent.parent
REPO_ROOT = _candidate if (_candidate / "tools" / "verify_behavior.py").exists() else _HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Skip entire module if tomlkit is not installed
tomlkit = pytest.importorskip("tomlkit", reason="tomlkit not installed")

import verify_behavior as vb

TOMLKIT_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "tomlkit.zspec.json"

_EXPECTED_COUNT = 16


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tomlkit_spec():
    return vb.SpecLoader().load(TOMLKIT_SPEC_PATH)


@pytest.fixture(scope="module")
def tomlkit_mod(tomlkit_spec):
    return vb.LibraryLoader().load(tomlkit_spec["library"])


@pytest.fixture(scope="module")
def registry(tomlkit_mod):
    return vb.PatternRegistry(tomlkit_mod, {})


# ---------------------------------------------------------------------------
# TestTomlkitLoader
# ---------------------------------------------------------------------------

class TestTomlkitLoader:
    def test_loads_spec(self, tomlkit_spec):
        assert isinstance(tomlkit_spec, dict)

    def test_all_required_sections_present(self, tomlkit_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in tomlkit_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, tomlkit_spec):
        assert tomlkit_spec["library"]["backend"] == "python_module"

    def test_module_name_is_tomlkit(self, tomlkit_spec):
        assert tomlkit_spec["library"]["module_name"] == "tomlkit"

    def test_loads_tomlkit_module(self, tomlkit_mod):
        import tomlkit as tk
        assert tomlkit_mod is tk

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_tomlkit_xyz",
            })

    def test_all_invariant_kinds_known(self, tomlkit_spec):
        for inv in tomlkit_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, tomlkit_spec):
        ids = [inv["id"] for inv in tomlkit_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count(self, tomlkit_spec):
        assert len(tomlkit_spec["invariants"]) == _EXPECTED_COUNT


# ---------------------------------------------------------------------------
# TestTomlkitVersion
# ---------------------------------------------------------------------------

class TestTomlkitVersion:
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

    def test_version_is_actually_a_string(self):
        import tomlkit as tk
        assert isinstance(tk.__version__, str)

    def test_version_dot_count(self):
        import tomlkit as tk
        # Typical version like '0.14.0' has at least one dot
        assert "." in tk.__version__


# ---------------------------------------------------------------------------
# TestTomlkitLoads
# ---------------------------------------------------------------------------

class TestTomlkitLoads:
    def test_integer(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["a = 42"],
                "method": "get",
                "method_args": ["a"],
                "expected": 42,
            },
        })
        assert ok, msg

    def test_float(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["a = 3.14"],
                "method": "get",
                "method_args": ["a"],
                "expected": 3.14,
            },
        })
        assert ok, msg

    def test_true_bool(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["a = true"],
                "method": "get",
                "method_args": ["a"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_false_bool(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["a = false"],
                "method": "get",
                "method_args": ["a"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ['a = "Bob"'],
                "method": "get",
                "method_args": ["a"],
                "expected": "Bob",
            },
        })
        assert ok, msg

    def test_empty_doc_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": [""],
                "method": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_array(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["x = [1, 2, 3]"],
                "method": "get",
                "method_args": ["x"],
                "expected": [1, 2, 3],
            },
        })
        assert ok, msg

    def test_inline_table(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["p = {x=1, y=2}"],
                "method": "get",
                "method_args": ["p"],
                "expected": {"x": 1, "y": 2},
            },
        })
        assert ok, msg

    def test_wrong_expected_fails(self, registry):
        ok, _ = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "loads",
                "args": ["a = 42"],
                "method": "get",
                "method_args": ["a"],
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestTomlkitDumps
# ---------------------------------------------------------------------------

class TestTomlkitDumps:
    def test_dumps_is_callable(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dumps.__class__.__name__.__eq__",
                "args": ["function"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_dumps_roundtrip_preserves_content(self):
        import tomlkit as tk
        original = "k = 1\n"
        doc = tk.loads(original)
        assert tk.dumps(doc) == original

    def test_dumps_preserves_string_value(self):
        import tomlkit as tk
        doc = tk.loads('name = "Alice"')
        out = tk.dumps(doc)
        assert "name" in out
        assert "Alice" in out


# ---------------------------------------------------------------------------
# TestTomlkitDocument
# ---------------------------------------------------------------------------

class TestTomlkitDocument:
    def test_toml_document_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "TOMLDocument.__name__.__eq__",
                "args": ["TOMLDocument"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_document_empty_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "document",
                "method": "__len__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_table_callable(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "table.__class__.__name__.__eq__",
                "args": ["function"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_document_class_identity(self):
        import tomlkit as tk
        doc = tk.document()
        assert type(doc).__name__ == "TOMLDocument"

    def test_table_class_identity(self):
        import tomlkit as tk
        t = tk.table()
        assert type(t).__name__ == "Table"


# ---------------------------------------------------------------------------
# TestTomlkitErrors
# ---------------------------------------------------------------------------

class TestTomlkitErrors:
    def test_unclosed_array_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": ["x = [unclosed"],
                "expected_exception": "tomlkit.exceptions.ParseError",
            },
        })
        assert ok, msg

    def test_empty_key_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": ["= nope"],
                "expected_exception": "tomlkit.exceptions.ParseError",
            },
        })
        assert ok, msg

    def test_no_raise_on_valid_toml(self, registry):
        # Valid TOML should NOT raise — raises handler returns False correctly
        ok, _ = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "loads",
                "args": ["valid = 1"],
                "expected_exception": "tomlkit.exceptions.ParseError",
            },
        })
        assert not ok

    def test_parseerror_is_valueerror(self):
        import tomlkit.exceptions
        assert issubclass(tomlkit.exceptions.ParseError, ValueError)

    def test_unexpected_char_error_is_parseerror(self):
        import tomlkit.exceptions
        assert issubclass(tomlkit.exceptions.UnexpectedCharError, tomlkit.exceptions.ParseError)


# ---------------------------------------------------------------------------
# TestTomlkitAll — full InvariantRunner integration
# ---------------------------------------------------------------------------

class TestTomlkitAll:
    def test_all_pass(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod)
        assert len(results) == _EXPECTED_COUNT

    def test_no_skips(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_version_category(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod, filter_category="version")
        # is_string + contains_dot = 2
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_loads_category(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod, filter_category="loads")
        # 5 table rows + empty + array + inline_table = 8
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_filter_dumps_category(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod, filter_category="dumps")
        # is_callable = 1
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_document_category(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod, filter_category="document")
        # class_name + empty_len + table_callable = 3
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_error_category(self, tomlkit_spec, tomlkit_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tomlkit_spec, tomlkit_mod, filter_category="error")
        # unclosed_array_raises + empty_key_raises = 2
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestTomlkitCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestTomlkitCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(TOMLKIT_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(TOMLKIT_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert f"{_EXPECTED_COUNT} invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(TOMLKIT_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "tomlkit.version.is_string" in out
        assert "tomlkit.error.unclosed_array_raises" in out

    def test_filter_flag_loads(self, capsys):
        vb.main([str(TOMLKIT_SPEC_PATH), "--filter", "loads", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_filter_flag_error(self, capsys):
        vb.main([str(TOMLKIT_SPEC_PATH), "--filter", "error", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(TOMLKIT_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == _EXPECTED_COUNT
        assert all(r["passed"] for r in data)
