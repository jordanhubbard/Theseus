"""
Tests for tools/spec_coverage.py.

Exercises load_extraction_records, build_report, and main() using tmp_path
synthetic extraction records. Does not require a real snapshot directory.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import spec_coverage as sc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_record(tmp_path: Path, name: str, score: float, has_bspec: bool = False) -> Path:
    """Write a minimal extraction record JSON and return its path."""
    data = {
        "identity": {"canonical_name": name},
        "analysis": {"composite_score": score},
    }
    if has_bspec:
        data["behavioral_spec"] = f"zspecs/{name}.zspec.json"
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# load_extraction_records
# ---------------------------------------------------------------------------

class TestLoadExtractionRecords:
    def test_loads_records(self, tmp_path):
        write_record(tmp_path, "alpha", 0.9)
        write_record(tmp_path, "beta", 0.5)
        records = sc.load_extraction_records(tmp_path)
        names = [r["identity"]["canonical_name"] for r in records]
        assert "alpha" in names
        assert "beta" in names

    def test_sorted_by_score_desc(self, tmp_path):
        write_record(tmp_path, "low", 0.1)
        write_record(tmp_path, "high", 0.95)
        write_record(tmp_path, "mid", 0.5)
        records = sc.load_extraction_records(tmp_path)
        scores = [r["analysis"]["composite_score"] for r in records]
        assert scores == sorted(scores, reverse=True)

    def test_skips_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json}")
        write_record(tmp_path, "good", 0.7)
        records = sc.load_extraction_records(tmp_path)
        assert len(records) == 1

    def test_skips_non_dict(self, tmp_path):
        arr = tmp_path / "array.json"
        arr.write_text("[1, 2, 3]")
        write_record(tmp_path, "good", 0.7)
        records = sc.load_extraction_records(tmp_path)
        assert len(records) == 1

    def test_empty_dir_returns_empty(self, tmp_path):
        records = sc.load_extraction_records(tmp_path)
        assert records == []


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

class TestBuildReport:
    def _records(self, tmp_path, specs):
        """specs: list of (name, score, has_bspec)"""
        records = []
        for name, score, has_bspec in specs:
            write_record(tmp_path, name, score, has_bspec)
        return sc.load_extraction_records(tmp_path)

    def test_all_covered(self, tmp_path):
        records = self._records(tmp_path, [
            ("alpha", 0.9, True),
            ("beta", 0.8, True),
        ])
        r = sc.build_report(records, top=None)
        assert r["total"] == 2
        assert r["covered"] == 2
        assert r["gap_count"] == 0

    def test_none_covered(self, tmp_path):
        records = self._records(tmp_path, [
            ("alpha", 0.9, False),
            ("beta", 0.8, False),
        ])
        r = sc.build_report(records, top=None)
        assert r["total"] == 2
        assert r["covered"] == 0
        assert r["gap_count"] == 2

    def test_mixed(self, tmp_path):
        records = self._records(tmp_path, [
            ("alpha", 0.9, True),
            ("beta", 0.5, False),
            ("gamma", 0.3, False),
        ])
        r = sc.build_report(records, top=None)
        assert r["total"] == 3
        assert r["covered"] == 1
        assert r["gap_count"] == 2

    def test_top_limits_candidates(self, tmp_path):
        records = self._records(tmp_path, [
            ("high", 0.9, True),
            ("mid", 0.5, False),
            ("low", 0.1, False),
        ])
        r = sc.build_report(records, top=2)
        assert r["total"] == 2
        assert r["covered"] == 1  # high has bspec, mid does not

    def test_gap_list_canonical_names(self, tmp_path):
        records = self._records(tmp_path, [
            ("needsspec", 0.7, False),
        ])
        r = sc.build_report(records, top=None)
        names = [e["canonical_name"] for e in r["gap_list"]]
        assert "needsspec" in names

    def test_covered_list_includes_score(self, tmp_path):
        records = self._records(tmp_path, [
            ("covered", 0.85, True),
        ])
        r = sc.build_report(records, top=None)
        assert r["covered_list"][0]["composite_score"] == pytest.approx(0.85)

    def test_real_spec_detection(self, tmp_path):
        """A record with canonical_name matching a real zspec file is 'covered' even without behavioral_spec field."""
        # "zlib" has a real zspec
        records = [{"identity": {"canonical_name": "zlib"}, "analysis": {"composite_score": 0.99}}]
        r = sc.build_report(records, top=None)
        assert r["covered"] == 1, "zlib should be covered because zspecs/zlib.zspec.json exists"

    def test_nonexistent_spec_not_covered(self, tmp_path):
        records = [{"identity": {"canonical_name": "definitely_no_spec_xyz"}, "analysis": {"composite_score": 0.5}}]
        r = sc.build_report(records, top=None)
        assert r["gap_count"] == 1


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_text_report_exit_0(self, tmp_path):
        write_record(tmp_path, "alpha", 0.9, has_bspec=True)
        write_record(tmp_path, "beta", 0.5, has_bspec=False)
        rc = sc.main([str(tmp_path)])
        assert rc == 0

    def test_json_report_stdout(self, tmp_path, capsys):
        write_record(tmp_path, "alpha", 0.9, has_bspec=True)
        rc = sc.main([str(tmp_path), "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "total" in data
        assert "covered" in data
        assert "gap_count" in data

    def test_top_flag(self, tmp_path, capsys):
        for i, score in enumerate([0.9, 0.8, 0.7, 0.6]):
            write_record(tmp_path, f"lib{i}", score)
        rc = sc.main([str(tmp_path), "--top", "2", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total"] == 2

    def test_nonexistent_dir_exits_2(self, tmp_path):
        rc = sc.main([str(tmp_path / "doesnotexist")])
        assert rc == 2

    def test_empty_dir_exits_1(self, tmp_path):
        rc = sc.main([str(tmp_path)])
        assert rc == 1

    def test_text_output_contains_summary(self, tmp_path, capsys):
        write_record(tmp_path, "lib_a", 0.9, has_bspec=True)
        write_record(tmp_path, "lib_b", 0.5, has_bspec=False)
        sc.main([str(tmp_path)])
        out = capsys.readouterr().out
        assert "Total candidates" in out
        assert "Covered" in out
        assert "Gap" in out
