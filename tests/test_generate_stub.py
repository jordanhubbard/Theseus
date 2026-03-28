"""
Tests for tools/generate_stub.py
"""
import json
import sys
from pathlib import Path

import pytest

# tools/ is already in sys.path via conftest.py
import generate_stub
from theseus.importer import SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_record(name: str = "mypkg", ecosystem: str = "nixpkgs",
                    confidence: float = 0.9, maintainers=None,
                    conflicts=None) -> dict:
    return {
        "schema_version": "0.2",
        "identity": {
            "canonical_name": name,
            "canonical_id": f"{name}-1.0.0",
            "version": "1.0.0",
            "ecosystem": ecosystem,
            "ecosystem_id": name,
        },
        "descriptive": {
            "summary": f"Summary for {name}",
            "homepage": "https://example.com",
            "categories": ["devel"],
            "maintainers": maintainers if maintainers is not None else ["alice@example.com"],
            "license": ["MIT"],
        },
        "sources": [
            {
                "type": "archive",
                "url": f"https://example.com/{name}-1.0.0.tar.gz",
                "sha256": "deadbeef",
            }
        ],
        "dependencies": {"build": [], "host": [], "runtime": [], "test": []},
        "build": {"system_kind": "autotools"},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "conflicts": conflicts if conflicts is not None else [],
        "patches": [],
        "tests": {},
        "provenance": {"confidence": confidence, "warnings": []},
        "extensions": {},
    }


def _write_records(snapshot_dir: Path, records: list[dict]) -> None:
    for rec in records:
        name = rec["identity"]["canonical_name"]
        eco = rec["identity"]["ecosystem"]
        eco_dir = snapshot_dir / eco
        eco_dir.mkdir(parents=True, exist_ok=True)
        (eco_dir / f"{name}.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_main_produces_stub_files(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("libfoo")])

    rc = generate_stub.main([str(snap), "--out", str(out)])

    assert rc == 0
    stub_file = out / "libfoo.json"
    assert stub_file.exists()


def test_stub_has_stub_true(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("libfoo")])

    generate_stub.main([str(snap), "--out", str(out)])

    stub = json.loads((out / "libfoo.json").read_text())
    assert stub.get("stub") is True


def test_stub_has_provenance_warning(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("libfoo")])

    generate_stub.main([str(snap), "--out", str(out)])

    stub = json.loads((out / "libfoo.json").read_text())
    warnings = stub.get("provenance", {}).get("warnings", [])
    assert any("generated stub" in w for w in warnings)


def test_stub_has_current_schema_version(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("libfoo")])

    generate_stub.main([str(snap), "--out", str(out)])

    stub = json.loads((out / "libfoo.json").read_text())
    assert stub["schema_version"] == SCHEMA_VERSION


def test_multi_ecosystem_merges_maintainers(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    rec_nix = _minimal_record("libfoo", ecosystem="nixpkgs",
                               maintainers=["alice@example.com"], confidence=0.9)
    rec_bsd = _minimal_record("libfoo", ecosystem="freebsd_ports",
                               maintainers=["bob@example.com"], confidence=0.7)
    _write_records(snap, [rec_nix, rec_bsd])

    generate_stub.main([str(snap), "--out", str(out)])

    stub = json.loads((out / "libfoo.json").read_text())
    maintainers = stub["descriptive"]["maintainers"]
    assert "alice@example.com" in maintainers
    assert "bob@example.com" in maintainers


def test_multi_ecosystem_merges_conflicts(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    rec_nix = _minimal_record("libfoo", ecosystem="nixpkgs",
                               conflicts=["conflictA"], confidence=0.9)
    rec_bsd = _minimal_record("libfoo", ecosystem="freebsd_ports",
                               conflicts=["conflictB"], confidence=0.7)
    _write_records(snap, [rec_nix, rec_bsd])

    generate_stub.main([str(snap), "--out", str(out)])

    stub = json.loads((out / "libfoo.json").read_text())
    assert "conflictA" in stub["conflicts"]
    assert "conflictB" in stub["conflicts"]


def test_highest_confidence_is_base(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    rec_low = _minimal_record("libfoo", ecosystem="nixpkgs", confidence=0.3)
    rec_high = _minimal_record("libfoo", ecosystem="freebsd_ports", confidence=0.95)
    rec_high["descriptive"]["summary"] = "High confidence summary"
    _write_records(snap, [rec_low, rec_high])

    generate_stub.main([str(snap), "--out", str(out)])

    stub = json.loads((out / "libfoo.json").read_text())
    assert stub["descriptive"]["summary"] == "High confidence summary"


def test_driver_flag_produces_output_files(tmp_path, monkeypatch):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("libfoo")])

    # Run from tmp_path so output/ is created there
    monkeypatch.chdir(tmp_path)
    generate_stub.main([str(snap), "--out", str(out), "--driver", "freebsd_ports"])

    # Check output files created
    output_dir = tmp_path / "output" / "freebsd_ports" / "libfoo"
    assert output_dir.exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "distinfo").exists()
    assert (output_dir / "pkg-descr").exists()


def test_driver_both_produces_both_outputs(tmp_path, monkeypatch):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("libfoo")])

    monkeypatch.chdir(tmp_path)
    generate_stub.main([str(snap), "--out", str(out), "--driver", "both"])

    assert (tmp_path / "output" / "freebsd_ports" / "libfoo" / "Makefile").exists()
    assert (tmp_path / "output" / "nixpkgs" / "libfoo" / "default.nix").exists()


def test_missing_snapshot_returns_error(tmp_path):
    rc = generate_stub.main([str(tmp_path / "nonexistent"), "--out", str(tmp_path / "out")])
    assert rc != 0


def test_multiple_packages_all_written(tmp_path):
    snap = tmp_path / "snap"
    out = tmp_path / "stubs"
    _write_records(snap, [_minimal_record("pkg-a"), _minimal_record("pkg-b")])

    generate_stub.main([str(snap), "--out", str(out)])

    assert (out / "pkg-a.json").exists()
    assert (out / "pkg-b.json").exists()
