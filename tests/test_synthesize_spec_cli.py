"""
Tests for tools/synthesize_spec.py CLI.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure tools/ is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "tools"))

import synthesize_spec as cli_mod
from theseus.synthesis.runner import SynthesisResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec_json(tmp_path: Path) -> Path:
    spec = {
        "schema_version": "0.2",
        "identity": {"canonical_name": "testlib"},
        "library": {"backend": "python_module", "module_name": "testlib"},
        "provenance": {"derived_from": [], "not_derived_from": [], "notes": []},
        "functions": {},
        "constants": {},
        "wire_formats": {},
        "error_model": {},
        "invariants": [
            {
                "id": "testlib.inv.0",
                "kind": "python_call_eq",
                "description": "test",
                "spec": {},
                "category": "basic",
            }
        ],
    }
    p = tmp_path / "testlib.zspec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return p


def _make_success_result() -> SynthesisResult:
    return SynthesisResult(
        canonical_name="testlib",
        backend_lang="python",
        status="success",
        model="claude-cli",
        attempted_at="2026-04-13T00:00:00Z",
        iterations=1,
        attempts=[],
        final_pass_count=1,
        final_fail_count=0,
        total_invariants=1,
        notes="Succeeded.",
        infeasible_reason=None,
        failed_invariant_details={},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCLIExitCodes:
    def test_exit_2_when_spec_not_found(self, tmp_path: Path) -> None:
        code = cli_mod.main([str(tmp_path / "nonexistent.zspec.json")])
        assert code == 2

    def test_exit_3_when_no_agent(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        with patch("theseus.agent.available", return_value=False):
            code = cli_mod.main([str(spec_path)])
        assert code == 3

    def test_exit_0_on_success(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        result = _make_success_result()
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            code = cli_mod.main([str(spec_path), "--no-annotate"])
        assert code == 0

    def test_exit_1_on_partial(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        result = _make_success_result()
        result.status = "partial"
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            code = cli_mod.main([str(spec_path), "--no-annotate"])
        assert code == 1

    def test_exit_1_on_failed(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        result = _make_success_result()
        result.status = "failed"
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            code = cli_mod.main([str(spec_path), "--no-annotate"])
        assert code == 1

    def test_exit_2_on_build_failed(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        result = _make_success_result()
        result.status = "build_failed"
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            code = cli_mod.main([str(spec_path), "--no-annotate"])
        assert code == 2


class TestDryRun:
    def test_dry_run_exits_0(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        code = cli_mod.main([str(spec_path), "--dry-run"])
        assert code == 0

    def test_dry_run_does_not_call_llm(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        with patch("theseus.agent.run_prompt") as mock_prompt:
            cli_mod.main([str(spec_path), "--dry-run"])
        mock_prompt.assert_not_called()

    def test_dry_run_prints_prompt(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec_path = _make_spec_json(tmp_path)
        cli_mod.main([str(spec_path), "--dry-run"])
        out = capsys.readouterr().out
        assert "SYSTEM PROMPT" in out or "USER PROMPT" in out or "testlib" in out


class TestJsonOut:
    def test_json_out_file_created(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        json_out = tmp_path / "result.json"
        result = _make_success_result()
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            cli_mod.main([str(spec_path), "--no-annotate", "--json-out", str(json_out)])
        assert json_out.exists()

    def test_json_out_is_valid(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        json_out = tmp_path / "result.json"
        result = _make_success_result()
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            cli_mod.main([str(spec_path), "--no-annotate", "--json-out", str(json_out)])
        data = json.loads(json_out.read_text())
        assert data["canonical_name"] == "testlib"
        assert data["status"] == "success"

    def test_json_out_contains_required_fields(self, tmp_path: Path) -> None:
        spec_path = _make_spec_json(tmp_path)
        json_out = tmp_path / "result.json"
        result = _make_success_result()
        with (
            patch("theseus.agent.available", return_value=True),
            patch("theseus.synthesis.runner.SynthesisRunner.run", return_value=result),
        ):
            cli_mod.main([str(spec_path), "--no-annotate", "--json-out", str(json_out)])
        data = json.loads(json_out.read_text())
        required = [
            "canonical_name", "backend_lang", "status", "model",
            "attempted_at", "iterations", "final_pass_count",
            "final_fail_count", "total_invariants", "notes",
            "infeasible_reason", "failed_invariant_details",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"
