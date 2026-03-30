"""
Tests for tools/diff_snapshots.py.
"""
import json
import sys
from pathlib import Path

import diff_snapshots as ds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(name, ecosystem, version, confidence=0.9):
    return {
        "schema_version": "0.1",
        "identity": {
            "canonical_name": name,
            "canonical_id": f"pkg:{name}",
            "version": version,
            "ecosystem": ecosystem,
            "ecosystem_id": f"pkgs/{name}",
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


def _write(snapshot_dir, records):
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for i, rec in enumerate(records):
        name = rec["identity"]["canonical_name"]
        eco = rec["identity"]["ecosystem"]
        (snapshot_dir / f"{name}_{eco}_{i}.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )


def _run_main(before, after, out=None):
    argv = ["diff_snapshots.py", "--before", str(before), "--after", str(after)]
    if out:
        argv += ["--out", str(out)]
    sys.argv = argv
    ds.main()


# ---------------------------------------------------------------------------
# load_snapshot
# ---------------------------------------------------------------------------

def test_load_snapshot_empty(tmp_path):
    result = ds.load_snapshot(tmp_path)
    assert result == {}


def test_load_snapshot_groups_by_name(tmp_path):
    _write(tmp_path, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("zlib", "freebsd_ports", "1.3.1"),
        _make_record("curl", "nixpkgs", "8.7.1"),
    ])
    groups = ds.load_snapshot(tmp_path)
    assert set(groups.keys()) == {"zlib", "curl"}
    assert len(groups["zlib"]) == 2
    assert len(groups["curl"]) == 1


def test_load_snapshot_skips_manifest(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps(_make_record("zlib", "nixpkgs", "1.3.1")), encoding="utf-8"
    )
    assert ds.load_snapshot(tmp_path) == {}


def test_load_snapshot_skips_invalid_json(tmp_path):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    assert ds.load_snapshot(tmp_path) == {}


def test_load_snapshot_skips_non_identity_records(tmp_path):
    (tmp_path / "meta.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    assert ds.load_snapshot(tmp_path) == {}


def test_load_snapshot_recurses_subdirs(tmp_path):
    sub = tmp_path / "nixpkgs"
    sub.mkdir()
    rec = _make_record("zlib", "nixpkgs", "1.3.1")
    (sub / "zlib.json").write_text(json.dumps(rec), encoding="utf-8")
    groups = ds.load_snapshot(tmp_path)
    assert "zlib" in groups


# ---------------------------------------------------------------------------
# diff_snapshots
# ---------------------------------------------------------------------------

def test_diff_added(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [_make_record("zlib", "nixpkgs", "1.3.1")])
    _write(after, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("curl", "nixpkgs", "8.7.1"),
    ])
    report = ds.diff_snapshots(before, after)
    assert "curl" in report["added"]
    assert report["summary"]["added_count"] == 1
    assert report["summary"]["removed_count"] == 0


def test_diff_removed(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("curl", "nixpkgs", "8.7.1"),
    ])
    _write(after, [_make_record("zlib", "nixpkgs", "1.3.1")])
    report = ds.diff_snapshots(before, after)
    assert "curl" in report["removed"]
    assert report["summary"]["removed_count"] == 1
    assert report["summary"]["added_count"] == 0


def test_diff_version_changed(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [_make_record("openssl", "nixpkgs", "3.2.0")])
    _write(after, [_make_record("openssl", "nixpkgs", "3.3.0")])
    report = ds.diff_snapshots(before, after)
    names = [e["canonical_name"] for e in report["version_changed"]]
    assert "openssl" in names
    assert report["summary"]["version_changed_count"] == 1


def test_diff_ecosystem_changed(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [_make_record("zlib", "nixpkgs", "1.3.1")])
    _write(after, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("zlib", "freebsd_ports", "1.3.1"),
    ])
    report = ds.diff_snapshots(before, after)
    names = [e["canonical_name"] for e in report["ecosystem_changed"]]
    assert "zlib" in names
    assert report["summary"]["ecosystem_changed_count"] == 1


def test_diff_unchanged(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    records = [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("curl", "freebsd_ports", "8.7.1"),
    ]
    _write(before, records)
    _write(after, records)
    report = ds.diff_snapshots(before, after)
    assert report["summary"]["unchanged_count"] == 2
    assert report["summary"]["added_count"] == 0
    assert report["summary"]["removed_count"] == 0
    assert report["summary"]["version_changed_count"] == 0


def test_diff_both_empty(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    report = ds.diff_snapshots(before, after)
    assert report["summary"]["total_before"] == 0
    assert report["summary"]["total_after"] == 0
    assert report["summary"]["added_count"] == 0


def test_diff_summary_counts_are_consistent(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("curl", "nixpkgs", "8.5.0"),
        _make_record("openssl", "nixpkgs", "3.2.0"),
    ])
    _write(after, [
        _make_record("zlib", "nixpkgs", "1.3.1"),      # unchanged
        _make_record("curl", "nixpkgs", "8.7.1"),      # version changed
        _make_record("libpng", "nixpkgs", "1.6.43"),   # added
        # openssl removed
    ])
    report = ds.diff_snapshots(before, after)
    s = report["summary"]
    total = s["added_count"] + s["removed_count"] + s["version_changed_count"] + \
            s["ecosystem_changed_count"] + s["unchanged_count"]
    all_names = set(ds.load_snapshot(before)) | set(ds.load_snapshot(after))
    assert total == len(all_names)


def test_diff_version_changed_captures_both_versions(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [_make_record("pkg", "nixpkgs", "1.0")])
    _write(after, [_make_record("pkg", "nixpkgs", "2.0")])
    report = ds.diff_snapshots(before, after)
    entry = report["version_changed"][0]
    assert entry["before"]["versions"]["nixpkgs"] == "1.0"
    assert entry["after"]["versions"]["nixpkgs"] == "2.0"


def test_diff_sorted_output(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    _write(after, [
        _make_record("zlib", "nixpkgs", "1.0"),
        _make_record("aaa", "nixpkgs", "1.0"),
        _make_record("mmm", "nixpkgs", "1.0"),
    ])
    report = ds.diff_snapshots(before, after)
    assert report["added"] == sorted(report["added"])


# ---------------------------------------------------------------------------
# main: output file writing
# ---------------------------------------------------------------------------

def test_main_writes_out_file(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write(before, [_make_record("zlib", "nixpkgs", "1.3.1")])
    _write(after, [
        _make_record("zlib", "nixpkgs", "1.3.1"),
        _make_record("curl", "nixpkgs", "8.7.1"),
    ])
    out = tmp_path / "diff.json"
    _run_main(before, after, out=out)
    assert out.exists()
    report = json.loads(out.read_text())
    assert "summary" in report
    assert report["summary"]["added_count"] == 1
