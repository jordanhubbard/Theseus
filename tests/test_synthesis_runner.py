"""
Tests for theseus/synthesis/runner.py — SynthesisRunner (mocked LLM and build).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from theseus.synthesis.build import SynthesisBuildResult
from theseus.synthesis.runner import SynthesisRunner, SynthesisResult, _detect_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(n_invariants: int = 2) -> dict:
    return {
        "identity": {"canonical_name": "testlib"},
        "library": {"backend": "python_module", "module_name": "testlib"},
        "provenance": {"derived_from": [], "not_derived_from": [], "notes": []},
        "functions": {},
        "constants": {},
        "wire_formats": {},
        "error_model": {},
        "invariants": [
            {
                "id": f"testlib.inv.{i}",
                "kind": "python_call_eq",
                "description": f"invariant {i}",
                "spec": {},
                "category": "basic",
            }
            for i in range(n_invariants)
        ],
    }


def _all_pass_results(spec: dict) -> list[dict]:
    return [
        {"id": inv["id"], "passed": True, "message": "ok", "skip_reason": None}
        for inv in spec["invariants"]
    ]


def _all_fail_results(spec: dict) -> list[dict]:
    return [
        {"id": inv["id"], "passed": False, "message": "mismatch", "skip_reason": None}
        for inv in spec["invariants"]
    ]


_VALID_RESPONSE = (
    '<file name="testlib.py"><content>\ndef do_thing(x):\n    return x\n</content></file>'
)

_GOOD_BUILD = SynthesisBuildResult(
    success=True,
    artifact_path="/tmp/fake",
    backend_lang="python",
    build_log="",
    returncode=0,
    work_dir="/tmp/fake",
)

_BAD_BUILD = SynthesisBuildResult(
    success=False,
    artifact_path="",
    backend_lang="python",
    build_log="SyntaxError: bad code",
    returncode=1,
    work_dir="/tmp/fake",
)

_AI_CFG = {"provider": "auto"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSynthesisRunnerSuccess:
    def test_success_on_first_iteration(self, tmp_path: Path) -> None:
        spec = _make_spec(2)
        verify_results = _all_pass_results(spec)

        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(
                SynthesisRunner, "_invoke_verify_harness", return_value=verify_results
            ),
            patch(
                "theseus.synthesis.build.SynthesisBuildDriver.build",
                return_value=_GOOD_BUILD,
            ),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=3)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert result.status == "success"
        assert result.iterations == 1
        assert result.final_pass_count == 2
        assert result.final_fail_count == 0

    def test_retries_on_failure_then_succeeds(self, tmp_path: Path) -> None:
        spec = _make_spec(2)
        fail_results = _all_fail_results(spec)
        pass_results = _all_pass_results(spec)

        call_count = {"verify": 0}

        def verify_side_effect(*args, **kwargs):
            call_count["verify"] += 1
            if call_count["verify"] == 1:
                return fail_results
            return pass_results

        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(
                SynthesisRunner, "_invoke_verify_harness", side_effect=verify_side_effect
            ),
            patch(
                "theseus.synthesis.build.SynthesisBuildDriver.build",
                return_value=_GOOD_BUILD,
            ),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=3)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert result.status == "success"
        assert result.iterations == 2

    def test_gives_up_after_max_iterations(self, tmp_path: Path) -> None:
        spec = _make_spec(2)
        fail_results = _all_fail_results(spec)

        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(
                SynthesisRunner, "_invoke_verify_harness", return_value=fail_results
            ),
            patch(
                "theseus.synthesis.build.SynthesisBuildDriver.build",
                return_value=_GOOD_BUILD,
            ),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=2)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert result.status in ("failed", "partial")
        assert result.iterations == 2

    def test_build_failure_sets_build_failed_status(self, tmp_path: Path) -> None:
        spec = _make_spec(2)

        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(SynthesisRunner, "_invoke_verify_harness", return_value=[]),
            patch(
                "theseus.synthesis.build.SynthesisBuildDriver.build",
                return_value=_BAD_BUILD,
            ),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=1)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert result.status == "build_failed"

    def test_partial_status_when_some_pass(self, tmp_path: Path) -> None:
        spec = _make_spec(4)
        mixed = [
            {"id": f"testlib.inv.{i}", "passed": i < 2, "message": "ok" if i < 2 else "err", "skip_reason": None}
            for i in range(4)
        ]

        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(SynthesisRunner, "_invoke_verify_harness", return_value=mixed),
            patch(
                "theseus.synthesis.build.SynthesisBuildDriver.build",
                return_value=_GOOD_BUILD,
            ),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=1)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert result.status == "partial"
        assert result.final_pass_count == 2
        assert result.final_fail_count == 2

    def test_llm_unavailable_returns_infeasible(self, tmp_path: Path) -> None:
        spec = _make_spec(2)

        with patch(
            "theseus.synthesis.runner.agent_mod.run_prompt",
            side_effect=RuntimeError("No AI provider"),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=3)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert result.status == "infeasible"
        assert result.infeasible_reason == "llm_unavailable"

    def test_failed_invariant_details_populated(self, tmp_path: Path) -> None:
        spec = _make_spec(2)
        fail_results = _all_fail_results(spec)

        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(SynthesisRunner, "_invoke_verify_harness", return_value=fail_results),
            patch(
                "theseus.synthesis.build.SynthesisBuildDriver.build",
                return_value=_GOOD_BUILD,
            ),
        ):
            runner = SynthesisRunner(_AI_CFG, max_iterations=1)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)

        assert "testlib.inv.0" in result.failed_invariant_details
        assert result.failed_invariant_details["testlib.inv.0"]["status"] == "failed"

    @pytest.mark.skipif(
        not (shutil.which("node") or shutil.which("nodejs")),
        reason="node not available",
    )
    def test_javascript_verify_shadows_node_builtin(self, tmp_path: Path) -> None:
        spec = {
            "schema_version": "0.2",
            "identity": {"canonical_name": "node_os"},
            "library": {
                "backend": "cli",
                "command": "node",
                "module_name": "os",
            },
            "provenance": {"derived_from": [], "not_derived_from": [], "notes": []},
            "constants": {},
            "types": {},
            "functions": {},
            "wire_formats": {},
            "error_model": {},
            "invariants": [
                {
                    "id": "node_os.osplat.linux",
                    "kind": "node_module_call_eq",
                    "description": "platform",
                    "category": "platform",
                    "spec": {
                        "function": "platform",
                        "args": [],
                        "expected": "linux",
                    },
                }
            ],
        }
        spec_path = tmp_path / "node_os.zspec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        package_dir = tmp_path / "node_modules" / "os"
        package_dir.mkdir(parents=True)
        (package_dir / "index.js").write_text(
            "module.exports = { platform: () => 'linux' };\n",
            encoding="utf-8",
        )

        build = SynthesisBuildResult(
            success=True,
            artifact_path=str(tmp_path),
            backend_lang="javascript",
            build_log="",
            returncode=0,
            work_dir=str(tmp_path),
        )
        runner = SynthesisRunner(_AI_CFG)

        results = runner._invoke_verify_harness(
            spec_path,
            build,
            spec["library"],
            spec["invariants"],
        )

        assert results[0]["passed"] is True

    def test_canonical_name_in_result(self, tmp_path: Path) -> None:
        spec = _make_spec()
        with (
            patch("theseus.synthesis.runner.agent_mod.run_prompt", return_value=_VALID_RESPONSE),
            patch.object(SynthesisRunner, "_invoke_verify_harness", return_value=_all_pass_results(spec)),
            patch("theseus.synthesis.build.SynthesisBuildDriver.build", return_value=_GOOD_BUILD),
        ):
            runner = SynthesisRunner(_AI_CFG)
            result = runner.run(spec, tmp_path / "testlib.zspec.json", tmp_path)
        assert result.canonical_name == "testlib"


class TestEnvVarOverrides:
    """Verify that _invoke_verify_harness sets the right environment variables."""

    def test_python_sets_pythonpath(self, tmp_path: Path) -> None:
        """For Python builds, PYTHONPATH must contain the artifact_path."""
        spec = _make_spec()
        runner = SynthesisRunner(_AI_CFG, max_iterations=1)

        captured_env: dict = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            # Write empty JSON result file so the runner can parse it
            for arg in cmd:
                if str(arg).endswith(".json") and "--json-out" in cmd:
                    idx = cmd.index("--json-out")
                    Path(cmd[idx + 1]).write_text("[]", encoding="utf-8")
                    break
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            return mock_result

        build_result = SynthesisBuildResult(
            success=True,
            artifact_path="/tmp/synth_staging",
            backend_lang="python",
            build_log="",
            returncode=0,
            work_dir="/tmp/synth_staging",
        )

        with patch("subprocess.run", side_effect=fake_run):
            runner._invoke_verify_harness(tmp_path / "x.zspec.json", build_result, {})

        assert "PYTHONPATH" in captured_env
        assert "/tmp/synth_staging" in captured_env["PYTHONPATH"]

    def test_c_sets_ld_library_path(self, tmp_path: Path) -> None:
        """For C builds, LD_LIBRARY_PATH must contain work_dir."""
        spec = _make_spec()
        runner = SynthesisRunner(_AI_CFG, max_iterations=1)

        captured_env: dict = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            for arg in cmd:
                if "--json-out" in str(cmd):
                    idx = list(cmd).index("--json-out")
                    Path(cmd[idx + 1]).write_text("[]", encoding="utf-8")
                    break
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            return mock_result

        build_result = SynthesisBuildResult(
            success=True,
            artifact_path="/tmp/mylib.so",
            backend_lang="c",
            build_log="",
            returncode=0,
            work_dir="/tmp/c_work",
        )

        with patch("subprocess.run", side_effect=fake_run):
            runner._invoke_verify_harness(tmp_path / "x.zspec.json", build_result, {})

        assert "LD_LIBRARY_PATH" in captured_env
        assert "/tmp/c_work" in captured_env["LD_LIBRARY_PATH"]

    def test_harness_crash_returns_failed_invariants(self, tmp_path: Path) -> None:
        spec = _make_spec(2)
        runner = SynthesisRunner(_AI_CFG, max_iterations=1)

        def fake_run(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 2
            mock_result.stderr = "import failed"
            mock_result.stdout = ""
            return mock_result

        build_result = SynthesisBuildResult(
            success=True,
            artifact_path="/tmp/synth_staging",
            backend_lang="python",
            build_log="",
            returncode=0,
            work_dir="/tmp/synth_staging",
        )

        with patch("subprocess.run", side_effect=fake_run):
            results = runner._invoke_verify_harness(
                tmp_path / "x.zspec.json",
                build_result,
                {},
                spec["invariants"],
            )

        assert len(results) == 2
        assert all(r["passed"] is False for r in results)
        assert all("Harness error (exit 2): import failed" in r["message"] for r in results)


class TestDetectModel:
    def test_claude_in_path(self) -> None:
        import shutil
        with patch.object(shutil, "which", return_value="/usr/bin/claude"):
            model = _detect_model({"provider": "claude"})
        assert model == "claude-cli"

    def test_openai_model_returned(self) -> None:
        with patch("shutil.which", return_value=None):
            model = _detect_model({"provider": "openai", "openai_model": "gpt-4o"})
        assert model == "gpt-4o"
