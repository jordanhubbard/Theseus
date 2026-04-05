"""
Tests for tools/spec_vector_coverage.py.

Exercises analyse_spec, load_specs, resolve_spec_paths, and main()
using synthetic tmp_path fixtures and the real _build/zspecs/ directory.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import spec_vector_coverage as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_spec(tmp_path: Path, name: str, invariants: list[dict]) -> Path:
    """Write a minimal compiled zspec file and return its path."""
    data = {
        "schema_version": "0.1",
        "identity": {"canonical_name": name},
        "invariants": invariants,
    }
    path = tmp_path / f"{name}.zspec.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def inv(id_: str, category: str, description: str = "") -> dict:
    """Build a minimal invariant dict."""
    d = {"id": id_, "category": category, "kind": "python_call_eq"}
    if description:
        d["description"] = description
    return d


# ---------------------------------------------------------------------------
# analyse_spec
# ---------------------------------------------------------------------------

class TestAnalyseSpec:
    def test_all_described(self, tmp_path):
        path = make_spec(tmp_path, "mylib", [
            inv("mylib.a.1", "cat_a", "desc1"),
            inv("mylib.a.2", "cat_a", "desc2"),
        ])
        rec = svc.analyse_spec(path)
        assert rec["spec"] == "mylib"
        assert rec["total"] == 2
        assert rec["described"] == 2
        assert rec["score"] == 100.0

    def test_none_described(self, tmp_path):
        path = make_spec(tmp_path, "emptylib", [
            inv("emptylib.a.1", "cat_a"),
            inv("emptylib.a.2", "cat_a"),
        ])
        rec = svc.analyse_spec(path)
        assert rec["score"] == 0.0
        assert rec["described"] == 0

    def test_partial_description(self, tmp_path):
        path = make_spec(tmp_path, "partial", [
            inv("partial.a.1", "cat_a", "has desc"),
            inv("partial.a.2", "cat_a"),          # no desc
            inv("partial.a.3", "cat_a"),          # no desc
        ])
        rec = svc.analyse_spec(path)
        assert rec["total"] == 3
        assert rec["described"] == 1
        assert abs(rec["score"] - 33.3) < 0.2

    def test_categories_sorted(self, tmp_path):
        path = make_spec(tmp_path, "sorted", [
            inv("s.z.1", "zzz", "d"),
            inv("s.a.1", "aaa", "d"),
            inv("s.m.1", "mmm", "d"),
        ])
        rec = svc.analyse_spec(path)
        cat_names = [c["name"] for c in rec["categories"]]
        assert cat_names == sorted(cat_names)

    def test_empty_description_string_not_counted(self, tmp_path):
        path = make_spec(tmp_path, "empties", [
            inv("e.a.1", "cat_a", ""),   # empty string — not described
            inv("e.a.2", "cat_a", "  "), # whitespace only — not described
            inv("e.a.3", "cat_a", "real desc"),
        ])
        rec = svc.analyse_spec(path)
        assert rec["described"] == 1

    def test_no_invariants(self, tmp_path):
        path = make_spec(tmp_path, "empty_spec", [])
        rec = svc.analyse_spec(path)
        assert rec["total"] == 0
        assert rec["described"] == 0
        assert rec["score"] == 0.0
        assert rec["categories"] == []

    def test_category_level_scores(self, tmp_path):
        path = make_spec(tmp_path, "cattest", [
            inv("ct.a.1", "alpha", "d"),
            inv("ct.a.2", "alpha", "d"),
            inv("ct.b.1", "beta"),
            inv("ct.b.2", "beta"),
            inv("ct.b.3", "beta"),
        ])
        rec = svc.analyse_spec(path)
        cats = {c["name"]: c for c in rec["categories"]}
        assert cats["alpha"]["score"] == 100.0
        assert cats["beta"]["score"] == 0.0


# ---------------------------------------------------------------------------
# main() — text output
# ---------------------------------------------------------------------------

class TestMainTextOutput:
    def test_text_output_contains_summary(self, tmp_path, capsys):
        make_spec(tmp_path, "mylib", [inv("mylib.a.1", "cat_a", "desc")])
        rc = svc.main([str(tmp_path / "mylib.zspec.json")])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Summary:" in out
        assert "mylib" in out

    def test_text_output_shows_spec_name(self, tmp_path, capsys):
        make_spec(tmp_path, "alpha", [inv("alpha.a.1", "cat_a", "d")])
        svc.main([str(tmp_path / "alpha.zspec.json")])
        out = capsys.readouterr().out
        assert "spec: alpha" in out

    def test_always_exits_0(self, tmp_path, capsys):
        # No spec files at all — still exit 0.
        rc = svc.main([])
        assert rc == 0


# ---------------------------------------------------------------------------
# main() — JSON output
# ---------------------------------------------------------------------------

class TestMainJsonOutput:
    def test_json_output_is_valid_list(self, tmp_path, capsys):
        make_spec(tmp_path, "lib1", [inv("lib1.a.1", "cat_a", "d")])
        rc = svc.main([str(tmp_path / "lib1.zspec.json"), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)

    def test_json_output_has_expected_keys(self, tmp_path, capsys):
        make_spec(tmp_path, "lib2", [inv("lib2.a.1", "cat_a", "d")])
        svc.main([str(tmp_path / "lib2.zspec.json"), "--json"])
        data = json.loads(capsys.readouterr().out)
        rec = data[0]
        for key in ("spec", "total", "described", "score", "categories"):
            assert key in rec, f"missing key: {key}"
        cat = rec["categories"][0]
        for key in ("name", "total", "described", "score"):
            assert key in cat, f"missing category key: {key}"

    def test_json_category_scores(self, tmp_path, capsys):
        make_spec(tmp_path, "lib3", [
            inv("lib3.a.1", "cat_a", "d"),
            inv("lib3.a.2", "cat_a"),
        ])
        svc.main([str(tmp_path / "lib3.zspec.json"), "--json"])
        data = json.loads(capsys.readouterr().out)
        rec = data[0]
        assert rec["total"] == 2
        assert rec["described"] == 1
        assert rec["score"] == 50.0


# ---------------------------------------------------------------------------
# --min-score filter
# ---------------------------------------------------------------------------

class TestMinScoreFilter:
    def test_min_score_filters_high_coverage(self, tmp_path, capsys):
        # lib_full: 100% described, lib_poor: 0% described
        make_spec(tmp_path, "lib_full", [inv("lf.a.1", "c", "d"), inv("lf.a.2", "c", "d")])
        make_spec(tmp_path, "lib_poor", [inv("lp.a.1", "c"), inv("lp.a.2", "c")])
        specs = [
            str(tmp_path / "lib_full.zspec.json"),
            str(tmp_path / "lib_poor.zspec.json"),
        ]
        svc.main(specs + ["--json", "--min-score", "50"])
        data = json.loads(capsys.readouterr().out)
        names = [r["spec"] for r in data]
        assert "lib_poor" in names
        assert "lib_full" not in names

    def test_min_score_100_shows_all_incomplete(self, tmp_path, capsys):
        make_spec(tmp_path, "lib_partial", [
            inv("lp.a.1", "c", "d"),
            inv("lp.a.2", "c"),
        ])
        svc.main([str(tmp_path / "lib_partial.zspec.json"), "--json", "--min-score", "100"])
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 1
        assert data[0]["spec"] == "lib_partial"

    def test_min_score_0_shows_nothing(self, tmp_path, capsys):
        make_spec(tmp_path, "lib_zero", [inv("lz.a.1", "c")])
        svc.main([str(tmp_path / "lib_zero.zspec.json"), "--json", "--min-score", "0"])
        data = json.loads(capsys.readouterr().out)
        assert data == []


# ---------------------------------------------------------------------------
# Summary totals correctness
# ---------------------------------------------------------------------------

class TestSummaryTotals:
    def test_summary_totals_correct(self, tmp_path, capsys):
        make_spec(tmp_path, "s1", [inv("s1.a.1", "c", "d"), inv("s1.a.2", "c", "d")])
        make_spec(tmp_path, "s2", [inv("s2.a.1", "c", "d"), inv("s2.a.2", "c")])
        specs = sorted(str(p) for p in tmp_path.glob("*.zspec.json"))
        svc.main(specs + ["--json"])
        data = json.loads(capsys.readouterr().out)
        total_inv = sum(r["total"] for r in data)
        total_desc = sum(r["described"] for r in data)
        assert total_inv == 4
        assert total_desc == 3


# ---------------------------------------------------------------------------
# Integration: real _build/zspecs/
# ---------------------------------------------------------------------------

class TestRealSpecs:
    @pytest.fixture(autouse=True)
    def require_compiled_specs(self):
        zspecs_dir = REPO_ROOT / "_build" / "zspecs"
        if not list(zspecs_dir.glob("*.zspec.json")):
            pytest.skip("_build/zspecs/ not compiled — run make compile-zsdl first")

    def test_runs_on_real_specs_exit_0(self, capsys):
        rc = svc.main([])
        assert rc == 0

    def test_json_output_is_valid_on_real_specs(self, capsys):
        svc.main(["--json"])
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_real_specs_have_required_keys(self, capsys):
        svc.main(["--json"])
        data = json.loads(capsys.readouterr().out)
        for rec in data:
            assert "spec" in rec
            assert "total" in rec
            assert "described" in rec
            assert "score" in rec
            assert "categories" in rec

    def test_hashlib_spec_present_and_complete(self, capsys):
        hashlib_path = REPO_ROOT / "_build" / "zspecs" / "hashlib.zspec.json"
        if not hashlib_path.exists():
            pytest.skip("hashlib spec not compiled")
        svc.main([str(hashlib_path), "--json"])
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 1
        rec = data[0]
        assert rec["spec"] == "hashlib"
        assert rec["total"] > 0
        # hashlib spec has all invariants described
        assert rec["score"] == 100.0

    def test_summary_line_in_text_output(self, capsys):
        svc.main([])
        out = capsys.readouterr().out
        assert "Summary:" in out
        assert "specs" in out
        assert "invariants" in out
        assert "described" in out
