"""
Tests for the CLI/subprocess backend and CLI pattern handlers
in tools/verify_behavior.py, plus openssl.zspec.json integration.

Organized as:
  - CLIBackend / LibraryLoader: loading openssl via the cli backend
  - CLIBackend helpers and _cli_run
  - cli_exits_with: exit code checking
  - cli_stdout_eq: exact stdout comparison
  - cli_stdout_contains: substring checking
  - cli_stdout_matches: regex matching
  - cli_stderr_contains: stderr substring checking
  - openssl spec integration: all 16 invariants pass
  - CLI end-to-end: verify-behavior runs openssl.zspec.json
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

OPENSSL_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "openssl.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def openssl_spec():
    return vb.SpecLoader().load(OPENSSL_SPEC_PATH)


@pytest.fixture(scope="module")
def openssl_backend(openssl_spec):
    try:
        return vb.LibraryLoader().load(openssl_spec["library"])
    except vb.LibraryNotFoundError:
        pytest.skip("openssl not found in PATH")


@pytest.fixture(scope="module")
def registry(openssl_backend):
    return vb.PatternRegistry(openssl_backend, {})


@pytest.fixture(scope="module")
def true_backend():
    """CLIBackend pointing at /bin/true (always exits 0, no output)."""
    import shutil
    cmd = shutil.which("true")
    if not cmd:
        pytest.skip("/bin/true not found")
    return vb.CLIBackend(command=cmd)


@pytest.fixture(scope="module")
def false_backend():
    """CLIBackend pointing at /bin/false (always exits 1, no output)."""
    import shutil
    cmd = shutil.which("false")
    if not cmd:
        pytest.skip("/bin/false not found")
    return vb.CLIBackend(command=cmd)


@pytest.fixture(scope="module")
def echo_backend():
    """CLIBackend pointing at /bin/echo."""
    import shutil
    cmd = shutil.which("echo")
    if not cmd:
        pytest.skip("/bin/echo not found")
    return vb.CLIBackend(command=cmd)


# ---------------------------------------------------------------------------
# CLIBackend and LibraryLoader
# ---------------------------------------------------------------------------

class TestCLIBackendLoader:
    def test_loads_openssl(self, openssl_backend):
        assert isinstance(openssl_backend, vb.CLIBackend)
        assert "openssl" in openssl_backend.command

    def test_backend_field_is_cli(self, openssl_spec):
        assert openssl_spec["library"]["backend"] == "cli"

    def test_raises_on_nonexistent_command(self):
        with pytest.raises(vb.LibraryNotFoundError, match="not found in PATH"):
            vb.LibraryLoader().load({
                "backend": "cli",
                "command": "no_such_command_xyz_abc",
            })

    def test_cli_backend_has_command_attr(self, openssl_backend):
        assert hasattr(openssl_backend, "command")
        assert isinstance(openssl_backend.command, str)

    def test_all_invariant_kinds_known(self, openssl_spec):
        for inv in openssl_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


# ---------------------------------------------------------------------------
# cli_exits_with
# ---------------------------------------------------------------------------

class TestCliExitsWith:
    def test_true_exits_zero(self, true_backend):
        reg = vb.PatternRegistry(true_backend, {})
        ok, msg = reg.run({
            "kind": "cli_exits_with",
            "spec": {"expected_exit": 0},
        })
        assert ok, msg

    def test_false_exits_one(self, false_backend):
        reg = vb.PatternRegistry(false_backend, {})
        ok, msg = reg.run({
            "kind": "cli_exits_with",
            "spec": {"expected_exit": 1},
        })
        assert ok, msg

    def test_fails_when_exit_code_wrong(self, true_backend):
        reg = vb.PatternRegistry(true_backend, {})
        ok, msg = reg.run({
            "kind": "cli_exits_with",
            "spec": {"expected_exit": 1},
        })
        assert not ok

    def test_openssl_version_exits_zero(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {"args": ["version"], "expected_exit": 0},
        })
        assert ok, msg

    def test_openssl_bad_subcommand_reports_error(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stderr_contains",
            "spec": {"args": ["no_such_cmd_xyz"], "expected_substring": "no_such_cmd_xyz"},
        })
        assert ok, msg

    def test_openssl_dgst_sha256_exits_zero(self, registry):
        ok, msg = registry.run({
            "kind": "cli_exits_with",
            "spec": {
                "args": ["dgst", "-sha256"],
                "stdin_b64": "YWJj",
                "expected_exit": 0,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# cli_stdout_eq
# ---------------------------------------------------------------------------

class TestCliStdoutEq:
    def test_echo_hello(self, echo_backend):
        reg = vb.PatternRegistry(echo_backend, {})
        ok, msg = reg.run({
            "kind": "cli_stdout_eq",
            "spec": {"args": ["hello"], "expected": "hello"},
        })
        assert ok, msg

    def test_echo_strips_trailing_newline(self, echo_backend):
        """echo appends a newline; cli_stdout_eq should strip it."""
        reg = vb.PatternRegistry(echo_backend, {})
        ok, msg = reg.run({
            "kind": "cli_stdout_eq",
            "spec": {"args": ["hello"], "expected": "hello"},
        })
        assert ok, msg

    def test_fails_on_wrong_expected(self, echo_backend):
        reg = vb.PatternRegistry(echo_backend, {})
        ok, msg = reg.run({
            "kind": "cli_stdout_eq",
            "spec": {"args": ["hello"], "expected": "world"},
        })
        assert not ok

    def test_echo_empty_args(self, echo_backend):
        reg = vb.PatternRegistry(echo_backend, {})
        ok, msg = reg.run({
            "kind": "cli_stdout_eq",
            "spec": {"args": [], "expected": ""},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# cli_stdout_contains
# ---------------------------------------------------------------------------

class TestCliStdoutContains:
    def test_openssl_version_contains_ssl(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["version"], "expected_substring": "SSL"},
        })
        assert ok, msg

    def test_openssl_sha256_abc_contains_hash(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["dgst", "-sha256"],
                "stdin_b64": "YWJj",
                "expected_substring": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            },
        })
        assert ok, msg

    def test_openssl_sha256_empty_input(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["dgst", "-sha256"],
                "stdin_b64": "",
                "expected_substring": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
        })
        assert ok, msg

    def test_openssl_md5_abc(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["dgst", "-md5"],
                "stdin_b64": "YWJj",
                "expected_substring": "900150983cd24fb0d6963f7d28e17f72",
            },
        })
        assert ok, msg

    def test_fails_on_wrong_substring(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["dgst", "-sha256"],
                "stdin_b64": "YWJj",
                "expected_substring": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        })
        assert not ok

    def test_echo_contains_word(self, echo_backend):
        reg = vb.PatternRegistry(echo_backend, {})
        ok, msg = reg.run({
            "kind": "cli_stdout_contains",
            "spec": {"args": ["hello world"], "expected_substring": "world"},
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# cli_stdout_matches
# ---------------------------------------------------------------------------

class TestCliStdoutMatches:
    def test_openssl_sha256_raw_format(self, registry):
        """openssl dgst -sha256 -r outputs '<hexdigest> *stdin'."""
        ok, msg = registry.run({
            "kind": "cli_stdout_matches",
            "spec": {
                "args": ["dgst", "-sha256", "-r"],
                "stdin_b64": "YWJj",
                "pattern": r"^ba7816bf[0-9a-f]+ [* ]",
            },
        })
        assert ok, msg

    def test_openssl_version_matches_version_pattern(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_matches",
            "spec": {
                "args": ["version"],
                "pattern": r"(OpenSSL|LibreSSL)\s+\d+\.\d+",
            },
        })
        assert ok, msg

    def test_fails_on_non_matching_pattern(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_matches",
            "spec": {
                "args": ["version"],
                "pattern": r"^ZZZZZZ_IMPOSSIBLE_PREFIX",
            },
        })
        assert not ok

    def test_multiline_flag(self, echo_backend):
        reg = vb.PatternRegistry(echo_backend, {})
        ok, msg = reg.run({
            "kind": "cli_stdout_matches",
            "spec": {
                "args": ["hello"],
                "pattern": r"^hello$",
                "multiline": True,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# cli_stderr_contains
# ---------------------------------------------------------------------------

class TestCliStderrContains:
    def test_openssl_bad_subcommand_stderr(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stderr_contains",
            "spec": {
                "args": ["no_such_subcommand_xyz"],
                "expected_substring": "command",
            },
        })
        assert ok, msg

    def test_fails_when_substring_not_in_stderr(self, registry):
        # openssl version doesn't write to stderr normally
        ok, msg = registry.run({
            "kind": "cli_stderr_contains",
            "spec": {
                "args": ["version"],
                "expected_substring": "ZZZZZZ_IMPOSSIBLE_SUBSTRING",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# openssl spec integration
# ---------------------------------------------------------------------------

class TestOpensslSpecIntegration:
    def test_all_invariants_pass(self, openssl_spec, openssl_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(openssl_spec, openssl_backend)
        failed = [r for r in results if not r.passed]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, openssl_spec, openssl_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(openssl_spec, openssl_backend)
        assert len(results) == 16

    def test_no_skips(self, openssl_spec, openssl_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(openssl_spec, openssl_backend)
        assert not any(r.skip_reason for r in results)

    def test_sha256_category(self, openssl_spec, openssl_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(openssl_spec, openssl_backend, filter_category="sha256_vector")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_md5_category(self, openssl_spec, openssl_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(openssl_spec, openssl_backend, filter_category="md5_vector")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_error_category(self, openssl_spec, openssl_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(openssl_spec, openssl_backend, filter_category="error")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_all_ids_unique(self, openssl_spec):
        ids = [inv["id"] for inv in openssl_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_all_kinds_known(self, openssl_spec):
        for inv in openssl_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS

    def test_cross_spec_sha256_abc_matches_hashlib(self):
        """The SHA-256('abc') value in openssl.zspec.json must equal the value
        in hashlib.zspec.json — this is the interoperability invariant."""
        hashlib_spec = vb.SpecLoader().load(REPO_ROOT / "_build" / "zspecs" / "hashlib.zspec.json")
        openssl_spec  = vb.SpecLoader().load(OPENSSL_SPEC_PATH)

        def get_hash(spec, inv_id):
            for inv in spec["invariants"]:
                if inv["id"] == inv_id:
                    return (
                        inv["spec"].get("expected_hex") or
                        inv["spec"].get("expected_substring")
                    )
            return None

        hl = get_hash(hashlib_spec, "hashlib.sha256.abc")
        ssl = get_hash(openssl_spec, "openssl.dgst.sha256.abc")
        assert hl and ssl, "invariants not found"
        assert hl == ssl, f"hashlib={hl!r} != openssl={ssl!r}"


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestOpensslCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(OPENSSL_SPEC_PATH)])
        assert rc == 0

    def test_verbose_shows_all(self, capsys):
        vb.main([str(OPENSSL_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "16 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(OPENSSL_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "openssl.version.exits_zero" in out

    def test_filter_sha256(self, capsys):
        vb.main([str(OPENSSL_SPEC_PATH), "--filter", "sha256_vector", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert len(data) == 16
        assert all(r["passed"] for r in data)


# ---------------------------------------------------------------------------
# TestBaselineDiff
# ---------------------------------------------------------------------------

class TestBaselineDiff:
    """Tests for --baseline / --diff mode in verify_behavior.main()."""

    def _write_baseline(self, tmp_path, results: list[dict]) -> Path:
        p = tmp_path / "baseline.json"
        p.write_text(json.dumps(results), encoding="utf-8")
        return p

    def test_baseline_identical_no_regressions(self, tmp_path, capsys):
        """Running against its own output reports no changes and exits 0."""
        out = tmp_path / "baseline.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out)])
        rc = vb.main([str(OPENSSL_SPEC_PATH), "--baseline", str(out)])
        assert rc == 0
        captured = capsys.readouterr().out
        assert "no changes" in captured

    def test_baseline_fix_detected(self, tmp_path, capsys):
        """An invariant that was failing in the baseline but passes now is a fix."""
        # Build real current results first
        out = tmp_path / "current.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out)])
        current = json.loads(out.read_text())

        # Simulate baseline where first entry was failing
        baseline = [dict(r) for r in current]
        baseline[0]["passed"] = False
        baseline[0]["message"] = "old failure"
        bl_file = self._write_baseline(tmp_path, baseline)

        rc = vb.main([str(OPENSSL_SPEC_PATH), "--baseline", str(bl_file)])
        assert rc == 0  # fix, not regression
        captured = capsys.readouterr().out
        assert "FIXED" in captured

    def test_baseline_regression_exits_1(self, tmp_path, capsys):
        """An invariant that was passing in the baseline but fails now is a regression."""
        out = tmp_path / "current.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out)])
        current = json.loads(out.read_text())

        # Simulate baseline where first entry was passing (it is) but we mark
        # the current as failing by injecting a modified entry into a fake baseline
        # where a formerly-failing invariant is now passing — test via _diff_results
        # directly to avoid actually breaking a spec.
        passing_baseline = [dict(r) for r in current]
        # Mark one as "was passing" in baseline, but make current show it as failing
        faked_current = [dict(r) for r in current]
        faked_current[0]["passed"] = False
        faked_current[0]["message"] = "now failing"

        bl_file = self._write_baseline(tmp_path, passing_baseline)
        regressions = vb._diff_results(bl_file, faked_current)
        assert regressions == 1

    def test_baseline_added_invariants(self, tmp_path, capsys):
        """New invariants (present in current but not baseline) are reported."""
        out = tmp_path / "current.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out)])
        current = json.loads(out.read_text())

        # Baseline is missing the last entry
        baseline = current[:-1]
        bl_file = self._write_baseline(tmp_path, baseline)

        rc = vb.main([str(OPENSSL_SPEC_PATH), "--baseline", str(bl_file)])
        assert rc == 0  # added entries are not regressions
        captured = capsys.readouterr().out
        assert "New invariants" in captured

    def test_baseline_removed_invariants(self, tmp_path, capsys):
        """Invariants in baseline but not in current are reported as removed."""
        out = tmp_path / "current.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out)])
        current = json.loads(out.read_text())

        # Baseline has an extra entry that no longer exists
        baseline = list(current) + [
            {"id": "openssl.removed.test", "passed": True, "message": "old", "skip_reason": None}
        ]
        bl_file = self._write_baseline(tmp_path, baseline)

        rc = vb.main([str(OPENSSL_SPEC_PATH), "--baseline", str(bl_file)])
        assert rc == 0
        captured = capsys.readouterr().out
        assert "Removed invariants" in captured

    def test_baseline_missing_file_exits_nonzero(self, tmp_path):
        """A missing baseline file should exit non-zero."""
        missing = tmp_path / "no_such_file.json"
        rc = vb.main([str(OPENSSL_SPEC_PATH), "--baseline", str(missing)])
        assert rc != 0

    def test_baseline_invalid_json_exits_nonzero(self, tmp_path):
        """A baseline file with invalid JSON should exit non-zero."""
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        rc = vb.main([str(OPENSSL_SPEC_PATH), "--baseline", str(bad)])
        assert rc != 0

    def test_diff_results_direct_no_changes(self, tmp_path):
        """_diff_results returns 0 when baseline and current are identical."""
        out = tmp_path / "current.json"
        vb.main([str(OPENSSL_SPEC_PATH), "--json-out", str(out)])
        current = json.loads(out.read_text())
        bl_file = self._write_baseline(tmp_path, current)
        assert vb._diff_results(bl_file, current) == 0

    def test_diff_results_counts_regressions(self, tmp_path):
        """_diff_results returns the correct regression count."""
        current = [
            {"id": "a", "passed": False, "message": "fail", "skip_reason": None},
            {"id": "b", "passed": False, "message": "fail", "skip_reason": None},
            {"id": "c", "passed": True,  "message": "ok",   "skip_reason": None},
        ]
        baseline = [
            {"id": "a", "passed": True, "message": "ok", "skip_reason": None},
            {"id": "b", "passed": True, "message": "ok", "skip_reason": None},
            {"id": "c", "passed": True, "message": "ok", "skip_reason": None},
        ]
        bl_file = self._write_baseline(tmp_path, baseline)
        assert vb._diff_results(bl_file, current) == 2
