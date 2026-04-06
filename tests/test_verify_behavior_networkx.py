"""
Tests for the networkx Z-layer behavioral spec (networkx.zspec.zsdl).

Covers:
  - SpecLoader: loading networkx spec via python_module backend
  - python_call_eq handler with networkx-specific patterns (method: on graph instances)
  - InvariantRunner integration: all 14 invariants pass
  - CLI: verify-behavior runs networkx.zspec.json end-to-end

Categories verified:
  version (2)        — __version__ is a str containing a dot
  graph (4)          — Graph() and path_graph(4) node/edge counts
  complete_graph (2) — complete_graph(3) node/edge counts
  directed (2)       — DiGraph/Graph is_directed() via instance method
  algorithms (4)     — density/is_connected/is_directed/shortest_path __name__ checks
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

NETWORKX_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "networkx.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def networkx_spec():
    return vb.SpecLoader().load(NETWORKX_SPEC_PATH)


@pytest.fixture(scope="module")
def networkx_mod(networkx_spec):
    return vb.LibraryLoader().load(networkx_spec["library"])


@pytest.fixture(scope="module")
def constants_map(networkx_spec):
    return vb.InvariantRunner().build_constants_map(networkx_spec["constants"])


@pytest.fixture(scope="module")
def registry(networkx_mod, constants_map):
    return vb.PatternRegistry(networkx_mod, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader / module loader
# ---------------------------------------------------------------------------

class TestNetworkxSpecLoader:
    def test_loads_networkx_spec(self, networkx_spec):
        assert isinstance(networkx_spec, dict)

    def test_all_required_sections_present(self, networkx_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in networkx_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, networkx_spec):
        assert networkx_spec["library"]["backend"] == "python_module"

    def test_module_name_is_networkx(self, networkx_spec):
        assert networkx_spec["library"]["module_name"] == "networkx"

    def test_loads_networkx_module(self, networkx_mod):
        import networkx as nx
        assert networkx_mod is nx

    def test_all_invariant_kinds_known(self, networkx_spec):
        for inv in networkx_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, networkx_spec):
        ids = [inv["id"] for inv in networkx_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version — __version__ is a string containing a dot
# ---------------------------------------------------------------------------

class TestNetworkxVersion:
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

    def test_version_wrong_class_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__class__.__name__.__eq__",
                "args": ["int"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# graph — empty Graph and path_graph node/edge counts
# ---------------------------------------------------------------------------

class TestNetworkxGraph:
    def test_empty_graph_nodes(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Graph",
                "args": [],
                "method": "number_of_nodes",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_empty_graph_edges(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Graph",
                "args": [],
                "method": "number_of_edges",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_path4_nodes(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "path_graph",
                "args": [4],
                "method": "number_of_nodes",
                "expected": 4,
            },
        })
        assert ok, msg

    def test_path4_edges(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "path_graph",
                "args": [4],
                "method": "number_of_edges",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_path4_wrong_node_count_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "path_graph",
                "args": [4],
                "method": "number_of_nodes",
                "expected": 99,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# complete_graph — K3 node and edge counts
# ---------------------------------------------------------------------------

class TestNetworkxCompleteGraph:
    def test_complete3_nodes(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "complete_graph",
                "args": [3],
                "method": "number_of_nodes",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_complete3_edges(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "complete_graph",
                "args": [3],
                "method": "number_of_edges",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_complete3_wrong_edges_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "complete_graph",
                "args": [3],
                "method": "number_of_edges",
                "expected": 6,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# directed — is_directed() via instance method
# ---------------------------------------------------------------------------

class TestNetworkxDirected:
    def test_digraph_is_directed(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "DiGraph",
                "args": [],
                "method": "is_directed",
                "expected": True,
            },
        })
        assert ok, msg

    def test_graph_not_directed(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Graph",
                "args": [],
                "method": "is_directed",
                "expected": False,
            },
        })
        assert ok, msg

    def test_digraph_is_directed_wrong_expected_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "DiGraph",
                "args": [],
                "method": "is_directed",
                "expected": False,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# algorithms — module-level function __name__ checks
# ---------------------------------------------------------------------------

class TestNetworkxAlgorithms:
    def test_density_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "density.__name__.__eq__",
                "args": ["density"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_is_connected_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "is_connected.__name__.__eq__",
                "args": ["is_connected"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_is_directed_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "is_directed.__name__.__eq__",
                "args": ["is_directed"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_shortest_path_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "shortest_path.__name__.__eq__",
                "args": ["shortest_path"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrong_function_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "density.__name__.__eq__",
                "args": ["not_density"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 14 networkx invariants must pass
# ---------------------------------------------------------------------------

class TestNetworkxAll:
    def test_all_pass(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod)
        assert len(results) == 14

    def test_no_skips(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_graph_category(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod, filter_category="graph")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_complete_graph_category(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod, filter_category="complete_graph")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_directed_category(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod, filter_category="directed")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_algorithms_category(self, networkx_spec, networkx_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(networkx_spec, networkx_mod, filter_category="algorithms")
        assert len(results) == 4
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestNetworkxCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(NETWORKX_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(NETWORKX_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "14 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(NETWORKX_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "networkx.version" in out
        assert "networkx.graph" in out

    def test_filter_flag(self, capsys):
        vb.main([str(NETWORKX_SPEC_PATH), "--filter", "graph", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(NETWORKX_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 14
        assert all(r["passed"] for r in data)
