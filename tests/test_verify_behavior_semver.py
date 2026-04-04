"""
Tests for the node_module_call_eq pattern handler and the semver Z-layer spec.

Organized as:
  - NodeModuleBackend: LibraryLoader loading node + semver module
  - NodeModuleCallEq: unit tests for the handler via semver functions
  - SemverSpecIntegration: all 24 invariants pass end-to-end
  - SemverCLI: main() exit-code and --verbose / --list / --json-out flags
"""
import sys
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

SEMVER_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "semver.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def semver_spec():
    return vb.SpecLoader().load(SEMVER_SPEC_PATH)


@pytest.fixture(scope="module")
def semver_backend(semver_spec):
    try:
        return vb.LibraryLoader().load(semver_spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"semver backend not available: {exc}")


@pytest.fixture(scope="module")
def registry(semver_backend):
    return vb.PatternRegistry(semver_backend, {})


# ---------------------------------------------------------------------------
# NodeModuleBackend
# ---------------------------------------------------------------------------

class TestNodeModuleBackend:
    def test_loads_as_cli_backend(self, semver_backend):
        assert isinstance(semver_backend, vb.CLIBackend)

    def test_command_is_node(self, semver_backend):
        assert "node" in semver_backend.command

    def test_module_name_is_semver(self, semver_backend):
        assert semver_backend.module_name == "semver"

    def test_raises_on_missing_node_module(self):
        import shutil
        node = shutil.which("node")
        if not node:
            pytest.skip("node not in PATH")
        with pytest.raises(vb.LibraryNotFoundError, match="not found"):
            vb.LibraryLoader().load({
                "backend": "cli",
                "command": "node",
                "module_name": "no_such_npm_package_xyz_abc_123",
            })

    def test_spec_backend_field(self, semver_spec):
        assert semver_spec["library"]["backend"] == "cli"

    def test_spec_module_name_field(self, semver_spec):
        assert semver_spec["library"]["module_name"] == "semver"

    def test_all_invariant_kinds_are_node_module_call_eq(self, semver_spec):
        for inv in semver_spec["invariants"]:
            assert inv["kind"] == "node_module_call_eq"

    def test_all_invariant_kinds_known(self, semver_spec):
        for inv in semver_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


# ---------------------------------------------------------------------------
# NodeModuleCallEq — unit tests via semver functions
# ---------------------------------------------------------------------------

class TestNodeModuleCallEq:
    # valid()
    def test_valid_returns_string(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "valid", "args": ["1.2.3"], "expected": "1.2.3"},
        })
        assert ok, msg

    def test_valid_returns_null_for_garbage(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "valid", "args": ["not-a-version"], "expected": None},
        })
        assert ok, msg

    def test_valid_normalises_v_prefix(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "valid", "args": ["v1.2.3"], "expected": "1.2.3"},
        })
        assert ok, msg

    def test_valid_fails_on_wrong_expected(self, registry):
        ok, _ = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "valid", "args": ["1.2.3"], "expected": "9.9.9"},
        })
        assert not ok

    # gt / lt / eq
    def test_gt_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "gt", "args": ["2.0.0", "1.9.9"], "expected": True},
        })
        assert ok, msg

    def test_gt_false(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "gt", "args": ["1.0.0", "2.0.0"], "expected": False},
        })
        assert ok, msg

    def test_lt_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "lt", "args": ["1.0.0", "2.0.0"], "expected": True},
        })
        assert ok, msg

    def test_eq_true(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "eq", "args": ["1.2.3", "1.2.3"], "expected": True},
        })
        assert ok, msg

    def test_eq_false(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "eq", "args": ["1.2.3", "1.2.4"], "expected": False},
        })
        assert ok, msg

    # compare
    def test_compare_equal(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "compare", "args": ["1.2.3", "1.2.3"], "expected": 0},
        })
        assert ok, msg

    def test_compare_greater(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "compare", "args": ["2.0.0", "1.0.0"], "expected": 1},
        })
        assert ok, msg

    def test_compare_less(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "compare", "args": ["1.0.0", "2.0.0"], "expected": -1},
        })
        assert ok, msg

    # satisfies
    def test_satisfies_caret_in_range(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "satisfies", "args": ["1.2.3", "^1.0.0"], "expected": True},
        })
        assert ok, msg

    def test_satisfies_caret_out_of_range(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "satisfies", "args": ["2.0.0", "^1.0.0"], "expected": False},
        })
        assert ok, msg

    # major / minor / patch
    def test_major(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "major", "args": ["1.2.3"], "expected": 1},
        })
        assert ok, msg

    def test_minor(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "minor", "args": ["1.2.3"], "expected": 2},
        })
        assert ok, msg

    def test_patch(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "patch", "args": ["1.2.3"], "expected": 3},
        })
        assert ok, msg

    # inc
    def test_inc_major(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "inc", "args": ["1.2.3", "major"], "expected": "2.0.0"},
        })
        assert ok, msg

    def test_inc_minor(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "inc", "args": ["1.2.3", "minor"], "expected": "1.3.0"},
        })
        assert ok, msg

    def test_inc_patch(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "inc", "args": ["1.2.3", "patch"], "expected": "1.2.4"},
        })
        assert ok, msg

    # maxSatisfying / minSatisfying
    def test_max_satisfying(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "maxSatisfying",
                "args": [["1.0.0", "1.2.3", "2.0.0"], "^1.0.0"],
                "expected": "1.2.3",
            },
        })
        assert ok, msg

    def test_min_satisfying(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "minSatisfying",
                "args": [["1.0.0", "1.2.3", "2.0.0"], "^1.0.0"],
                "expected": "1.0.0",
            },
        })
        assert ok, msg

    def test_max_satisfying_no_match_returns_null(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "maxSatisfying",
                "args": [["3.0.0", "4.0.0"], "^1.0.0"],
                "expected": None,
            },
        })
        assert ok, msg

    # clean
    def test_clean(self, registry):
        ok, msg = registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "clean", "args": ["  =v1.5.0  "], "expected": "1.5.0"},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# SemverSpecIntegration
# ---------------------------------------------------------------------------

class TestSemverSpecIntegration:
    def test_all_invariants_pass(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend)
        failed = [r for r in results if not r.passed]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend)
        assert len(results) == 24

    def test_no_skips(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend)
        assert not any(r.skip_reason for r in results)

    def test_comparison_category(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend, filter_category="comparison")
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_range_category(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend, filter_category="range")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_fields_category(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend, filter_category="fields")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_increment_category(self, semver_spec, semver_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(semver_spec, semver_backend, filter_category="increment")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_all_ids_unique(self, semver_spec):
        ids = [inv["id"] for inv in semver_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# SemverCLI
# ---------------------------------------------------------------------------

class TestSemverCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(SEMVER_SPEC_PATH)])
        assert rc == 0

    def test_verbose_shows_pass(self, capsys):
        vb.main([str(SEMVER_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(SEMVER_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "semver.valid.valid_string" in out

    def test_filter_comparison(self, capsys):
        vb.main([str(SEMVER_SPEC_PATH), "--filter", "comparison", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        out_file = tmp_path / "results.json"
        vb.main([str(SEMVER_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert len(data) == 24
        assert all(r["passed"] for r in data)
