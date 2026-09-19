"""Characterization loop: gold-set authority, uncertainty ledgers, live probes."""
from __future__ import annotations

from pathlib import Path

import pytest

import characterize
import corpus_autopsy as autopsy
import live_probe

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "gold"


def test_list_families_includes_json_and_intended_set():
    names = characterize.list_families()
    assert "json" in names
    missing = autopsy.INTENDED_GOLD_SET - set(names)
    assert not missing, "gold-set families without package.md: {}".format(sorted(missing))


def test_phase11_cohort_families_are_characterized():
    names = set(characterize.list_families())
    missing = autopsy.CHARACTERIZATION_COHORT - names
    assert not missing, "Phase 11 cohort missing gold/<family>/: {}".format(sorted(missing))
    overlap = autopsy.CHARACTERIZATION_COHORT & autopsy.INTENDED_GOLD_SET
    assert not overlap, overlap
    for family in sorted(autopsy.CHARACTERIZATION_COHORT):
        rec = characterize.load_family(family)
        assert rec["meta"].get("held_out_oracle") in (None, "")
        assert rec["meta"].get("qualification") in ("none", None)
        assert rec["probes"] is not None, family


def test_characterize_bisect():
    report = characterize.characterize("bisect")
    assert report["family"] == "bisect"
    assert report["qualification"] == "none"
    names = [step["name"] for step in report["steps"]]
    assert "public_oracle" in names
    assert "live_probes" in names
    assert "held_out_guard" not in names


def test_every_gold_family_loads_with_reviewed_ledger():
    for family in characterize.list_families():
        rec = characterize.load_family(family)
        assert rec["meta"]["qualification"] in ("none", None)
        assert rec["meta"]["public_oracle"]
        assert rec["ledger"]["reviewed"] is True
        assert rec["ledger"]["items"]
        for item in rec["ledger"]["items"]:
            assert item["status"] in characterize.LEDGER_STATUSES, (family, item)


def test_open_ledger_is_rejected(tmp_path, monkeypatch):
    family_dir = tmp_path / "gold" / "demo"
    family_dir.mkdir(parents=True)
    (family_dir / "package.md").write_text(
        "---\nfamily: demo\nladder: characterized\nqualification: none\n"
        "public_oracle: zspecs/json.zspec.zsdl\n---\n\n# demo\n",
        encoding="utf-8",
    )
    (family_dir / "uncertainty.yaml").write_text(
        "family: demo\nreviewed: true\nitems:\n  - id: x\n    claim: leftover\n    status: open\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(characterize, "GOLD_ROOT", tmp_path / "gold")
    with pytest.raises(ValueError, match="unresolved"):
        characterize.load_family("demo")


def test_live_probe_refuses_source_path():
    with pytest.raises(ValueError, match="import name"):
        live_probe.probe_python("Lib/json.py", "dumps", [1], {})


def test_live_probe_json_dumps_integer():
    observed = live_probe.run_one("python_module", "json", "dumps", [42], {})
    assert observed["ok"] is True
    assert observed["result"] == "42"
    assert observed.get("module_file")
    # Receipt may name the origin path; the tool must not have needed its contents.
    path = Path(observed["module_file"])
    assert path.exists()


def test_live_probe_method_hexdigest():
    observed = live_probe.run_one(
        "python_module",
        "hashlib",
        "sha256",
        [{"type": "bytes_ascii", "value": ""}],
        {},
        method="hexdigest",
    )
    assert observed["ok"] is True
    assert observed["result"] == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_json_probes_file_passes():
    result = live_probe.run_file(GOLD / "json" / "probes.yaml")
    assert result["fail"] == 0
    assert result["pass"] >= 4


def test_json_layer2_avoids_held_out_tokens():
    text = (ROOT / "zspecs" / "json.zspec.zsdl").read_text(encoding="utf-8")
    for token in ("1.5e2", "café", "[1,]", r"\u0041", 'say "hi"', "{]"):
        assert token not in text


def test_characterize_json():
    report = characterize.characterize("json")
    assert report["family"] == "json"
    assert report["qualification"] == "none"
    names = [step["name"] for step in report["steps"]]
    assert "public_oracle" in names
    assert "live_probes" in names
    assert "held_out_guard" in names


def test_autopsy_scan_characterization_tmp(tmp_path):
    family = tmp_path / "gold" / "json"
    family.mkdir(parents=True)
    (family / "package.md").write_text("# json\n", encoding="utf-8")
    (family / "uncertainty.yaml").write_text(
        "reviewed: true\nitems:\n  - id: a\n    status: resolved\n    claim: ok\n",
        encoding="utf-8",
    )
    rows = autopsy.scan_characterization(tmp_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "accepted"
    assert rows[0]["intended_gold_set"] is True


def test_autopsy_scan_real_gold_accepted():
    rows = autopsy.scan_characterization(ROOT)
    by_name = {row["family"]: row for row in rows}
    missing = autopsy.INTENDED_GOLD_SET - set(by_name)
    assert not missing, missing
    for family in autopsy.INTENDED_GOLD_SET:
        assert by_name[family]["status"] == "accepted", family
    for family in autopsy.CHARACTERIZATION_COHORT:
        assert by_name[family]["status"] == "accepted", family
        assert by_name[family]["characterization_cohort"] is True
        assert by_name[family]["intended_gold_set"] is False


def test_autopsy_scan_rejects_open(tmp_path):
    family = tmp_path / "gold" / "json"
    family.mkdir(parents=True)
    (family / "package.md").write_text("# json\n", encoding="utf-8")
    (family / "uncertainty.yaml").write_text(
        "reviewed: true\nitems:\n  - id: a\n    status: open\n    claim: leftover\n",
        encoding="utf-8",
    )
    rows = autopsy.scan_characterization(tmp_path)
    assert rows[0]["status"] == "open"
    assert "a" in rows[0]["open_items"]
