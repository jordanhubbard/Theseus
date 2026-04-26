"""
Tests for the lodash Z-layer behavioral spec.

Organized as:
  - LodashBackend: LibraryLoader loading node + lodash module
  - LodashNodeModuleCallEq: unit tests for the node_module_call_eq handler
  - LodashSpecIntegration: all invariants pass end-to-end
  - LodashCLI: main() exit-code and --list / --verbose / --json-out flags
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

LODASH_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "lodash.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lodash_spec():
    return vb.SpecLoader().load(LODASH_SPEC_PATH)


@pytest.fixture(scope="module")
def lodash_backend(lodash_spec):
    try:
        return vb.LibraryLoader().load(lodash_spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"lodash backend not available: {exc}")


@pytest.fixture(scope="module")
def registry(lodash_backend):
    return vb.PatternRegistry(lodash_backend, {})


# ---------------------------------------------------------------------------
# LodashBackend
# ---------------------------------------------------------------------------

class TestLodashBackend:
    def test_loads_as_cli_backend(self, lodash_backend):
        assert isinstance(lodash_backend, vb.CLIBackend)

    def test_command_is_node(self, lodash_backend):
        assert "node" in lodash_backend.command

    def test_module_name_is_lodash(self, lodash_backend):
        assert lodash_backend.module_name == "lodash"

    def test_not_esm(self, lodash_backend):
        assert not getattr(lodash_backend, "esm", False)

    def test_spec_backend_field(self, lodash_spec):
        assert lodash_spec["library"]["backend"] == "cli"

    def test_spec_module_name_field(self, lodash_spec):
        assert lodash_spec["library"]["module_name"] == "lodash"

    def test_all_invariant_kinds_known(self, lodash_spec):
        for inv in lodash_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


# ---------------------------------------------------------------------------
# LodashNodeModuleCallEq — unit tests for the handler
# ---------------------------------------------------------------------------

class TestLodashNodeModuleCallEq:
    # chunk
    def test_chunk_even(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "chunk", "args": [[1, 2, 3, 4], 2], "expected": [[1, 2], [3, 4]]},
        })
        assert ok, msg

    def test_chunk_odd(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "chunk", "args": [[1, 2, 3, 4, 5], 2], "expected": [[1, 2], [3, 4], [5]]},
        })
        assert ok, msg

    # flatten
    def test_flatten_nested(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "flatten", "args": [[[1, 2], [3, 4]]], "expected": [1, 2, 3, 4]},
        })
        assert ok, msg

    # uniq
    def test_uniq_removes_duplicates(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "uniq", "args": [[1, 2, 1, 3, 2]], "expected": [1, 2, 3]},
        })
        assert ok, msg

    # math
    def test_sum(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "sum", "args": [[1, 2, 3]], "expected": 6},
        })
        assert ok, msg

    def test_sum_empty(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "sum", "args": [[]], "expected": 0},
        })
        assert ok, msg

    def test_max(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "max", "args": [[1, 5, 3]], "expected": 5},
        })
        assert ok, msg

    def test_min(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "min", "args": [[1, 5, 3]], "expected": 1},
        })
        assert ok, msg

    def test_clamp_in_range(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "clamp", "args": [5, 1, 10], "expected": 5},
        })
        assert ok, msg

    def test_clamp_below_min(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "clamp", "args": [-5, 1, 10], "expected": 1},
        })
        assert ok, msg

    def test_clamp_above_max(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "clamp", "args": [15, 1, 10], "expected": 10},
        })
        assert ok, msg

    # predicates
    def test_is_empty_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "isEmpty", "args": [[]], "expected": True},
        })
        assert ok, msg

    def test_is_empty_false(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "isEmpty", "args": [[1]], "expected": False},
        })
        assert ok, msg

    def test_is_array_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "isArray", "args": [[1, 2]], "expected": True},
        })
        assert ok, msg

    def test_is_array_false(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "isArray", "args": ["x"], "expected": False},
        })
        assert ok, msg

    def test_is_string_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "isString", "args": ["hello"], "expected": True},
        })
        assert ok, msg

    def test_is_number_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "isNumber", "args": [42], "expected": True},
        })
        assert ok, msg

    # string transforms
    def test_capitalize(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "capitalize", "args": ["hello"], "expected": "Hello"},
        })
        assert ok, msg

    def test_snake_case(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "snakeCase", "args": ["helloWorld"], "expected": "hello_world"},
        })
        assert ok, msg

    def test_camel_case(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "camelCase", "args": ["hello_world"], "expected": "helloWorld"},
        })
        assert ok, msg

    def test_wrong_expected_fails(self, registry):
        ok, _ = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "sum", "args": [[1, 2, 3]], "expected": 999},
        })
        assert not ok


# ---------------------------------------------------------------------------
# LodashSpecIntegration
# ---------------------------------------------------------------------------

class TestLodashSpecIntegration:
    def test_all_invariants_pass(self, lodash_spec, lodash_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(lodash_spec, lodash_backend)
        failed = [r for r in results if not r.passed]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, lodash_spec, lodash_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(lodash_spec, lodash_backend)
        # The base zspecs/lodash.zspec.zsdl is a small sampler; full per-function
        # coverage lives in lodash_chunk / lodash_camelcase / etc. specs.
        assert len(results) == 8

    def test_no_skips(self, lodash_spec, lodash_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(lodash_spec, lodash_backend)
        assert not any(r.skip_reason for r in results)

    def test_array_category(self, lodash_spec, lodash_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(lodash_spec, lodash_backend, filter_category="array")
        # 7 array invariants in the current sampler (chunk/flatten/uniq/sortBy/diff)
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_math_category(self, lodash_spec, lodash_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(lodash_spec, lodash_backend, filter_category="math")
        # 1 math invariant in the current sampler (sum)
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_all_ids_unique(self, lodash_spec):
        ids = [inv["id"] for inv in lodash_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# LodashCLI
# ---------------------------------------------------------------------------

class TestLodashCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(LODASH_SPEC_PATH)])
        assert rc == 0

    def test_verbose_shows_pass(self, capsys):
        vb.main([str(LODASH_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(LODASH_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        # Use an invariant that's in the current sampler (was 'lodash.version.contains_dot' in a richer historic spec)
        assert "lodash.lchunk.two" in out

    def test_filter_array(self, capsys):
        vb.main([str(LODASH_SPEC_PATH), "--filter", "array", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        out_file = tmp_path / "results.json"
        vb.main([str(LODASH_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        # Matches base zspecs/lodash.zspec.zsdl invariant count
        assert len(data) == 8
        assert all(r["passed"] for r in data)
