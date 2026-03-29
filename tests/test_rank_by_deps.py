"""Tests for tools/rank_by_deps.py"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib.util

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "rank_by_deps.py"
spec = importlib.util.spec_from_file_location("rank_by_deps", _TOOL)
rank_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rank_mod)

load_records = rank_mod.load_records


def write_rec(path: Path, name: str, eco: str, deps: dict) -> None:
    path.write_text(json.dumps({
        "identity": {"canonical_name": name, "ecosystem": eco, "version": "1.0"},
        "dependencies": deps,
        "provenance": {"confidence": 0.9},
    }), encoding="utf-8")


# ---------------------------------------------------------------------------
# load_records
# ---------------------------------------------------------------------------

class TestLoadRecords:
    def test_yields_valid_records(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        write_rec(d / "a.json", "aaa", "nixpkgs", {})
        records = list(load_records([d]))
        assert len(records) == 1

    def test_skips_manifest(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        (d / "manifest.json").write_text('{"type":"manifest"}')
        write_rec(d / "a.json", "aaa", "nixpkgs", {})
        records = list(load_records([d]))
        assert len(records) == 1

    def test_skips_invalid_json(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        (d / "bad.json").write_text("not json")
        records = list(load_records([d]))
        assert records == []

    def test_multiple_snapshot_dirs(self, tmp_path):
        d1 = tmp_path / "s1"; d1.mkdir()
        d2 = tmp_path / "s2"; d2.mkdir()
        write_rec(d1 / "a.json", "aaa", "nixpkgs", {})
        write_rec(d2 / "b.json", "bbb", "freebsd_ports", {})
        records = list(load_records([d1, d2]))
        assert len(records) == 2

    def test_recurses_into_subdirs(self, tmp_path):
        sub = tmp_path / "snap" / "nixpkgs"; sub.mkdir(parents=True)
        write_rec(sub / "a.json", "aaa", "nixpkgs", {})
        records = list(load_records([tmp_path / "snap"]))
        assert len(records) == 1


# ---------------------------------------------------------------------------
# ref_count logic (via main with --out)
# ---------------------------------------------------------------------------

class TestRefCounting:
    def _run(self, snap: Path, out: Path, extra_args=None):
        """Call main() programmatically via argv."""
        import sys as _sys
        old = _sys.argv
        argv = ["rank_by_deps.py", str(snap), "--out", str(out)]
        if extra_args:
            argv += extra_args
        _sys.argv = argv
        try:
            rank_mod.main()
        except SystemExit:
            pass
        finally:
            _sys.argv = old
        if out.exists():
            return json.loads(out.read_text())
        return []

    def test_basic_ref_count(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        # pkg_a and pkg_b both depend on zlib
        write_rec(snap / "a.json", "pkg_a", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "b.json", "pkg_b", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "z.json", "zlib",  "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out)
        by_name = {r["canonical_name"]: r for r in result}
        assert by_name["zlib"]["ref_count"] == 2

    def test_deduplication_within_record(self, tmp_path):
        # same dep appearing in build AND host should only count once per record
        snap = tmp_path / "snap"; snap.mkdir()
        write_rec(snap / "a.json", "pkg_a", "nixpkgs",
                  {"build": ["zlib"], "host": ["zlib"]})
        write_rec(snap / "z.json", "zlib", "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out)
        by_name = {r["canonical_name"]: r for r in result}
        assert by_name["zlib"]["ref_count"] == 1

    def test_sorted_descending(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        write_rec(snap / "a.json", "a", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "b.json", "b", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "c.json", "c", "nixpkgs", {"host": ["zlib", "openssl"]})
        write_rec(snap / "z.json", "zlib",    "nixpkgs", {})
        write_rec(snap / "o.json", "openssl", "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out)
        counts = [r["ref_count"] for r in result]
        assert counts == sorted(counts, reverse=True)

    def test_min_refs_filter(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        write_rec(snap / "a.json", "a", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "z.json", "zlib", "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out, ["--min-refs", "2"])
        # zlib only has 1 ref, should be excluded
        assert all(r["canonical_name"] != "zlib" for r in result)

    def test_top_limits_output(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        for i in range(10):
            write_rec(snap / f"p{i}.json", f"pkg{i}", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "z.json", "zlib", "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out, ["--top", "1"])
        assert len(result) == 1

    def test_in_snapshot_flag(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        # zlib is in snapshot; some-external-dep is not
        write_rec(snap / "a.json", "a", "nixpkgs", {"host": ["zlib", "some-external-dep"]})
        write_rec(snap / "z.json", "zlib", "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out, ["--min-refs", "1"])
        by_name = {r["canonical_name"]: r for r in result}
        assert by_name["zlib"]["in_snapshot"] is True
        assert by_name["some-external-dep"]["in_snapshot"] is False

    def test_cross_ecosystem_refs_tracked(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        write_rec(snap / "a.json", "a", "nixpkgs",      {"host": ["zlib"]})
        write_rec(snap / "b.json", "b", "freebsd_ports", {"host": ["zlib"]})
        write_rec(snap / "z.json", "zlib", "nixpkgs", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out)
        by_name = {r["canonical_name"]: r for r in result}
        refs = by_name["zlib"]["refs_by_ecosystem"]
        assert refs.get("nixpkgs") == 1
        assert refs.get("freebsd_ports") == 1
        assert by_name["zlib"]["ref_count"] == 2

    def test_ecosystems_field_reflects_snapshot(self, tmp_path):
        snap = tmp_path / "snap"; snap.mkdir()
        write_rec(snap / "a.json", "a", "nixpkgs", {"host": ["zlib"]})
        write_rec(snap / "z_nix.json", "zlib", "nixpkgs",      {})
        write_rec(snap / "z_bsd.json", "zlib", "freebsd_ports", {})
        out = tmp_path / "ranked.json"
        result = self._run(snap, out)
        by_name = {r["canonical_name"]: r for r in result}
        assert set(by_name["zlib"]["ecosystems"]) == {"nixpkgs", "freebsd_ports"}
