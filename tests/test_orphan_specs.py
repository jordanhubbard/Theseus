"""
Tests for tools/orphan_specs.py.

Exercises load_spec_names, load_extraction_canonical_names, build_report,
and main() using synthetic tmp_path fixtures plus the real examples/ directory.
"""
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import orphan_specs as os_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_zspec(tmp_path: Path, name: str) -> Path:
    """Write a minimal compiled zspec and return its path."""
    data = {
        "identity": {"canonical_name": name},
        "library": {"name": name},
        "invariants": [],
    }
    path = tmp_path / f"{name}.zspec.json"
    path.write_text(json.dumps(data))
    return path


def write_record(tmp_path: Path, name: str) -> Path:
    """Write a minimal extraction record and return its path."""
    data = {"identity": {"canonical_name": name}}
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# load_spec_names
# ---------------------------------------------------------------------------

class TestLoadSpecNames:
    def test_returns_names(self, tmp_path):
        write_zspec(tmp_path, "alpha")
        write_zspec(tmp_path, "beta")
        with mock.patch.object(os_mod, "ZSPECS_DIR", tmp_path):
            names = os_mod.load_spec_names()
        assert "alpha" in names
        assert "beta" in names

    def test_skips_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.zspec.json"
        bad.write_text("{not valid json}")
        write_zspec(tmp_path, "good")
        with mock.patch.object(os_mod, "ZSPECS_DIR", tmp_path):
            names = os_mod.load_spec_names()
        assert names == ["good"]

    def test_skips_non_dict(self, tmp_path):
        arr = tmp_path / "arr.zspec.json"
        arr.write_text("[1, 2, 3]")
        write_zspec(tmp_path, "good")
        with mock.patch.object(os_mod, "ZSPECS_DIR", tmp_path):
            names = os_mod.load_spec_names()
        assert names == ["good"]

    def test_empty_dir_returns_empty(self, tmp_path):
        with mock.patch.object(os_mod, "ZSPECS_DIR", tmp_path):
            assert os_mod.load_spec_names() == []


# ---------------------------------------------------------------------------
# load_extraction_canonical_names
# ---------------------------------------------------------------------------

class TestLoadExtractionCanonicalNames:
    def test_collects_names(self, tmp_path):
        write_record(tmp_path, "zlib")
        write_record(tmp_path, "curl")
        names = os_mod.load_extraction_canonical_names(tmp_path)
        assert names == {"zlib", "curl"}

    def test_skips_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{nope}")
        write_record(tmp_path, "good")
        names = os_mod.load_extraction_canonical_names(tmp_path)
        assert names == {"good"}

    def test_empty_dir_returns_empty_set(self, tmp_path):
        names = os_mod.load_extraction_canonical_names(tmp_path)
        assert names == set()


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_no_orphans(self):
        report = os_mod.build_report(["alpha", "beta"], {"alpha", "beta", "gamma"})
        assert report["orphan_count"] == 0
        assert report["matched"] == 2
        assert report["total_specs"] == 2

    def test_all_orphans(self):
        report = os_mod.build_report(["alpha", "beta"], set())
        assert report["orphan_count"] == 2
        assert report["matched"] == 0

    def test_mixed(self):
        report = os_mod.build_report(["zlib", "curl", "orphaned"], {"zlib", "curl"})
        assert report["orphan_count"] == 1
        assert report["matched"] == 2
        assert "orphaned" in report["orphan_list"]
        assert "zlib" in report["matched_list"]

    def test_empty_spec_names(self):
        report = os_mod.build_report([], {"zlib"})
        assert report["total_specs"] == 0
        assert report["orphan_count"] == 0
        assert report["matched"] == 0


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_no_orphans_exits_0(self, tmp_path):
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        write_zspec(zspecs, "zlib")
        write_record(extractions, "zlib")
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            rc = os_mod.main([str(extractions)])
        assert rc == 0

    def test_orphans_exits_1(self, tmp_path):
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        write_zspec(zspecs, "orphan_lib")
        # No matching extraction record
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            rc = os_mod.main([str(extractions)])
        assert rc == 1

    def test_nonexistent_extraction_dir_exits_2(self, tmp_path):
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        write_zspec(zspecs, "zlib")
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            rc = os_mod.main([str(tmp_path / "does_not_exist")])
        assert rc == 2

    def test_missing_zspecs_dir_exits_2(self, tmp_path, capsys):
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        nonexistent = tmp_path / "no_zspecs"
        with mock.patch.object(os_mod, "ZSPECS_DIR", nonexistent):
            rc = os_mod.main([str(extractions)])
        assert rc == 2
        captured = capsys.readouterr()
        assert "compile-zsdl" in captured.err

    def test_json_output_format(self, tmp_path, capsys):
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        write_zspec(zspecs, "alpha")
        write_zspec(zspecs, "beta")
        write_record(extractions, "alpha")
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            rc = os_mod.main([str(extractions), "--json"])
        assert rc == 1
        data = json.loads(capsys.readouterr().out)
        assert "total_specs" in data
        assert "matched" in data
        assert "orphan_count" in data
        assert "orphan_list" in data
        assert "matched_list" in data
        assert data["orphan_count"] == 1
        assert "beta" in data["orphan_list"]

    def test_text_output_contains_summary(self, tmp_path, capsys):
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        write_zspec(zspecs, "zlib")
        write_record(extractions, "zlib")
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            os_mod.main([str(extractions)])
        out = capsys.readouterr().out
        assert "Total specs" in out
        assert "Matched" in out
        assert "Orphan" in out

    def test_known_matched_not_orphaned(self, tmp_path):
        """A spec whose canonical_name exists in records must NOT appear in orphan_list."""
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        write_zspec(zspecs, "zlib")
        write_record(extractions, "zlib")
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            rc = os_mod.main([str(extractions), "--json"])
        assert rc == 0

    def test_known_absent_is_orphaned(self, tmp_path):
        """A spec whose canonical_name is absent from all records IS an orphan."""
        zspecs = tmp_path / "zspecs"
        zspecs.mkdir()
        extractions = tmp_path / "extractions"
        extractions.mkdir()
        write_zspec(zspecs, "mystery_lib")
        write_record(extractions, "unrelated_lib")
        with mock.patch.object(os_mod, "ZSPECS_DIR", zspecs):
            rc = os_mod.main([str(extractions), "--json"])
        assert rc == 1


# ---------------------------------------------------------------------------
# Integration with examples/ directory
# ---------------------------------------------------------------------------

class TestWithExamples:
    def test_examples_freebsd_ports_zlib_not_orphaned(self):
        """zlib has both a compiled spec and a record in examples/freebsd_ports/."""
        examples_dir = REPO_ROOT / "examples" / "freebsd_ports"
        if not examples_dir.is_dir():
            pytest.skip("examples/freebsd_ports not present")
        if not (REPO_ROOT / "_build" / "zspecs" / "zlib.zspec.json").exists():
            pytest.skip("_build/zspecs/zlib.zspec.json not compiled")
        # Temporarily limit ZSPECS_DIR to only zlib so we get a deterministic result
        zspecs = REPO_ROOT / "_build" / "zspecs"
        extraction_names = os_mod.load_extraction_canonical_names(examples_dir)
        assert "zlib" in extraction_names, "zlib should be in freebsd_ports examples"
        spec_names = os_mod.load_spec_names()
        assert "zlib" in spec_names, "zlib should be a compiled spec"
        report = os_mod.build_report(["zlib"], extraction_names)
        assert report["orphan_count"] == 0
        assert "zlib" in report["matched_list"]
