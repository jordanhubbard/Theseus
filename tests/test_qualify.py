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


def test_check_rejects_qualified_without_empty_workspace_pair():
    receipts = [
        {
            "family": "json",
            "attempted": True,
            "skipped": False,
            "qualified": True,
            "independent_generation": True,
            "empty_workspace_pair": False,
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
    assert any("empty-workspace" in e for e in errors)


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


# Families with two stored empty-workspace generations that both passed.
QUALIFIED_FAMILIES = {
    "base64",
    "binascii",
    "difflib",
    "fnmatch",
    "hashlib",
    "hmac",
    "json",
    "shlex",
    "struct",
    "urllib_parse",
    "bisect",
    "colorsys",
}


def test_committed_receipts_are_honest():
    summary = json.loads((RECEIPTS / "summary.json").read_text(encoding="utf-8"))
    assert summary["qualified"] == len(QUALIFIED_FAMILIES)
    assert summary["attempted"] >= 5
    assert set(summary["families_qualified"]) == QUALIFIED_FAMILIES
    assert summary["kill_gate"]["fired"] is False
    assert summary["kill_gate"]["product_claim"] == "replacement_still_open"
    for family in summary["families_attempted"]:
        rec = json.loads((RECEIPTS / "{}.json".format(family)).read_text(encoding="utf-8"))
        assert rec["attempted"] is True
        assert rec["public_oracle"]["ok"] is True
        assert rec["held_out_oracle"]["ok"] is True
        assert rec["held_out_guard"]["pass"] is True
        assert rec["isolation"] is True
        if family in QUALIFIED_FAMILIES:
            assert rec["qualified"] is True
            assert rec["independent_generation"] is True
            assert rec["empty_workspace_pair"] is True
            assert rec["impl_hash_run1"] != rec["impl_hash_run2"]
        else:
            assert rec["qualified"] is False
            assert rec["independent_generation"] is False


def test_registry_is_qualified_tracks_dual_generation_not_legacy_status():
    assert registry.is_allowed("theseus_json") is True
    assert registry.is_qualified("theseus_re") is False
    assert registry.is_qualified("theseus_base64") is False
    data = json.loads((ROOT / "theseus_registry.json").read_text(encoding="utf-8"))
    assert data["ladder"]["is_qualified"] is False
    assert data["ladder"]["qualified"] == [
        "theseus_base64_q",
        "theseus_fnmatch_q",
        "theseus_json",
        "theseus_shlex_q",
        "theseus_binascii_q",
        "theseus_difflib_q",
        "theseus_hashlib_q",
        "theseus_hmac_q",
        "theseus_struct_q",
        "theseus_urllib_parse_q",
        "theseus_bisect_q",
        "theseus_colorsys_q",
    ]
    assert data["ladder"]["product"] == "characterization"
    assert registry.is_qualified("theseus_base64_q") is True
    assert registry.is_qualified("theseus_fnmatch_q") is True
    assert registry.is_qualified("theseus_json") is True
    assert registry.is_qualified("theseus_shlex_q") is True
    assert registry.is_qualified("theseus_binascii_q") is True
    assert registry.is_qualified("theseus_difflib_q") is True
    assert registry.is_qualified("theseus_hashlib_q") is True
    assert registry.is_qualified("theseus_hmac_q") is True
    assert registry.is_qualified("theseus_struct_q") is True
    assert registry.is_qualified("theseus_urllib_parse_q") is True
    assert registry.is_qualified("theseus_bisect_q") is True
    assert registry.is_qualified("theseus_colorsys_q") is True
