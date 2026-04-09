"""
tests/test_extract_candidates.py

Unit tests for tools/extract_candidates.py (Phase Z extraction).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import extract_candidates as ec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record(
    name: str,
    ecosystem: str,
    version: str = "1.0",
    confidence: float = 0.8,
    license: list[str] | None = None,
    runtime_deps: list[str] | None = None,
    maintainers: list[str] | None = None,
    deprecated: bool = False,
    conflicts: list[str] | None = None,
    platforms_include: list[str] | None = None,
    source_url: str | None = None,
) -> dict:
    return {
        "schema_version": "0.2",
        "identity": {
            "canonical_name": name,
            "canonical_id": f"pkg:{name}",
            "ecosystem": ecosystem,
            "ecosystem_id": f"{ecosystem}/{name}",
            "version": version,
        },
        "descriptive": {
            "summary": f"{name} summary",
            "homepage": f"https://{name}.example.com/",
            "license": license if license is not None else ["MIT"],
            "categories": [],
            "maintainers": maintainers if maintainers is not None else [],
            "deprecated": deprecated,
        },
        "conflicts": conflicts if conflicts is not None else [],
        "sources": [{"type": "archive", "url": source_url}] if source_url else [],
        "dependencies": {
            "build": [],
            "host": [],
            "runtime": runtime_deps if runtime_deps is not None else [],
            "test": [],
        },
        "build": {},
        "features": {},
        "platforms": {"include": platforms_include or [], "exclude": []},
        "patches": [],
        "tests": {},
        "provenance": {
            "generated_by": "test",
            "imported_at": "2026-01-01T00:00:00Z",
            "source_path": "",
            "source_repo_commit": None,
            "confidence": confidence,
            "unmapped": [],
            "warnings": [],
        },
        "extensions": {},
    }


# ---------------------------------------------------------------------------
# _version_info
# ---------------------------------------------------------------------------

def test_version_info_agreement():
    recs = [
        _record("zlib", "nixpkgs", version="1.3"),
        _record("zlib", "freebsd_ports", version="1.3"),
    ]
    agreement, by_eco = ec._version_info(recs)
    assert agreement is True
    assert by_eco == {"nixpkgs": "1.3", "freebsd_ports": "1.3"}


def test_version_info_skew():
    recs = [
        _record("zlib", "nixpkgs", version="1.3.1"),
        _record("zlib", "freebsd_ports", version="1.3.0"),
    ]
    agreement, by_eco = ec._version_info(recs)
    assert agreement is False
    assert by_eco["nixpkgs"] == "1.3.1"
    assert by_eco["freebsd_ports"] == "1.3.0"


def test_version_info_single_record():
    recs = [_record("zlib", "nixpkgs", version="1.3")]
    agreement, by_eco = ec._version_info(recs)
    assert agreement is True


# ---------------------------------------------------------------------------
# _dep_union
# ---------------------------------------------------------------------------

def test_dep_union_merges_runtime():
    recs = [
        _record("curl", "nixpkgs", runtime_deps=["zlib", "openssl"]),
        _record("curl", "freebsd_ports", runtime_deps=["openssl", "ca_root_nss"]),
    ]
    union = ec._dep_union(recs)
    assert set(union["runtime"]) == {"zlib", "openssl", "ca_root_nss"}


def test_dep_union_empty_when_no_deps():
    recs = [
        _record("zlib", "nixpkgs"),
        _record("zlib", "freebsd_ports"),
    ]
    union = ec._dep_union(recs)
    assert union == {"build": [], "host": [], "runtime": [], "test": []}


def test_dep_union_no_duplicates():
    recs = [
        _record("pkg", "nixpkgs", runtime_deps=["libc"]),
        _record("pkg", "freebsd_ports", runtime_deps=["libc"]),
    ]
    union = ec._dep_union(recs)
    assert union["runtime"] == ["libc"]


# ---------------------------------------------------------------------------
# _license_info
# ---------------------------------------------------------------------------

def test_license_info_agreement():
    recs = [
        _record("zlib", "nixpkgs", license=["Zlib"]),
        _record("zlib", "freebsd_ports", license=["Zlib"]),
    ]
    agreement, by_eco = ec._license_info(recs)
    assert agreement is True


def test_license_info_disagreement():
    recs = [
        _record("pkg", "nixpkgs", license=["MIT"]),
        _record("pkg", "freebsd_ports", license=["BSD-2-Clause"]),
    ]
    agreement, by_eco = ec._license_info(recs)
    assert agreement is False
    assert by_eco["nixpkgs"] == ["MIT"]
    assert by_eco["freebsd_ports"] == ["BSD-2-Clause"]


# ---------------------------------------------------------------------------
# extract_candidate
# ---------------------------------------------------------------------------

def test_extract_candidate_structure():
    recs = [
        _record("curl", "nixpkgs", version="8.6.0", confidence=0.85),
        _record("curl", "freebsd_ports", version="8.6.0", confidence=0.90),
    ]
    result = ec.extract_candidate("curl", recs, score=88.0)
    assert result["canonical_name"] == "curl"
    assert result["score"] == 88.0
    assert set(result["ecosystems"]) == {"nixpkgs", "freebsd_ports"}
    assert "merged" in result
    assert "per_ecosystem" in result
    assert "analysis" in result


def test_extract_candidate_version_agreement_true():
    recs = [
        _record("zlib", "nixpkgs", version="1.3.1"),
        _record("zlib", "freebsd_ports", version="1.3.1"),
    ]
    result = ec.extract_candidate("zlib", recs, score=90.0)
    assert result["analysis"]["version_agreement"] is True


def test_extract_candidate_version_agreement_false():
    recs = [
        _record("zlib", "nixpkgs", version="1.3.1"),
        _record("zlib", "freebsd_ports", version="1.3.0"),
    ]
    result = ec.extract_candidate("zlib", recs, score=85.0)
    assert result["analysis"]["version_agreement"] is False
    assert result["analysis"]["versions_by_ecosystem"]["nixpkgs"] == "1.3.1"
    assert result["analysis"]["versions_by_ecosystem"]["freebsd_ports"] == "1.3.0"


def test_extract_candidate_merged_maintainers_union():
    recs = [
        _record("curl", "nixpkgs", maintainers=["alice"]),
        _record("curl", "freebsd_ports", maintainers=["bob"]),
    ]
    result = ec.extract_candidate("curl", recs, score=80.0)
    assert set(result["merged"]["maintainers"]) == {"alice", "bob"}


def test_extract_candidate_merged_maintainers_deduped():
    recs = [
        _record("curl", "nixpkgs", maintainers=["alice"]),
        _record("curl", "freebsd_ports", maintainers=["alice", "bob"]),
    ]
    result = ec.extract_candidate("curl", recs, score=80.0)
    assert result["merged"]["maintainers"].count("alice") == 1


def test_extract_candidate_merged_conflicts_union():
    recs = [
        _record("openssl", "nixpkgs", conflicts=["libressl"]),
        _record("openssl", "freebsd_ports", conflicts=["openssl30", "libressl"]),
    ]
    result = ec.extract_candidate("openssl", recs, score=75.0)
    assert set(result["merged"]["conflicts"]) == {"libressl", "openssl30"}
    assert result["analysis"]["has_conflicts"] is True


def test_extract_candidate_deprecated_any_ecosystem():
    recs = [
        _record("oldpkg", "nixpkgs", deprecated=False),
        _record("oldpkg", "freebsd_ports", deprecated=True),
    ]
    result = ec.extract_candidate("oldpkg", recs, score=50.0)
    assert result["merged"]["deprecated"] is True
    assert "freebsd_ports" in result["analysis"]["deprecated_in"]


def test_extract_candidate_deprecated_not_set():
    recs = [
        _record("zlib", "nixpkgs", deprecated=False),
        _record("zlib", "freebsd_ports", deprecated=False),
    ]
    result = ec.extract_candidate("zlib", recs, score=90.0)
    assert result["merged"]["deprecated"] is False
    assert result["analysis"]["deprecated_in"] == []


def test_extract_candidate_dep_union_in_merged():
    recs = [
        _record("curl", "nixpkgs", runtime_deps=["zlib"]),
        _record("curl", "freebsd_ports", runtime_deps=["openssl"]),
    ]
    result = ec.extract_candidate("curl", recs, score=80.0)
    assert set(result["merged"]["dependencies"]["runtime"]) == {"zlib", "openssl"}


def test_extract_candidate_sources_union():
    recs = [
        _record("curl", "nixpkgs", source_url="https://curl.se/curl-8.6.0.tar.gz"),
        _record("curl", "freebsd_ports", source_url="https://curl.se/curl-8.6.0.tar.bz2"),
    ]
    result = ec.extract_candidate("curl", recs, score=80.0)
    assert len(result["merged"]["sources"]) == 2


def test_extract_candidate_confidence_avg():
    recs = [
        _record("zlib", "nixpkgs", confidence=0.8),
        _record("zlib", "freebsd_ports", confidence=0.9),
    ]
    result = ec.extract_candidate("zlib", recs, score=90.0)
    assert result["analysis"]["confidence_avg"] == pytest.approx(0.85, abs=0.001)


def test_extract_candidate_per_ecosystem_keys():
    recs = [
        _record("zlib", "nixpkgs"),
        _record("zlib", "freebsd_ports"),
    ]
    result = ec.extract_candidate("zlib", recs, score=90.0)
    assert set(result["per_ecosystem"].keys()) == {"nixpkgs", "freebsd_ports"}


def test_extract_candidate_single_ecosystem():
    recs = [_record("onlynix", "nixpkgs", version="2.0")]
    result = ec.extract_candidate("onlynix", recs, score=40.0)
    assert result["ecosystems"] == ["nixpkgs"]
    assert result["analysis"]["version_agreement"] is True


def test_extract_candidate_notes_contain_version_agreement():
    recs = [
        _record("zlib", "nixpkgs", version="1.3.1"),
        _record("zlib", "freebsd_ports", version="1.3.1"),
    ]
    result = ec.extract_candidate("zlib", recs, score=90.0)
    notes = result["analysis"]["notes"]
    assert any("version agreement" in n for n in notes)


def test_extract_candidate_notes_contain_version_skew():
    recs = [
        _record("zlib", "nixpkgs", version="1.3.1"),
        _record("zlib", "freebsd_ports", version="1.3.0"),
    ]
    result = ec.extract_candidate("zlib", recs, score=85.0)
    notes = result["analysis"]["notes"]
    assert any("version skew" in n for n in notes)


def test_extract_candidate_notes_dep_difference():
    recs = [
        _record("curl", "nixpkgs", runtime_deps=["zlib", "openssl", "nghttp2"]),
        _record("curl", "freebsd_ports", runtime_deps=["openssl"]),
    ]
    result = ec.extract_candidate("curl", recs, score=80.0)
    notes = result["analysis"]["notes"]
    assert any("more dep" in n for n in notes)


def test_extract_candidate_license_union_in_merged():
    recs = [
        _record("dual", "nixpkgs", license=["MIT"]),
        _record("dual", "freebsd_ports", license=["Apache-2.0"]),
    ]
    result = ec.extract_candidate("dual", recs, score=70.0)
    assert set(result["merged"]["license"]) == {"MIT", "Apache-2.0"}


def test_extract_candidate_platforms_include_union():
    recs = [
        _record("pkg", "nixpkgs", platforms_include=["x86_64-linux"]),
        _record("pkg", "freebsd_ports", platforms_include=["amd64"]),
    ]
    result = ec.extract_candidate("pkg", recs, score=60.0)
    assert set(result["merged"]["platforms_include"]) == {"x86_64-linux", "amd64"}


# ---------------------------------------------------------------------------
# load_records_by_name
# ---------------------------------------------------------------------------

def test_load_records_by_name(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    rec1 = _record("zlib", "nixpkgs")
    rec2 = _record("zlib", "freebsd_ports")
    rec3 = _record("curl", "nixpkgs")
    (snap / "zlib_nix.json").write_text(json.dumps(rec1))
    (snap / "zlib_ports.json").write_text(json.dumps(rec2))
    (snap / "curl_nix.json").write_text(json.dumps(rec3))
    by_name = ec.load_records_by_name(snap)
    assert len(by_name["zlib"]) == 2
    assert len(by_name["curl"]) == 1


def test_load_records_by_name_skips_manifest(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "manifest.json").write_text(json.dumps({"meta": True}))
    (snap / "pkg.json").write_text(json.dumps(_record("pkg", "nixpkgs")))
    by_name = ec.load_records_by_name(snap)
    assert "meta" not in by_name
    assert "pkg" in by_name


def test_load_records_by_name_skips_bad_json(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "broken.json").write_text("not json{{{")
    (snap / "good.json").write_text(json.dumps(_record("pkg", "nixpkgs")))
    by_name = ec.load_records_by_name(snap)
    assert "pkg" in by_name


def test_load_records_by_name_skips_non_record_json(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "other.json").write_text(json.dumps({"not": "a record"}))
    by_name = ec.load_records_by_name(snap)
    assert len(by_name) == 0


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------

def test_main_writes_files(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "zlib_nix.json").write_text(json.dumps(_record("zlib", "nixpkgs", version="1.3.1", confidence=0.9)))
    (snap / "zlib_ports.json").write_text(json.dumps(_record("zlib", "freebsd_ports", version="1.3.1", confidence=0.85)))
    (snap / "curl_nix.json").write_text(json.dumps(_record("curl", "nixpkgs", version="8.6.0", confidence=0.8)))

    candidates = [
        {"canonical_name": "zlib", "score": 92.0},
        {"canonical_name": "curl", "score": 75.0},
    ]
    cand_file = tmp_path / "candidates.json"
    cand_file.write_text(json.dumps(candidates))

    out_dir = tmp_path / "extractions"
    ec.main.__module__  # ensure importable
    import sys as _sys
    _sys.argv = [
        "extract_candidates.py",
        str(snap),
        str(cand_file),
        "--out", str(out_dir),
    ]
    ec.main()

    assert (out_dir / "zlib.json").exists()
    assert (out_dir / "curl.json").exists()
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert len(manifest) == 2
    names = {m["canonical_name"] for m in manifest}
    assert names == {"zlib", "curl"}


def test_main_top_limits_output(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    for pkg in ("a", "b", "c"):
        (snap / f"{pkg}.json").write_text(json.dumps(_record(pkg, "nixpkgs")))

    candidates = [
        {"canonical_name": "a", "score": 90.0},
        {"canonical_name": "b", "score": 80.0},
        {"canonical_name": "c", "score": 70.0},
    ]
    cand_file = tmp_path / "candidates.json"
    cand_file.write_text(json.dumps(candidates))

    out_dir = tmp_path / "extractions"
    import sys as _sys
    _sys.argv = [
        "extract_candidates.py",
        str(snap),
        str(cand_file),
        "--out", str(out_dir),
        "--top", "2",
    ]
    ec.main()

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert len(manifest) == 2
    assert not (out_dir / "c.json").exists()


def test_main_skips_missing_candidates(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "zlib.json").write_text(json.dumps(_record("zlib", "nixpkgs")))

    candidates = [
        {"canonical_name": "zlib", "score": 90.0},
        {"canonical_name": "not_in_snapshot", "score": 80.0},
    ]
    cand_file = tmp_path / "candidates.json"
    cand_file.write_text(json.dumps(candidates))

    out_dir = tmp_path / "extractions"
    import sys as _sys
    _sys.argv = [
        "extract_candidates.py",
        str(snap),
        str(cand_file),
        "--out", str(out_dir),
    ]
    ec.main()

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert len(manifest) == 1
    assert manifest[0]["canonical_name"] == "zlib"


# ---------------------------------------------------------------------------
# behavioral_spec auto-injection
# ---------------------------------------------------------------------------

def test_find_behavioral_spec_known_library(tmp_path, monkeypatch):
    """Libraries with a matching zspec get a behavioral_spec path."""
    build_dir = tmp_path / "_build" / "zspecs"
    build_dir.mkdir(parents=True)
    for name in ("openssl", "zlib", "curl", "sqlite3"):
        (build_dir / f"{name}.zspec.json").write_text("{}")
    monkeypatch.setattr(ec, "REPO_ROOT", tmp_path)
    assert ec._find_behavioral_spec("openssl") == "_build/zspecs/openssl.zspec.json"
    assert ec._find_behavioral_spec("zlib")    == "_build/zspecs/zlib.zspec.json"
    assert ec._find_behavioral_spec("curl")    == "_build/zspecs/curl.zspec.json"
    assert ec._find_behavioral_spec("sqlite3") == "_build/zspecs/sqlite3.zspec.json"


def test_find_behavioral_spec_unknown_library():
    assert ec._find_behavioral_spec("no_such_package_xyz") is None


def test_extract_candidate_includes_behavioral_spec():
    """extract_candidate sets behavioral_spec when a matching zspec exists."""
    rec = _record("openssl", "nixpkgs", "3.0.0")
    result = ec.extract_candidate("openssl", [rec], 80.0)
    assert result.get("behavioral_spec") == "_build/zspecs/openssl.zspec.json"


def test_extract_candidate_no_behavioral_spec_when_none():
    """extract_candidate omits behavioral_spec when no matching zspec exists."""
    rec = _record("no_such_package_xyz", "nixpkgs", "1.0.0")
    result = ec.extract_candidate("no_such_package_xyz", [rec], 50.0)
    assert "behavioral_spec" not in result
