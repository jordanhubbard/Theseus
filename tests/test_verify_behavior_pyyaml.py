"""
Tests for the python_module backend and pyyaml-specific invariants
in tools/verify_behavior.py.

Organized as:
  - TestPyyamlLoader: loading the pyyaml spec and the yaml module
  - TestPyyamlLoadScalars: safe_load scalar invariants
  - TestPyyamlLoadStructures: safe_load structure invariants
  - TestPyyamlDump: dump invariants
  - TestPyyamlErrors: error/exception invariants
  - TestPyyamlAll: all 18 pyyaml invariants pass
  - TestPyyamlCLI: verify_behavior CLI end-to-end
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

# Skip entire module if yaml is not installed
yaml = pytest.importorskip("yaml", reason="pyyaml not installed")

import verify_behavior as vb

PYYAML_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pyyaml.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pyyaml_spec():
    return vb.SpecLoader().load(PYYAML_SPEC_PATH)


@pytest.fixture(scope="module")
def pyyaml_mod(pyyaml_spec):
    return vb.LibraryLoader().load(pyyaml_spec["library"])


@pytest.fixture(scope="module")
def constants_map(pyyaml_spec):
    return vb.InvariantRunner().build_constants_map(pyyaml_spec["constants"])


@pytest.fixture(scope="module")
def registry(pyyaml_mod, constants_map):
    return vb.PatternRegistry(pyyaml_mod, constants_map)


# ---------------------------------------------------------------------------
# TestPyyamlLoader
# ---------------------------------------------------------------------------

class TestPyyamlLoader:
    def test_loads_spec(self, pyyaml_spec):
        assert isinstance(pyyaml_spec, dict)

    def test_all_required_sections_present(self, pyyaml_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pyyaml_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pyyaml_spec):
        assert pyyaml_spec["library"]["backend"] == "python_module"

    def test_module_name_is_yaml(self, pyyaml_spec):
        assert pyyaml_spec["library"]["module_name"] == "yaml"

    def test_loads_yaml_module(self, pyyaml_mod):
        import yaml as yaml_mod
        assert pyyaml_mod is yaml_mod

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_pyyaml_xyz",
            })

    def test_all_invariant_kinds_known(self, pyyaml_spec):
        for inv in pyyaml_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pyyaml_spec):
        ids = [inv["id"] for inv in pyyaml_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_18(self, pyyaml_spec):
        assert len(pyyaml_spec["invariants"]) == 18


# ---------------------------------------------------------------------------
# TestPyyamlLoadScalars
# ---------------------------------------------------------------------------

class TestPyyamlLoadScalars:
    def test_integer(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["42"], "expected": 42},
        })
        assert ok, msg

    def test_float(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["3.14"], "expected": 3.14},
        })
        assert ok, msg

    def test_true_bool(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["true"], "expected": True},
        })
        assert ok, msg

    def test_false_bool(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["false"], "expected": False},
        })
        assert ok, msg

    def test_null(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["null"], "expected": None},
        })
        assert ok, msg

    def test_quoted_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ['"hello"'], "expected": "hello"},
        })
        assert ok, msg

    def test_bare_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["hello"], "expected": "hello"},
        })
        assert ok, msg

    def test_wrong_expected_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {"function": "safe_load", "args": ["42"], "expected": 99},
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestPyyamlLoadStructures
# ---------------------------------------------------------------------------

class TestPyyamlLoadStructures:
    def test_mapping(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "safe_load",
                "args": ["key: value"],
                "expected": {"key": "value"},
            },
        })
        assert ok, msg

    def test_inline_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "safe_load",
                "args": ["[1, 2, 3]"],
                "expected": [1, 2, 3],
            },
        })
        assert ok, msg

    def test_block_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "safe_load",
                "args": ["- a\n- b\n- c"],
                "expected": ["a", "b", "c"],
            },
        })
        assert ok, msg

    def test_nested_mapping(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "safe_load",
                "args": ["outer:\n  inner: 42"],
                "expected": {"outer": {"inner": 42}},
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestPyyamlDump
# ---------------------------------------------------------------------------

class TestPyyamlDump:
    def test_dict(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dump",
                "args": [{"key": "value"}],
                "expected": "key: value\n",
            },
        })
        assert ok, msg

    def test_list(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dump",
                "args": [[1, 2, 3]],
                "expected": "- 1\n- 2\n- 3\n",
            },
        })
        assert ok, msg

    def test_integer(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dump",
                "args": [42],
                "expected": "42\n...\n",
            },
        })
        assert ok, msg

    def test_none(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dump",
                "args": [None],
                "expected": "null\n...\n",
            },
        })
        assert ok, msg

    def test_sorted_keys(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "dump",
                "args": [{"b": 1, "a": 2}],
                "kwargs": {"default_flow_style": False},
                "expected": "a: 2\nb: 1\n",
            },
        })
        assert ok, msg

    def test_safe_dump_simple_dict(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "safe_dump",
                "args": [{"x": 1}],
                "expected": "x: 1\n",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestPyyamlErrors
# ---------------------------------------------------------------------------

class TestPyyamlErrors:
    def test_malformed_yaml_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "safe_load",
                "args": [":"],
                "expected_exception": "yaml.parser.ParserError",
            },
        })
        assert ok, msg

    def test_no_raise_on_valid_yaml(self, registry):
        # Valid YAML should NOT raise — verify the raises handler returns False correctly
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "safe_load",
                "args": ["valid: yaml"],
                "expected_exception": "yaml.YAMLError",
            },
        })
        assert not ok  # no exception was raised — handler returns False

    def test_yaml_error_is_base_class(self):
        # Verify ParserError is a subclass of yaml.YAMLError per the PyYAML docs
        import yaml as yaml_mod
        assert issubclass(yaml_mod.parser.ParserError, yaml_mod.YAMLError)

    def test_version_is_string_starting_with_digit(self):
        # yaml.__version__ must be a non-empty string starting with a digit
        import yaml as yaml_mod
        v = yaml_mod.__version__
        assert isinstance(v, str)
        assert v and v[0].isdigit(), f"yaml.__version__ = {v!r} does not start with a digit"


# ---------------------------------------------------------------------------
# TestPyyamlAll — full InvariantRunner integration
# ---------------------------------------------------------------------------

class TestPyyamlAll:
    def test_all_pass(self, pyyaml_spec, pyyaml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyyaml_spec, pyyaml_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pyyaml_spec, pyyaml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyyaml_spec, pyyaml_mod)
        assert len(results) == 18

    def test_no_skips(self, pyyaml_spec, pyyaml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyyaml_spec, pyyaml_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_load_category(self, pyyaml_spec, pyyaml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyyaml_spec, pyyaml_mod, filter_category="load")
        # 7 scalars + 3 structures + 1 nested = 11
        assert len(results) == 11
        assert all(r.passed for r in results)

    def test_filter_dump_category(self, pyyaml_spec, pyyaml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyyaml_spec, pyyaml_mod, filter_category="dump")
        # 4 dump rows + 1 sorted_keys + 1 safe_dump = 6
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_errors_category(self, pyyaml_spec, pyyaml_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pyyaml_spec, pyyaml_mod, filter_category="errors")
        assert len(results) == 1
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestPyyamlCLI — end-to-end CLI
# ---------------------------------------------------------------------------

class TestPyyamlCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PYYAML_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(PYYAML_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "18 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PYYAML_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "pyyaml.safe_load.integer" in out
        assert "pyyaml.dump.dict" in out

    def test_filter_flag_load(self, capsys):
        vb.main([str(PYYAML_SPEC_PATH), "--filter", "load", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(PYYAML_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 18
        assert all(r["passed"] for r in data)
