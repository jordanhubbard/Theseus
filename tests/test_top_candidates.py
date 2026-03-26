"""
Tests for tools/top_candidates.py.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import top_candidates


def _make_record(name, ecosystem, version, confidence=0.9, build_deps=None, has_tests=True, patches=None):
    return {
        "schema_version": "0.1",
        "identity": {
            "canonical_name": name,
            "canonical_id": f"pkg:{name}",
            "ecosystem": ecosystem,
            "ecosystem_id": f"pkgs/{name}",
            "version": version,
        },
        "descriptive": {"summary": "", "categories": [], "license": []},
        "sources": [{"type": "archive", "url": "https://example.com/pkg.tar.gz"}],
        "dependencies": {
            "build": build_deps or [],
            "host": [],
            "runtime": [],
            "test": [],
        },
        "build": {"system_kind": "autotools"},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": patches or [],
        "tests": {"has_check_phase": has_tests} if has_tests else {},
        "provenance": {"confidence": confidence, "generated_by": "test"},
        "extensions": {},
    }


def _write(tmp_dir, records):
    for i, rec in enumerate(records):
        name = rec["identity"]["canonical_name"]
        eco = rec["identity"]["ecosystem"]
        (tmp_dir / f"{name}_{eco}_{i}.json").write_text(json.dumps(rec), encoding="utf-8")


def _run_main(snapshot, out):
    sys.argv = ["top_candidates.py", str(snapshot), "--out", str(out)]
    top_candidates.main()


# --- score_record ---

def test_score_record_returns_float():
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    assert isinstance(top_candidates.score_record(rec), float)


def test_score_record_positive_for_good_package():
    rec = _make_record("zlib", "nixpkgs", "1.3.1", confidence=0.95, has_tests=True)
    assert top_candidates.score_record(rec) > 0


def test_score_tests_add_points():
    rec_with = _make_record("pkg", "nixpkgs", "1.0", has_tests=True)
    rec_without = _make_record("pkg", "nixpkgs", "1.0", has_tests=False)
    assert top_candidates.score_record(rec_with) > top_candidates.score_record(rec_without)


def test_score_patches_reduce_score():
    rec_clean = _make_record("pkg", "nixpkgs", "1.0", patches=[])
    rec_patched = _make_record("pkg", "nixpkgs", "1.0", patches=[
        {"path": "files/patch-a", "reason": "fix build"},
        {"path": "files/patch-b", "reason": "security"},
    ])
    assert top_candidates.score_record(rec_clean) > top_candidates.score_record(rec_patched)


def test_score_fewer_deps_scores_higher():
    rec_few = _make_record("pkg", "nixpkgs", "1.0", build_deps=[])
    rec_many = _make_record("pkg", "nixpkgs", "1.0", build_deps=list("abcdefghijklmnopqrstu"))
    assert top_candidates.score_record(rec_few) > top_candidates.score_record(rec_many)


def test_score_higher_confidence_scores_higher():
    rec_high = _make_record("pkg", "nixpkgs", "1.0", confidence=0.95)
    rec_low = _make_record("pkg", "nixpkgs", "1.0", confidence=0.1)
    assert top_candidates.score_record(rec_high) > top_candidates.score_record(rec_low)


def test_score_uses_all_dep_categories():
    rec = _make_record("pkg", "nixpkgs", "1.0")
    rec["dependencies"]["test"] = ["pytest", "coverage"]
    score_with_test_deps = top_candidates.score_record(rec)
    rec2 = _make_record("pkg", "nixpkgs", "1.0")
    score_without = top_candidates.score_record(rec2)
    assert score_with_test_deps < score_without


# --- load_records ---

def test_load_records_empty(tmp_path):
    assert list(top_candidates.load_records(tmp_path)) == []


def test_load_records_finds_valid(tmp_path):
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    (tmp_path / "zlib.json").write_text(json.dumps(rec), encoding="utf-8")
    results = list(top_candidates.load_records(tmp_path))
    assert len(results) == 1


def test_load_records_skips_manifest(tmp_path):
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    (tmp_path / "manifest.json").write_text(json.dumps(rec), encoding="utf-8")
    assert list(top_candidates.load_records(tmp_path)) == []


def test_load_records_skips_invalid_json(tmp_path):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    assert list(top_candidates.load_records(tmp_path)) == []


# --- main / ranking ---

def test_main_creates_output_file(tmp_path):
    _write(tmp_path, [_make_record("zlib", "nixpkgs", "1.3.1")])
    out = tmp_path / "ranked.json"
    _run_main(tmp_path, out)
    assert out.exists()


def test_main_output_is_list(tmp_path):
    _write(tmp_path, [_make_record("zlib", "nixpkgs", "1.3.1")])
    out = tmp_path / "ranked.json"
    _run_main(tmp_path, out)
    ranked = json.loads(out.read_text())
    assert isinstance(ranked, list)


def test_main_dual_ecosystem_bonus(tmp_path):
    _write(tmp_path, [
        _make_record("dual", "nixpkgs", "1.0", confidence=0.5),
        _make_record("dual", "freebsd_ports", "1.0", confidence=0.5),
        _make_record("solo", "nixpkgs", "1.0", confidence=0.95),
    ])
    out = tmp_path / "ranked.json"
    _run_main(tmp_path, out)
    ranked = json.loads(out.read_text())
    names = [r["canonical_name"] for r in ranked]
    assert names[0] == "dual", "dual-ecosystem package should rank first due to bonus"


def test_main_ranked_fields_present(tmp_path):
    _write(tmp_path, [_make_record("zlib", "nixpkgs", "1.3.1")])
    out = tmp_path / "ranked.json"
    _run_main(tmp_path, out)
    ranked = json.loads(out.read_text())
    assert len(ranked) == 1
    entry = ranked[0]
    for field in ("canonical_name", "ecosystems", "score", "versions", "avg_confidence", "has_any_tests", "total_patch_count"):
        assert field in entry, f"ranked entry missing field '{field}'"


def test_main_groups_by_canonical_name(tmp_path):
    _write(tmp_path, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("zlib", "freebsd_ports", "1.3.1"),
        _make_record("curl", "nixpkgs", "8.5.0"),
    ])
    out = tmp_path / "ranked.json"
    _run_main(tmp_path, out)
    ranked = json.loads(out.read_text())
    assert len(ranked) == 2


def test_main_sorted_descending_by_score(tmp_path):
    _write(tmp_path, [
        _make_record("high", "nixpkgs", "1.0", confidence=0.99),
        _make_record("low", "nixpkgs", "1.0", confidence=0.01),
    ])
    out = tmp_path / "ranked.json"
    _run_main(tmp_path, out)
    ranked = json.loads(out.read_text())
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)
