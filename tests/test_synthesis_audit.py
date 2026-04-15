"""
Tests for theseus/synthesis/audit.py — AuditReportGenerator.
"""
import json
from pathlib import Path

import pytest

from theseus.synthesis.audit import AuditReportGenerator
from theseus.synthesis.runner import SynthesisResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    canonical_name: str = "testlib",
    status: str = "success",
    pass_count: int = 5,
    fail_count: int = 0,
    total: int = 5,
    model: str = "claude-cli",
    failed_details: dict | None = None,
) -> SynthesisResult:
    return SynthesisResult(
        canonical_name=canonical_name,
        backend_lang="python",
        status=status,
        model=model,
        attempted_at="2026-04-13T00:00:00Z",
        iterations=1,
        attempts=[],
        final_pass_count=pass_count,
        final_fail_count=fail_count,
        total_invariants=total,
        notes="test",
        infeasible_reason=None,
        failed_invariant_details=failed_details or {},
    )


def _generate(tmp_path: Path, results: list[SynthesisResult]) -> dict:
    out = tmp_path / "audit.json"
    AuditReportGenerator().generate(results, out, human_readable=False)
    return json.loads(out.read_text())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuditSummaryCounts:
    def test_total_specs(self, tmp_path: Path) -> None:
        results = [_make_result("a"), _make_result("b")]
        report = _generate(tmp_path, results)
        assert report["summary"]["total_specs"] == 2

    def test_success_count(self, tmp_path: Path) -> None:
        results = [
            _make_result("a", status="success"),
            _make_result("b", status="partial"),
        ]
        report = _generate(tmp_path, results)
        assert report["summary"]["success_count"] == 1

    def test_partial_count(self, tmp_path: Path) -> None:
        results = [
            _make_result("a", status="partial"),
            _make_result("b", status="partial"),
        ]
        report = _generate(tmp_path, results)
        assert report["summary"]["partial_count"] == 2

    def test_failed_count(self, tmp_path: Path) -> None:
        results = [_make_result("a", status="failed")]
        report = _generate(tmp_path, results)
        assert report["summary"]["failed_count"] == 1

    def test_build_failed_count(self, tmp_path: Path) -> None:
        results = [_make_result("a", status="build_failed")]
        report = _generate(tmp_path, results)
        assert report["summary"]["build_failed_count"] == 1

    def test_infeasible_count(self, tmp_path: Path) -> None:
        results = [_make_result("a", status="infeasible")]
        report = _generate(tmp_path, results)
        assert report["summary"]["infeasible_count"] == 1

    def test_total_invariants(self, tmp_path: Path) -> None:
        results = [
            _make_result("a", total=10),
            _make_result("b", total=5),
        ]
        report = _generate(tmp_path, results)
        assert report["summary"]["total_invariants"] == 15

    def test_total_passing(self, tmp_path: Path) -> None:
        results = [
            _make_result("a", pass_count=8, total=10),
            _make_result("b", pass_count=5, total=5),
        ]
        report = _generate(tmp_path, results)
        assert report["summary"]["total_passing"] == 13

    def test_total_failing(self, tmp_path: Path) -> None:
        results = [
            _make_result("a", fail_count=2, total=10),
            _make_result("b", fail_count=0, total=5),
        ]
        report = _generate(tmp_path, results)
        assert report["summary"]["total_failing"] == 2


class TestSynthesizabilityRate:
    def test_all_success(self, tmp_path: Path) -> None:
        results = [_make_result("a", status="success"), _make_result("b", status="success")]
        report = _generate(tmp_path, results)
        assert report["summary"]["synthesizability_rate"] == 1.0

    def test_half_success(self, tmp_path: Path) -> None:
        results = [_make_result("a", status="success"), _make_result("b", status="failed")]
        report = _generate(tmp_path, results)
        assert report["summary"]["synthesizability_rate"] == 0.5

    def test_none_success(self, tmp_path: Path) -> None:
        results = [_make_result("a", status="failed")]
        report = _generate(tmp_path, results)
        assert report["summary"]["synthesizability_rate"] == 0.0

    def test_empty_list(self, tmp_path: Path) -> None:
        report = _generate(tmp_path, [])
        assert report["summary"]["synthesizability_rate"] == 0.0


class TestReportFileOutput:
    def test_json_file_written(self, tmp_path: Path) -> None:
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate([_make_result()], out, human_readable=False)
        assert out.exists()

    def test_json_is_valid(self, tmp_path: Path) -> None:
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate([_make_result()], out, human_readable=False)
        data = json.loads(out.read_text())
        assert "summary" in data and "specs" in data

    def test_human_readable_creates_txt(self, tmp_path: Path) -> None:
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate([_make_result()], out, human_readable=True)
        assert out.with_suffix(".txt").exists()

    def test_human_readable_txt_contains_spec_name(self, tmp_path: Path) -> None:
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate(
            [_make_result("speciallib")], out, human_readable=True
        )
        txt = out.with_suffix(".txt").read_text()
        assert "speciallib" in txt

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        out = tmp_path / "reports" / "synthesis" / "audit.json"
        AuditReportGenerator().generate([_make_result()], out, human_readable=False)
        assert out.exists()

    def test_generated_at_present(self, tmp_path: Path) -> None:
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate([_make_result()], out, human_readable=False)
        data = json.loads(out.read_text())
        assert "generated_at" in data
        assert data["generated_at"].endswith("Z")

    def test_spec_entries_present(self, tmp_path: Path) -> None:
        results = [_make_result("lib_a"), _make_result("lib_b")]
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate(results, out, human_readable=False)
        data = json.loads(out.read_text())
        names = [s["canonical_name"] for s in data["specs"]]
        assert "lib_a" in names
        assert "lib_b" in names

    def test_model_inferred_from_results(self, tmp_path: Path) -> None:
        results = [_make_result(model="test-model-x")]
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate(results, out)
        data = json.loads(out.read_text())
        assert data["model"] == "test-model-x"

    def test_model_overridden_by_parameter(self, tmp_path: Path) -> None:
        results = [_make_result(model="from-result")]
        out = tmp_path / "audit.json"
        AuditReportGenerator().generate(results, out, model="override-model")
        data = json.loads(out.read_text())
        assert data["model"] == "override-model"
