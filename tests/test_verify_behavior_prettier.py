"""
Tests for the prettier Z-layer behavioral spec.

Organized as:
  - PrettierBackend: LibraryLoader loading node + prettier module
  - PrettierCLIStdout: unit tests for the cli_stdout_contains handler
  - PrettierSpecIntegration: all invariants pass end-to-end
  - PrettierCLI: main() exit-code and --list / --verbose / --json-out flags

Note: prettier 3.x is async-first; all formatting/check invariants use
cli_stdout_contains with inline async IIFE node scripts.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PRETTIER_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "prettier.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def prettier_spec():
    return vb.SpecLoader().load(PRETTIER_SPEC_PATH)


@pytest.fixture(scope="module")
def prettier_backend(prettier_spec):
    try:
        return vb.LibraryLoader().load(prettier_spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"prettier backend not available: {exc}")


@pytest.fixture(scope="module")
def registry(prettier_backend):
    return vb.PatternRegistry(prettier_backend, {})


# ---------------------------------------------------------------------------
# PrettierBackend
# ---------------------------------------------------------------------------

class TestPrettierBackend:
    def test_loads_as_cli_backend(self, prettier_backend):
        assert isinstance(prettier_backend, vb.CLIBackend)

    def test_command_is_node(self, prettier_backend):
        assert "node" in prettier_backend.command

    def test_module_name_is_prettier(self, prettier_backend):
        assert prettier_backend.module_name == "prettier"

    def test_not_esm(self, prettier_backend):
        assert not getattr(prettier_backend, "esm", False)

    def test_spec_backend_field(self, prettier_spec):
        assert prettier_spec["library"]["backend"] == "cli"

    def test_spec_module_name_field(self, prettier_spec):
        assert prettier_spec["library"]["module_name"] == "prettier"

    def test_all_invariant_kinds_known(self, prettier_spec):
        for inv in prettier_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS


# ---------------------------------------------------------------------------
# PrettierCLIStdout — unit tests via cli_stdout_contains handler
# ---------------------------------------------------------------------------

class TestPrettierCLIStdout:
    def test_version_contains_dot(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["-e", "const p=require('prettier');process.stdout.write(p.version)"],
                "expected_substring": ".",
            },
        })
        assert ok, msg

    def test_format_babel_contains_const(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": [
                    "-e",
                    "(async()=>{const p=require('prettier');const r=await p.format('const x=1',{parser:'babel'});process.stdout.write(r)})()",
                ],
                "expected_substring": "const x = 1",
            },
        })
        assert ok, msg

    def test_format_css_contains_color(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": [
                    "-e",
                    "(async()=>{const p=require('prettier');const r=await p.format('.foo{color:red}',{parser:'css'});process.stdout.write(r)})()",
                ],
                "expected_substring": "color: red",
            },
        })
        assert ok, msg

    def test_check_already_formatted(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": [
                    "-e",
                    "(async()=>{const p=require('prettier');const r=await p.check('const x = 1;\\n',{parser:'babel'});process.stdout.write(String(r))})()",
                ],
                "expected_substring": "true",
            },
        })
        assert ok, msg

    def test_check_needs_formatting(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": [
                    "-e",
                    "(async()=>{const p=require('prettier');const r=await p.check('const x=1',{parser:'babel'});process.stdout.write(String(r))})()",
                ],
                "expected_substring": "false",
            },
        })
        assert ok, msg

    def test_format_is_function(self, registry):
        ok, msg = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["-e", "const p=require('prettier');process.stdout.write(typeof p.format)"],
                "expected_substring": "function",
            },
        })
        assert ok, msg

    def test_wrong_substring_fails(self, registry):
        ok, _ = registry.run({
            "kind": "cli_stdout_contains",
            "spec": {
                "args": ["-e", "const p=require('prettier');process.stdout.write(p.version)"],
                "expected_substring": "NOTAVERSION",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# PrettierSpecIntegration
# ---------------------------------------------------------------------------

class TestPrettierSpecIntegration:
    def test_all_invariants_pass(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend)
        failed = [r for r in results if not r.passed]
        assert not failed, [f"{r.inv_id}: {r.message}" for r in failed]

    def test_invariant_count(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend)
        assert len(results) == 25

    def test_no_skips(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend)
        assert not any(r.skip_reason for r in results)

    def test_version_category(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_api_category(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend, filter_category="api")
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_format_category(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend, filter_category="format")
        assert len(results) == 14
        assert all(r.passed for r in results)

    def test_check_category(self, prettier_spec, prettier_backend):
        runner = vb.InvariantRunner()
        results = runner.run_all(prettier_spec, prettier_backend, filter_category="check")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_all_ids_unique(self, prettier_spec):
        ids = [inv["id"] for inv in prettier_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# PrettierCLI
# ---------------------------------------------------------------------------

class TestPrettierCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PRETTIER_SPEC_PATH)])
        assert rc == 0

    def test_verbose_shows_pass(self, capsys):
        vb.main([str(PRETTIER_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PRETTIER_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "prettier.version.contains_dot" in out

    def test_filter_format(self, capsys):
        vb.main([str(PRETTIER_SPEC_PATH), "--filter", "format", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        out_file = tmp_path / "results.json"
        vb.main([str(PRETTIER_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert len(data) == 25
        assert all(r["passed"] for r in data)
