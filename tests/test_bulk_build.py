"""
tests/test_bulk_build.py

Tests for tools/bulk_build.py: load_snapshot_index, merge_records, build_one,
and main() entry point.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "bulk_build.py"
_spec = importlib.util.spec_from_file_location("bulk_build", _TOOL)
bulk_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bulk_mod)

load_snapshot_index = bulk_mod.load_snapshot_index
merge_records = bulk_mod.merge_records
build_one = bulk_mod.build_one
main = bulk_mod.main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record(name: str, ecosystem: str = "nixpkgs", confidence: float = 0.8,
            deps: dict | None = None, sources: list | None = None) -> dict:
    return {
        "schema_version": "0.2",
        "identity": {
            "canonical_name": name,
            "canonical_id": f"pkg:{name}",
            "version": "1.0",
            "ecosystem": ecosystem,
        },
        "descriptive": {
            "summary": f"{name} summary",
            "homepage": "",
            "license": [],
            "categories": [],
            "maintainers": ["alice"],
        },
        "conflicts": [],
        "sources": sources or [{"url": f"https://example.com/{name}.tar.gz"}],
        "dependencies": deps or {"build": [], "host": [], "runtime": [], "test": []},
        "build": {"system_kind": "autotools", "configure_args": [], "make_args": []},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": [],
        "tests": {},
        "provenance": {
            "generated_by": "test",
            "imported_at": "2026-01-01",
            "source_path": name,
            "source_repo_commit": None,
            "confidence": confidence,
            "unmapped": [],
            "warnings": [],
        },
        "extensions": {},
    }


def _write(directory: Path, name: str, **kw) -> Path:
    rec = _record(name, **kw)
    p = directory / f"{name}.json"
    p.write_text(json.dumps(rec), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_snapshot_index
# ---------------------------------------------------------------------------

class TestLoadSnapshotIndex:
    def test_indexes_by_canonical_name(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        _write(d, "curl")
        index = load_snapshot_index([d])
        assert "curl" in index
        assert len(index["curl"]) == 1

    def test_skips_manifest(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        (d / "manifest.json").write_text('{"type":"manifest"}')
        _write(d, "curl")
        index = load_snapshot_index([d])
        assert list(index.keys()) == ["curl"]

    def test_skips_invalid_json(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        (d / "bad.json").write_text("not-json")
        index = load_snapshot_index([d])
        assert index == {}

    def test_skips_record_without_identity(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        (d / "no_id.json").write_text('{"foo": "bar"}')
        index = load_snapshot_index([d])
        assert index == {}

    def test_multiple_snapshot_dirs(self, tmp_path):
        d1 = tmp_path / "snap1"
        d2 = tmp_path / "snap2"
        d1.mkdir(); d2.mkdir()
        _write(d1, "curl", ecosystem="freebsd_ports")
        _write(d2, "curl", ecosystem="nixpkgs")
        index = load_snapshot_index([d1, d2])
        assert len(index["curl"]) == 2

    def test_groups_by_canonical_name(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        _write(d, "curl")
        _write(d, "openssl")
        index = load_snapshot_index([d])
        assert set(index.keys()) == {"curl", "openssl"}

    def test_uses_name_field_when_canonical_name_absent(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        rec = _record("curl")
        del rec["identity"]["canonical_name"]
        rec["identity"]["name"] = "curl"
        (d / "curl.json").write_text(json.dumps(rec))
        index = load_snapshot_index([d])
        assert "curl" in index

    def test_skips_nested_without_name(self, tmp_path):
        d = tmp_path / "snap"
        d.mkdir()
        rec = _record("curl")
        del rec["identity"]["canonical_name"]
        # no "name" either
        (d / "curl.json").write_text(json.dumps(rec))
        index = load_snapshot_index([d])
        assert index == {}

    def test_rglob_finds_nested_files(self, tmp_path):
        d = tmp_path / "snap"
        sub = d / "sub"
        sub.mkdir(parents=True)
        _write(sub, "curl")
        index = load_snapshot_index([d])
        assert "curl" in index


# ---------------------------------------------------------------------------
# merge_records
# ---------------------------------------------------------------------------

class TestMergeRecords:
    def test_empty_list_returns_empty(self):
        assert merge_records([]) == {}

    def test_single_record_returned_as_spec(self):
        rec = _record("curl")
        result = merge_records([rec])
        assert result["identity"]["canonical_name"] == "curl"

    def test_uses_highest_confidence_as_base(self):
        low = _record("curl", confidence=0.5)
        low["descriptive"]["summary"] = "low confidence"
        high = _record("curl", confidence=0.9)
        high["descriptive"]["summary"] = "high confidence"
        result = merge_records([low, high])
        assert result["descriptive"]["summary"] == "high confidence"

    def test_unions_sources_by_url(self):
        r1 = _record("curl", sources=[{"url": "https://a.example/curl.tar.gz"}])
        r2 = _record("curl", sources=[{"url": "https://b.example/curl.tar.gz"}])
        result = merge_records([r1, r2])
        urls = {s["url"] for s in result["sources"]}
        assert "https://a.example/curl.tar.gz" in urls
        assert "https://b.example/curl.tar.gz" in urls

    def test_no_duplicate_sources(self):
        same_url = "https://example.com/curl.tar.gz"
        r1 = _record("curl", sources=[{"url": same_url}])
        r2 = _record("curl", sources=[{"url": same_url}])
        result = merge_records([r1, r2])
        assert len(result["sources"]) == 1

    def test_unions_deps_across_buckets(self):
        r1 = _record("curl", deps={"build": ["cmake"], "host": [], "runtime": [], "test": []})
        r2 = _record("curl", deps={"build": [], "host": ["zlib"], "runtime": ["openssl"], "test": []})
        result = merge_records([r1, r2])
        assert "cmake" in result["dependencies"]["build"]
        assert "zlib" in result["dependencies"]["host"]
        assert "openssl" in result["dependencies"]["runtime"]

    def test_no_duplicate_deps(self):
        r1 = _record("curl", deps={"build": ["cmake"], "host": [], "runtime": [], "test": []})
        r2 = _record("curl", deps={"build": ["cmake"], "host": [], "runtime": [], "test": []})
        result = merge_records([r1, r2])
        assert result["dependencies"]["build"].count("cmake") == 1

    def test_unions_maintainers(self):
        r1 = _record("curl")
        r1["descriptive"]["maintainers"] = ["alice"]
        r2 = _record("curl")
        r2["descriptive"]["maintainers"] = ["bob"]
        result = merge_records([r1, r2])
        maintainers = result["descriptive"]["maintainers"]
        assert "alice" in maintainers
        assert "bob" in maintainers

    def test_unions_conflicts(self):
        r1 = _record("curl")
        r1["conflicts"] = ["libcurl-compat"]
        r2 = _record("curl")
        r2["conflicts"] = ["curl-legacy"]
        result = merge_records([r1, r2])
        assert "libcurl-compat" in result["conflicts"]
        assert "curl-legacy" in result["conflicts"]

    def test_records_merged_from_ecosystems(self):
        r1 = _record("curl", ecosystem="freebsd_ports")
        r2 = _record("curl", ecosystem="nixpkgs")
        result = merge_records([r1, r2])
        assert "freebsd_ports" in result["extensions"]["merged_from"]
        assert "nixpkgs" in result["extensions"]["merged_from"]

    def test_deep_copy_does_not_mutate_input(self):
        r1 = _record("curl")
        original_sources = list(r1["sources"])
        r2 = _record("curl", sources=[{"url": "https://other.example/curl.tar.gz"}])
        merge_records([r1, r2])
        assert r1["sources"] == original_sources


# ---------------------------------------------------------------------------
# build_one
# ---------------------------------------------------------------------------

class TestBuildOne:
    def _minimal_cfg(self) -> dict:
        return {"targets": [], "artifact_store": {"url": "", "cache_generated_sources": False}}

    def test_returns_result_dict_structure(self, tmp_path):
        records = [_record("curl")]
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": lambda s: {"Makefile": "content"}}):
            result = build_one("curl", records, ["freebsd_ports"], self._minimal_cfg(), tmp_path, dry_run=True)
        assert "name" in result
        assert "drivers" in result
        assert "errors" in result

    def test_dry_run_skips_driver(self, tmp_path):
        records = [_record("curl")]
        called = []
        def fake_driver(spec):
            called.append(spec)
            return {"Makefile": "x"}
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            result = build_one("curl", records, ["freebsd_ports"], self._minimal_cfg(), tmp_path, dry_run=True)
        assert called == []
        assert result["drivers"]["freebsd_ports"] == "dry-run"

    def test_empty_records_produces_error(self, tmp_path):
        result = build_one("curl", [], ["freebsd_ports"], self._minimal_cfg(), tmp_path, dry_run=False)
        assert result["errors"]

    def test_unknown_driver_produces_error(self, tmp_path):
        records = [_record("curl")]
        result = build_one("curl", records, ["no_such_driver"], self._minimal_cfg(), tmp_path, dry_run=False)
        assert any("unknown driver" in e for e in result["errors"])

    def test_spec_written_to_specs_dir(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "content"}
        cfg = self._minimal_cfg()
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        assert (tmp_path / "curl.json").exists()

    def test_spec_written_even_without_target(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "content"}
        cfg = self._minimal_cfg()  # no targets
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            result = build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        assert (tmp_path / "curl.json").exists()
        assert result["drivers"]["freebsd_ports"] == "generated"

    def test_output_files_written_by_driver(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "PORTNAME=curl\n", "distinfo": "SHA256= abc\n"}
        cfg = self._minimal_cfg()
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        out_dir = Path("output") / "freebsd_ports" / "curl"
        assert (out_dir / "Makefile").exists()
        assert (out_dir / "distinfo").exists()

    def test_driver_exception_recorded_as_error(self, tmp_path):
        records = [_record("curl")]
        def bad_driver(spec):
            raise RuntimeError("explode")
        cfg = self._minimal_cfg()
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": bad_driver}):
            result = build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        assert any("driver error" in e for e in result["errors"])

    def test_build_dispatched_to_target(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "content"}
        target = {"name": "freebsd.local", "driver": "freebsd_ports", "host": "freebsd.local"}
        cfg = {"targets": [target], "artifact_store": {"url": "", "cache_generated_sources": False}}
        mock_res = MagicMock(success=True, returncode=0, stderr="")
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            with patch("theseus.remote.build_on_target", return_value=mock_res) as mock_build:
                result = build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        mock_build.assert_called_once()
        assert result["drivers"]["freebsd_ports"] == "ok"

    def test_build_failure_recorded(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "content"}
        target = {"name": "freebsd.local", "driver": "freebsd_ports", "host": "freebsd.local"}
        cfg = {"targets": [target], "artifact_store": {"url": "", "cache_generated_sources": False}}
        mock_res = MagicMock(success=False, returncode=1, stderr="build failed")
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            with patch("theseus.remote.build_on_target", return_value=mock_res):
                result = build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        assert result["drivers"]["freebsd_ports"] == "failed"

    def test_store_called_when_cache_enabled(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "content"}
        cfg = {"targets": [], "artifact_store": {"url": "s3://bucket", "cache_generated_sources": True}}
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            with patch("theseus.store.store", return_value=(True, "")) as mock_store:
                build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        mock_store.assert_called_once()

    def test_store_not_called_when_cache_disabled(self, tmp_path):
        records = [_record("curl")]
        def fake_driver(spec):
            return {"Makefile": "content"}
        cfg = {"targets": [], "artifact_store": {"url": "s3://bucket", "cache_generated_sources": False}}
        with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": fake_driver}):
            with patch("theseus.store.store", return_value=(True, "")) as mock_store:
                build_one("curl", records, ["freebsd_ports"], cfg, tmp_path, dry_run=False)
        mock_store.assert_not_called()


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    def _write_ranked(self, path: Path, entries: list[dict]) -> None:
        path.write_text(json.dumps(entries), encoding="utf-8")

    def _ranked_entry(self, name: str, ref_count: int = 10,
                      in_snapshot: bool = True, ecosystems: list | None = None) -> dict:
        return {
            "canonical_name": name,
            "ref_count": ref_count,
            "in_snapshot": in_snapshot,
            "ecosystems": ecosystems or ["nixpkgs"],
        }

    def test_no_candidates_returns_1(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        self._write_ranked(ranked, [])
        snap = tmp_path / "snap"
        snap.mkdir()
        rc = main([str(ranked), str(snap)])
        assert rc == 1

    def test_min_refs_filters_low_count(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        self._write_ranked(ranked, [self._ranked_entry("curl", ref_count=1)])
        snap = tmp_path / "snap"
        snap.mkdir()
        rc = main([str(ranked), str(snap), "--min-refs", "5"])
        assert rc == 1

    def test_not_in_snapshot_filtered(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        self._write_ranked(ranked, [self._ranked_entry("curl", in_snapshot=False)])
        snap = tmp_path / "snap"
        snap.mkdir()
        rc = main([str(ranked), str(snap)])
        assert rc == 1

    def test_ecosystem_filter_applied(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        self._write_ranked(ranked, [self._ranked_entry("curl", ecosystems=["freebsd_ports"])])
        snap = tmp_path / "snap"
        snap.mkdir()
        rc = main([str(ranked), str(snap), "--ecosystems", "nixpkgs"])
        assert rc == 1

    def test_dry_run_returns_0(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        self._write_ranked(ranked, [self._ranked_entry("curl")])
        snap = tmp_path / "snap"
        snap.mkdir()
        _write(snap, "curl")
        with patch("theseus.config.load", return_value={"targets": [], "artifact_store": {}}):
            with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": lambda s: {}}):
                rc = main([str(ranked), str(snap), "--dry-run",
                           "--drivers", "freebsd_ports", "--top", "1"])
        assert rc == 0

    def test_top_limits_candidates(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        entries = [self._ranked_entry(f"pkg{i}", ref_count=10) for i in range(10)]
        self._write_ranked(ranked, entries)
        snap = tmp_path / "snap"
        snap.mkdir()
        for i in range(10):
            _write(snap, f"pkg{i}")

        processed = []
        def fake_build_one(name, *args, **kwargs):
            processed.append(name)
            return {"name": name, "drivers": {}, "errors": []}

        with patch("theseus.config.load", return_value={"targets": [], "artifact_store": {}}):
            with patch.object(bulk_mod, "build_one", side_effect=fake_build_one):
                main([str(ranked), str(snap), "--top", "3", "--dry-run"])

        assert len(processed) == 3

    def test_specs_dir_created(self, tmp_path):
        ranked = tmp_path / "ranked.json"
        self._write_ranked(ranked, [self._ranked_entry("curl")])
        snap = tmp_path / "snap"
        snap.mkdir()
        specs = tmp_path / "specs_out"

        with patch("theseus.config.load", return_value={"targets": [], "artifact_store": {}}):
            with patch.object(bulk_mod, "_REPO_ROOT", tmp_path):
                with patch.dict(bulk_mod.DRIVERS, {"freebsd_ports": lambda s: {}}):
                    main([str(ranked), str(snap), "--dry-run",
                          "--drivers", "freebsd_ports"])
        # specs dir is created under _REPO_ROOT/specs
        assert (tmp_path / "specs").is_dir()
