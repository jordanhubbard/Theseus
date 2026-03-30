"""
Tests for tools/overlap_report.py.
"""
import json
import sys
from pathlib import Path

import overlap_report


def _make_record(name, ecosystem, version, confidence=0.9):
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
        "dependencies": {"build": [], "host": [], "runtime": [], "test": []},
        "build": {"system_kind": "autotools"},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": [],
        "tests": {},
        "provenance": {"confidence": confidence, "generated_by": "test"},
        "extensions": {},
    }


def _write(tmp_dir, records):
    for i, rec in enumerate(records):
        name = rec["identity"]["canonical_name"]
        eco = rec["identity"]["ecosystem"]
        (tmp_dir / f"{name}_{eco}_{i}.json").write_text(json.dumps(rec), encoding="utf-8")


def _run_main(snapshot, out):
    sys.argv = ["overlap_report.py", str(snapshot), "--out", str(out)]
    overlap_report.main()


# --- load_records ---

def test_load_records_empty(tmp_path):
    assert list(overlap_report.load_records(tmp_path)) == []


def test_load_records_finds_valid_record(tmp_path):
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    (tmp_path / "zlib.json").write_text(json.dumps(rec), encoding="utf-8")
    results = list(overlap_report.load_records(tmp_path))
    assert len(results) == 1


def test_load_records_skips_manifest(tmp_path):
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    (tmp_path / "manifest.json").write_text(json.dumps(rec), encoding="utf-8")
    assert list(overlap_report.load_records(tmp_path)) == []


def test_load_records_skips_invalid_json(tmp_path):
    (tmp_path / "bad.json").write_text("not valid json", encoding="utf-8")
    assert list(overlap_report.load_records(tmp_path)) == []


def test_load_records_skips_non_identity_records(tmp_path):
    (tmp_path / "other.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    assert list(overlap_report.load_records(tmp_path)) == []


def test_load_records_recurses_subdirs(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    (sub / "zlib.json").write_text(json.dumps(rec), encoding="utf-8")
    results = list(overlap_report.load_records(tmp_path))
    assert len(results) == 1


# --- overlap detection ---

def test_overlap_both_ecosystems(tmp_path):
    _write(tmp_path, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("zlib", "freebsd_ports", "1.3.1"),
    ])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["overlap_count"] == 1
    assert summary["packages_total"] == 1
    assert summary["only_nix_count"] == 0
    assert summary["only_ports_count"] == 0


def test_only_nix(tmp_path):
    _write(tmp_path, [_make_record("nix-only", "nixpkgs", "1.0")])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["only_nix_count"] == 1
    assert summary["overlap_count"] == 0
    only_nix = json.loads((out / "only_nix.json").read_text())
    assert "nix-only" in only_nix


def test_only_ports(tmp_path):
    _write(tmp_path, [_make_record("ports-only", "freebsd_ports", "1.0")])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["only_ports_count"] == 1
    only_ports = json.loads((out / "only_ports.json").read_text())
    assert "ports-only" in only_ports


def test_version_skew_detected(tmp_path):
    _write(tmp_path, [
        _make_record("curl", "nixpkgs", "8.5.0"),
        _make_record("curl", "freebsd_ports", "8.4.0"),
    ])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["version_skew_count"] == 1
    skew = json.loads((out / "version_skew.json").read_text())
    assert "curl" in skew


def test_no_version_skew_when_versions_match(tmp_path):
    _write(tmp_path, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("zlib", "freebsd_ports", "1.3.1"),
    ])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["version_skew_count"] == 0


def test_output_files_created(tmp_path):
    _write(tmp_path, [_make_record("pkg", "nixpkgs", "1.0")])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    for fname in ("summary.json", "overlap.json", "only_nix.json", "only_ports.json", "version_skew.json"):
        assert (out / fname).exists(), f"Expected output file {fname} not created"


def test_mixed_ecosystem_packages(tmp_path):
    _write(tmp_path, [
        _make_record("shared", "nixpkgs", "2.0"),
        _make_record("shared", "freebsd_ports", "2.0"),
        _make_record("nix-extra", "nixpkgs", "1.0"),
        _make_record("ports-extra", "freebsd_ports", "1.0"),
    ])
    out = tmp_path / "out"
    _run_main(tmp_path, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["packages_total"] == 3
    assert summary["overlap_count"] == 1
    assert summary["only_nix_count"] == 1
    assert summary["only_ports_count"] == 1
