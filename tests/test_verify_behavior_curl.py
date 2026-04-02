"""
Tests for the curl Z-layer spec.

All invariants in curl.zspec.json are offline-safe: they use --version, --help,
file://, or connect to localhost on a port guaranteed to refuse connections.
No external network access is required.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT      = Path(__file__).resolve().parent.parent
CURL_SPEC_PATH = REPO_ROOT / "zspecs" / "curl.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def curl_spec():
    return vb.SpecLoader().load(CURL_SPEC_PATH)


@pytest.fixture(scope="module")
def curl_backend(curl_spec):
    try:
        return vb.LibraryLoader().load(curl_spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"curl not available: {exc}")


@pytest.fixture(scope="module")
def registry(curl_backend):
    return vb.PatternRegistry(curl_backend, {})


# ---------------------------------------------------------------------------
# TestCurlBackend
# ---------------------------------------------------------------------------

class TestCurlBackend:
    def test_loads_as_cli_backend(self, curl_backend):
        assert isinstance(curl_backend, vb.CLIBackend)

    def test_command_contains_curl(self, curl_backend):
        assert "curl" in curl_backend.command

    def test_no_module_name(self, curl_backend):
        assert curl_backend.module_name is None

    def test_spec_backend_is_cli(self, curl_spec):
        assert curl_spec["library"]["backend"] == "cli"

    def test_spec_command_is_curl(self, curl_spec):
        assert curl_spec["library"]["command"] == "curl"


# ---------------------------------------------------------------------------
# TestHealth
# ---------------------------------------------------------------------------

class TestHealth:
    def test_version_exits_0(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {"args": ["--version"], "expected_exit": 0},
        })
        assert ok, msg

    def test_version_contains_curl(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["--version"], "expected_substring": "curl"},
        })
        assert ok, msg

    def test_version_contains_libcurl(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["--version"], "expected_substring": "libcurl"},
        })
        assert ok, msg

    def test_version_contains_protocols(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["--version"], "expected_substring": "Protocols:"},
        })
        assert ok, msg

    def test_version_contains_http(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["--version"], "expected_substring": " http"},
        })
        assert ok, msg

    def test_help_exits_0(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {"args": ["--help"], "expected_exit": 0},
        })
        assert ok, msg

    def test_help_contains_usage(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["--help"], "expected_substring": "Usage:"},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestFileProtocol
# ---------------------------------------------------------------------------

class TestFileProtocol:
    def test_read_etc_hosts_exits_0(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {"args": ["--silent", "--output", "/dev/null", "file:///etc/hosts"],
                     "expected_exit": 0},
        })
        assert ok, msg

    def test_read_etc_hosts_contains_localhost(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["--silent", "file:///etc/hosts"],
                     "expected_substring": "localhost"},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestErrorBehavior
# ---------------------------------------------------------------------------

class TestErrorBehavior:
    def test_unsupported_protocol_exits_1(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {"args": ["--silent", "badproto://example.com"], "expected_exit": 1},
        })
        assert ok, msg

    def test_unsupported_protocol_stderr_contains_protocol(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stderr_contains",
            "spec": {"args": ["badproto://example.com"], "expected_substring": "Protocol"},
        })
        assert ok, msg

    def test_connection_refused_exits_7(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {"args": ["--silent", "--max-time", "2", "http://localhost:19999"],
                     "expected_exit": 7,
                     "timeout": 5},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestCurlSpecIntegration
# ---------------------------------------------------------------------------

class TestCurlSpecIntegration:
    def test_all_invariants_pass(self, curl_spec, curl_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(curl_spec, curl_backend)
        failed  = [r for r in results if not r.passed and not r.skip_reason]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, curl_spec, curl_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(curl_spec, curl_backend)
        assert len(results) == 12

    def test_no_skips(self, curl_spec, curl_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(curl_spec, curl_backend)
        assert not any(r.skip_reason for r in results)

    def test_health_category(self, curl_spec, curl_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(curl_spec, curl_backend, filter_category="health")
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_file_protocol_category(self, curl_spec, curl_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(curl_spec, curl_backend, filter_category="file_protocol")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_error_behavior_category(self, curl_spec, curl_backend):
        runner  = vb.InvariantRunner()
        results = runner.run_all(curl_spec, curl_backend, filter_category="error_behavior")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_all_ids_unique(self, curl_spec):
        ids = [inv["id"] for inv in curl_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_all_kinds_known(self, curl_spec):
        for inv in curl_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


# ---------------------------------------------------------------------------
# TestCurlCLI
# ---------------------------------------------------------------------------

class TestCurlCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(CURL_SPEC_PATH)])
        assert rc == 0

    def test_verbose_shows_pass(self, capsys):
        vb.main([str(CURL_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(CURL_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "curl.version.exits_0" in out

    def test_json_out(self, tmp_path):
        out_file = tmp_path / "results.json"
        vb.main([str(CURL_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert len(data) == 12
        assert all(r["passed"] for r in data)
