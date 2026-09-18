"""Gold-set wrapper freeze and characterization-record schema (ADR 0006 / Phase 7)."""
from __future__ import annotations

import json
from pathlib import Path

import characterize
import lint_gold_wrappers as lint

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads(
    (ROOT / "schema" / "characterization-record.schema.json").read_text(encoding="utf-8")
)


def test_gold_cleanroom_specs_are_not_zero_arg_wrappers():
    errors, info = lint.lint()
    assert errors == [], errors
    assert "zspecs/theseus_json.zspec.zsdl" in info["gold"]
    assert any(name.endswith("_q.zspec.zsdl") for name in info["gold"])


def test_factory_freeze_covers_legacy_theseus_specs():
    freeze = lint.load_freeze()
    specs = set(freeze.get("specs") or [])
    assert specs, "factory-wrapper-freeze.json must list grandfathered factory specs"
    assert "zspecs/theseus_json.zspec.zsdl" not in specs
    assert not any(name.endswith("_q.zspec.zsdl") for name in specs)


def test_characterization_records_match_schema_required_keys():
    required = set(SCHEMA["required"])
    for family in characterize.list_families():
        rec = characterize.characterization_record(family)
        assert rec["kind"] == "characterization_record"
        assert rec["qualification"] == "none"
        missing = required - set(rec)
        assert not missing, (family, missing)
        assert rec["family"] == family
        assert (ROOT / rec["authority"]).is_file()
        assert (ROOT / rec["public_oracle"]).is_file()
        assert (ROOT / rec["uncertainty_ledger"]).is_file()
