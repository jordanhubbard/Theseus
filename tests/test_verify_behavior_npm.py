"""
Tests for npm Z-layer specs: uuid and minimist.

uuid.zspec.json:  validate(), version() — fixed UUID test vectors
minimist.zspec.json: direct module call (function: null) — argv parsing

Also tests the compact-JSON comparison fix in _node_module_call_eq so that
JSON.stringify output (no spaces) correctly matches json.dumps expected values.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT       = Path(__file__).resolve().parent.parent
UUID_SPEC_PATH  = REPO_ROOT / "_build" / "zspecs" / "uuid.zspec.json"
MINI_SPEC_PATH  = REPO_ROOT / "_build" / "zspecs" / "minimist.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _load_backend(spec_path: Path):
    spec = vb.SpecLoader().load(spec_path)
    try:
        return spec, vb.LibraryLoader().load(spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"backend not available: {exc}")


@pytest.fixture(scope="module")
def uuid_spec_and_backend():
    return _load_backend(UUID_SPEC_PATH)


@pytest.fixture(scope="module")
def uuid_spec(uuid_spec_and_backend):
    return uuid_spec_and_backend[0]


@pytest.fixture(scope="module")
def uuid_backend(uuid_spec_and_backend):
    return uuid_spec_and_backend[1]


@pytest.fixture(scope="module")
def uuid_registry(uuid_backend):
    return vb.PatternRegistry(uuid_backend, {})


@pytest.fixture(scope="module")
def mini_spec_and_backend():
    return _load_backend(MINI_SPEC_PATH)


@pytest.fixture(scope="module")
def mini_spec(mini_spec_and_backend):
    return mini_spec_and_backend[0]


@pytest.fixture(scope="module")
def mini_backend(mini_spec_and_backend):
    return mini_spec_and_backend[1]


@pytest.fixture(scope="module")
def mini_registry(mini_backend):
    return vb.PatternRegistry(mini_backend, {})


# ---------------------------------------------------------------------------
# TestUuidBackend
# ---------------------------------------------------------------------------

class TestUuidBackend:
    def test_is_cli_backend(self, uuid_backend):
        assert isinstance(uuid_backend, vb.CLIBackend)

    def test_module_name_is_uuid(self, uuid_backend):
        assert uuid_backend.module_name == "uuid"

    def test_spec_backend_field(self, uuid_spec):
        assert uuid_spec["library"]["backend"] == "cli"

    def test_all_kinds_known(self, uuid_spec):
        for inv in uuid_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


# ---------------------------------------------------------------------------
# TestUuidValidate
# ---------------------------------------------------------------------------

class TestUuidValidate:
    def test_valid_uuid_returns_true(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "validate",
                "args": ["550e8400-e29b-41d4-a716-446655440000"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_nil_uuid_validates(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "validate",
                "args": ["00000000-0000-0000-0000-000000000000"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_garbage_does_not_validate(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "validate", "args": ["not-a-uuid"], "expected": False},
        })
        assert ok, msg

    def test_empty_string_does_not_validate(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": "validate", "args": [""], "expected": False},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestUuidVersion
# ---------------------------------------------------------------------------

class TestUuidVersion:
    def test_version_v1(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "version",
                "args": ["6ba7b810-9dad-11d1-80b4-00c04fd430c8"],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_version_v4(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "version",
                "args": ["f47ac10b-58cc-4372-a567-0e02b2c3d479"],
                "expected": 4,
            },
        })
        assert ok, msg

    def test_nil_is_version_0(self, uuid_registry):
        ok, msg = uuid_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": "version",
                "args": ["00000000-0000-0000-0000-000000000000"],
                "expected": 0,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestUuidSpecIntegration
# ---------------------------------------------------------------------------

class TestUuidSpecIntegration:
    def test_all_invariants_pass(self, uuid_spec, uuid_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(uuid_spec, uuid_backend)
        failed  = [r for r in results if not r.passed and not r.skip_reason]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, uuid_spec, uuid_backend):
        results = vb.InvariantRunner().run_all(uuid_spec, uuid_backend)
        assert len(results) == 8

    def test_cli_exit_0(self):
        assert vb.main([str(UUID_SPEC_PATH)]) == 0


# ---------------------------------------------------------------------------
# TestMinimistBackend
# ---------------------------------------------------------------------------

class TestMinimistBackend:
    def test_is_cli_backend(self, mini_backend):
        assert isinstance(mini_backend, vb.CLIBackend)

    def test_module_name_is_minimist(self, mini_backend):
        assert mini_backend.module_name == "minimist"

    def test_all_kinds_known(self, mini_spec):
        for inv in mini_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS

    def test_function_is_null_in_spec(self, mini_spec):
        """All minimist invariants call the module directly (function: null)."""
        for inv in mini_spec["invariants"]:
            assert inv["spec"]["function"] is None


# ---------------------------------------------------------------------------
# TestMinimistParsing
# ---------------------------------------------------------------------------

class TestMinimistParsing:
    def _run(self, registry, args, expected):
        return registry.run({
            "kind": "node_module_call_eq",
            "spec": {"function": None, "args": [args], "expected": expected},
        })

    def test_long_flag_with_value(self, mini_registry):
        ok, msg = self._run(mini_registry, ["--foo", "bar"], {"_": [], "foo": "bar"})
        assert ok, msg

    def test_long_flag_equals_syntax(self, mini_registry):
        ok, msg = self._run(mini_registry, ["--foo=bar"], {"_": [], "foo": "bar"})
        assert ok, msg

    def test_long_boolean_flag(self, mini_registry):
        ok, msg = self._run(mini_registry, ["--flag"], {"_": [], "flag": True})
        assert ok, msg

    def test_short_boolean_flags(self, mini_registry):
        ok, msg = self._run(mini_registry, ["-x", "-y"], {"_": [], "x": True, "y": True})
        assert ok, msg

    def test_short_combined_flags(self, mini_registry):
        ok, msg = self._run(mini_registry, ["-xy"], {"_": [], "x": True, "y": True})
        assert ok, msg

    def test_positional_args(self, mini_registry):
        ok, msg = self._run(mini_registry, ["a", "b", "c"], {"_": ["a", "b", "c"]})
        assert ok, msg

    def test_double_dash_separator(self, mini_registry):
        ok, msg = self._run(mini_registry, ["a", "b", "--", "c"], {"_": ["a", "b", "c"]})
        assert ok, msg

    def test_numeric_coercion(self, mini_registry):
        ok, msg = self._run(mini_registry, ["--num", "42"], {"_": [], "num": 42})
        assert ok, msg

    def test_empty_argv(self, mini_registry):
        ok, msg = self._run(mini_registry, [], {"_": []})
        assert ok, msg

    def test_wrong_expected_fails(self, mini_registry):
        ok, _ = self._run(mini_registry, ["--foo", "bar"], {"_": [], "foo": "wrong"})
        assert not ok


# ---------------------------------------------------------------------------
# TestMinimistSpecIntegration
# ---------------------------------------------------------------------------

class TestMinimistSpecIntegration:
    def test_all_invariants_pass(self, mini_spec, mini_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(mini_spec, mini_backend)
        failed  = [r for r in results if not r.passed and not r.skip_reason]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, mini_spec, mini_backend):
        results = vb.InvariantRunner().run_all(mini_spec, mini_backend)
        assert len(results) == 9

    def test_cli_exit_0(self):
        assert vb.main([str(MINI_SPEC_PATH)]) == 0

    def test_json_out(self, tmp_path):
        out = tmp_path / "results.json"
        vb.main([str(MINI_SPEC_PATH), "--json-out", str(out)])
        data = json.loads(out.read_text())
        assert all(r["passed"] for r in data)


# ---------------------------------------------------------------------------
# TestCompactJsonComparison
# ---------------------------------------------------------------------------

class TestCompactJsonComparison:
    """
    Regression tests for the compact-separator fix in _node_module_call_eq.

    JSON.stringify produces no spaces ({"a":1}), while json.dumps defaults to
    spaces after separators ({"a": 1}). The handler must use compact separators
    on the expected side so the comparison works for object/array return values.
    """

    def test_object_expected_no_space_mismatch(self, mini_registry):
        """Object return value compares equal despite JSON formatting difference."""
        ok, msg = mini_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": None,
                "args": [["--a", "1", "--b", "2"]],
                "expected": {"_": [], "a": 1, "b": 2},
            },
        })
        assert ok, msg

    def test_nested_array_expected_no_space_mismatch(self, mini_registry):
        """Array within object compares equal."""
        ok, msg = mini_registry.run({
            "kind": "node_module_call_eq",
            "spec": {
                "function": None,
                "args": [["x", "y", "z"]],
                "expected": {"_": ["x", "y", "z"]},
            },
        })
        assert ok, msg
