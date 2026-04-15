"""
theseus/synthesis/audit.py

Aggregates multiple SynthesisResult objects into a machine-readable JSON audit
report and an optional human-readable text summary.

The audit report schema lives at schema/synthesis-result.schema.json.
"""
from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from theseus.synthesis.runner import SynthesisResult


@dataclass
class AuditSummary:
    total_specs: int = 0
    success_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    build_failed_count: int = 0
    infeasible_count: int = 0
    total_invariants: int = 0
    total_passing: int = 0
    total_failing: int = 0
    synthesizability_rate: float = 0.0


class AuditReportGenerator:
    """
    Generates an audit report from a list of SynthesisResult objects.

    Usage::

        gen = AuditReportGenerator()
        gen.generate(results, Path("reports/synthesis/audit.json"))
    """

    def generate(
        self,
        results: list[SynthesisResult],
        output_path: Path,
        *,
        human_readable: bool = True,
        model: str = "",
    ) -> None:
        """
        Write the JSON audit report to *output_path*.

        If *human_readable* is True, also writes a ``.txt`` summary alongside
        the JSON file.

        Args:
            results: list of SynthesisResult objects (one per spec).
            output_path: destination for the JSON report.
            human_readable: whether to also write a plain-text summary.
            model: model name to embed in the report header.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary = _compute_summary(results)
        report = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": model or _infer_model(results),
            "summary": _summary_to_dict(summary),
            "specs": [_result_to_dict(r) for r in results],
        }

        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        if human_readable:
            txt_path = output_path.with_suffix(".txt")
            txt_path.write_text(_render_text(report, results), encoding="utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_summary(results: list[SynthesisResult]) -> AuditSummary:
    s = AuditSummary()
    s.total_specs = len(results)
    for r in results:
        if r.status == "success":
            s.success_count += 1
        elif r.status == "partial":
            s.partial_count += 1
        elif r.status == "build_failed":
            s.build_failed_count += 1
        elif r.status == "infeasible":
            s.infeasible_count += 1
        else:
            s.failed_count += 1
        s.total_invariants += r.total_invariants
        s.total_passing += r.final_pass_count
        s.total_failing += r.final_fail_count
    if s.total_specs > 0:
        s.synthesizability_rate = round(s.success_count / s.total_specs, 4)
    return s


def _summary_to_dict(s: AuditSummary) -> dict:
    return {
        "total_specs": s.total_specs,
        "success_count": s.success_count,
        "partial_count": s.partial_count,
        "failed_count": s.failed_count,
        "build_failed_count": s.build_failed_count,
        "infeasible_count": s.infeasible_count,
        "total_invariants": s.total_invariants,
        "total_passing": s.total_passing,
        "total_failing": s.total_failing,
        "synthesizability_rate": s.synthesizability_rate,
    }


def _result_to_dict(r: SynthesisResult) -> dict:
    return {
        "canonical_name": r.canonical_name,
        "backend_lang": r.backend_lang,
        "status": r.status,
        "model": r.model,
        "attempted_at": r.attempted_at,
        "iterations": r.iterations,
        "pass_count": r.final_pass_count,
        "fail_count": r.final_fail_count,
        "total_invariants": r.total_invariants,
        "notes": r.notes,
        "infeasible_reason": r.infeasible_reason,
        "failed_invariant_details": r.failed_invariant_details,
    }


def _infer_model(results: list[SynthesisResult]) -> str:
    for r in results:
        if r.model:
            return r.model
    return "unknown"


def _render_text(report: dict, results: list[SynthesisResult]) -> str:
    s = report["summary"]
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("THESEUS SYNTHESIS AUDIT REPORT")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Model:     {report['model']}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total specs:          {s['total_specs']}")
    lines.append(f"  Succeeded:            {s['success_count']}")
    lines.append(f"  Partial:              {s['partial_count']}")
    lines.append(f"  Failed:               {s['failed_count']}")
    lines.append(f"  Build failed:         {s['build_failed_count']}")
    lines.append(f"  Infeasible:           {s['infeasible_count']}")
    lines.append(f"  Total invariants:     {s['total_invariants']}")
    lines.append(f"  Passing invariants:   {s['total_passing']}")
    lines.append(f"  Failing invariants:   {s['total_failing']}")
    lines.append(f"  Synthesizability:     {s['synthesizability_rate']:.1%}")
    lines.append("")
    lines.append("PER-SPEC RESULTS")
    lines.append("-" * 70)
    header = f"{'Spec':<30} {'Lang':<12} {'Status':<14} {'Pass':>5} {'Fail':>5} {'Iters':>5}"
    lines.append(header)
    lines.append("-" * 70)
    for r in results:
        lines.append(
            f"{r.canonical_name:<30} {r.backend_lang:<12} {r.status:<14} "
            f"{r.final_pass_count:>5} {r.final_fail_count:>5} {r.iterations:>5}"
        )
    lines.append("")
    # Failed invariant detail section
    any_failed = any(r.failed_invariant_details for r in results)
    if any_failed:
        lines.append("FAILED INVARIANT DETAILS")
        lines.append("-" * 70)
        for r in results:
            if r.failed_invariant_details:
                lines.append(f"  {r.canonical_name}:")
                for inv_id, detail in r.failed_invariant_details.items():
                    reason = detail.get("reason", "")[:80]
                    lines.append(f"    - {inv_id}: {reason}")
        lines.append("")
    return "\n".join(lines)
