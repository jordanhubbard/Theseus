"""Qualification protocol (ADR 0004) and kill gate (ADR 0005)."""
from __future__ import annotations

import json
from pathlib import Path

import qualify
import registry

ROOT = Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / "reports" / "qualification"


def test_summarize_kill_gate_fires_when_none_qualify():
    receipts = [
        {"family": "a", "attempted": True, "skipped": False, "qualified": False},
        {"family": "b", "attempted": True, "skipped": False, "qualified": False},
        {"family": "c", "attempted": True, "skipped": False, "qualified": False},
        {"family": "d", "attempted": True, "skipped": False, "qualified": False},
        {"family": "e", "attempted": True, "skipped": False, "qualified": False},
        {"family": "skip", "attempted": False, "skipped": True, "reason": "native"},
    ]
    summary = qualify.summarize(receipts)
    assert summary["attempted"] == 5
    assert summary["qualified"] == 0
    assert summary["kill_gate"]["fired"] is True
    assert summary["kill_gate"]["product_claim"] == "characterization"
    assert qualify.check_receipts(summary, receipts) == []


def test_check_rejects_qualified_without_independent_generation():
    receipts = [
        {
            "family": "json",
            "attempted": True,
            "skipped": False,
            "qualified": True,
            "independent_generation": False,
            "held_out_guard": {"pass": True},
        }
    ]
    summary = {
        "attempted": 1,
        "qualified": 1,
        "families_qualified": ["json"],
        "kill_gate": {"fired": False},
    }
    errors = qualify.check_receipts(summary, receipts)
    assert any("independent_generation" in e for e in errors)


def test_committed_receipts_are_honest():
    summary = json.loads((RECEIPTS / "summary.json").read_text(encoding="utf-8"))
    assert summary["qualified"] == 0
    assert summary["attempted"] >= 5
    assert summary["kill_gate"]["fired"] is True
    assert summary["kill_gate"]["product_claim"] == "characterization"
    assert summary["families_qualified"] == []
    for family in summary["families_attempted"]:
        rec = json.loads((RECEIPTS / "{}.json".format(family)).read_text(encoding="utf-8"))
        assert rec["attempted"] is True
        assert rec["qualified"] is False
        assert rec["independent_generation"] is False
        assert rec["public_oracle"]["ok"] is True
        assert rec["held_out_oracle"]["ok"] is True
        assert rec["held_out_guard"]["pass"] is True
        assert rec["isolation"] is True


def test_registry_is_qualified_false_for_legacy_verified():
    assert registry.is_qualified("theseus_json") is False
    assert registry.is_allowed("theseus_json") is True
    data = json.loads((ROOT / "theseus_registry.json").read_text(encoding="utf-8"))
    assert data["ladder"]["is_qualified"] is False
    assert data["ladder"]["qualified"] == []
    assert data["ladder"]["product"] == "characterization"
