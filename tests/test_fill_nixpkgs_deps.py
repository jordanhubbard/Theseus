"""
tests/test_fill_nixpkgs_deps.py

Tests for the nixpkgs dep-fill pass: _nixpkgs_deps_one and fill_nixpkgs_deps.
"""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import theseus.importer as imp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nixpkgs_record(attr: str, *, has_deps: bool = False, ecosystem: str = "nixpkgs") -> dict:
    return {
        "schema_version": "0.2",
        "identity": {
            "canonical_name": attr,
            "canonical_id": f"pkg:{attr}",
            "version": "1.0",
            "ecosystem": ecosystem,
            "ecosystem_id": attr,
        },
        "descriptive": {"summary": "", "homepage": "", "license": [], "categories": [], "maintainers": []},
        "conflicts": [],
        "sources": [],
        "dependencies": {
            "build": ["cmake"] if has_deps else [],
            "host": ["openssl"] if has_deps else [],
            "runtime": [],
            "test": [],
        },
        "build": {"system_kind": "autotools", "configure_args": [], "make_args": []},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": [],
        "tests": {},
        "provenance": {
            "generated_by": "test",
            "imported_at": "2026-01-01",
            "source_path": attr,
            "source_repo_commit": None,
            "confidence": 0.8,
            "unmapped": [],
            "warnings": ["deps not extracted by eval importer (infinite recursion risk)"],
        },
        "extensions": {"nixpkgs": {"attr": attr}},
    }


def _write_record(directory: Path, attr: str, **kw) -> Path:
    rec = _nixpkgs_record(attr, **kw)
    p = directory / f"{attr}.json"
    p.write_text(json.dumps(rec), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# _nixpkgs_deps_one
# ---------------------------------------------------------------------------

class TestNixpkgsDepsOne:
    @patch("theseus.importer.subprocess.run")
    def test_success_returns_dep_lists(self, mock_run, tmp_path):
        payload = {"build": ["cmake"], "host": ["zlib"], "runtime": ["openssl"]}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        result = imp._nixpkgs_deps_one("curl", tmp_path)
        assert result == payload

    @patch("theseus.importer.subprocess.run")
    def test_nonzero_returncode_returns_none(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        assert imp._nixpkgs_deps_one("curl", tmp_path) is None

    @patch("theseus.importer.subprocess.run", side_effect=subprocess.TimeoutExpired("nix-instantiate", 30))
    def test_timeout_returns_none(self, mock_run, tmp_path):
        assert imp._nixpkgs_deps_one("curl", tmp_path) is None

    @patch("theseus.importer.subprocess.run")
    def test_invalid_json_returns_none(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="not-json", stderr="")
        assert imp._nixpkgs_deps_one("curl", tmp_path) is None

    @patch("theseus.importer.subprocess.run")
    def test_attr_embedded_in_expression(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"build":[],"host":[],"runtime":[]}', stderr=""
        )
        imp._nixpkgs_deps_one("mySpecialPkg", tmp_path)
        cmd = mock_run.call_args[0][0]
        assert "mySpecialPkg" in " ".join(cmd)

    @patch("theseus.importer.subprocess.run")
    def test_no_strict_flag(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"build":[],"host":[],"runtime":[]}', stderr=""
        )
        imp._nixpkgs_deps_one("curl", tmp_path)
        cmd = mock_run.call_args[0][0]
        assert "--strict" not in cmd

    @patch("theseus.importer.subprocess.run")
    def test_custom_timeout_passed(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"build":[],"host":[],"runtime":[]}', stderr=""
        )
        imp._nixpkgs_deps_one("curl", tmp_path, timeout=15)
        assert mock_run.call_args[1]["timeout"] == 15


# ---------------------------------------------------------------------------
# fill_nixpkgs_deps
# ---------------------------------------------------------------------------

class TestFillNixpkgsDeps:
    def _patch_deps_one(self, return_value):
        return patch(
            "theseus.importer._nixpkgs_deps_one",
            return_value=return_value,
        )

    def test_fills_empty_deps(self, tmp_path):
        _write_record(tmp_path, "curl")
        deps = {"build": ["cmake"], "host": ["zlib"], "runtime": []}
        with self._patch_deps_one(deps):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert filled == 1
        assert skipped == 0
        assert failed == 0
        rec = json.loads((tmp_path / "curl.json").read_text())
        assert rec["dependencies"]["build"] == ["cmake"]
        assert rec["dependencies"]["host"] == ["zlib"]

    def test_skips_record_with_existing_deps(self, tmp_path):
        _write_record(tmp_path, "curl", has_deps=True)
        with self._patch_deps_one({"build": ["x"], "host": [], "runtime": []}) as m:
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert filled == 0
        assert skipped == 1
        m.assert_not_called()

    def test_overwrite_forces_refill(self, tmp_path):
        _write_record(tmp_path, "curl", has_deps=True)
        deps = {"build": ["new"], "host": [], "runtime": []}
        with self._patch_deps_one(deps):
            filled, skipped, failed = imp.fill_nixpkgs_deps(
                tmp_path, tmp_path, overwrite=True
            )
        assert filled == 1
        rec = json.loads((tmp_path / "curl.json").read_text())
        assert rec["dependencies"]["build"] == ["new"]

    def test_failed_eval_increments_failed(self, tmp_path):
        _write_record(tmp_path, "curl")
        with self._patch_deps_one(None):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert failed == 1
        assert filled == 0

    def test_failed_eval_updates_warning(self, tmp_path):
        _write_record(tmp_path, "curl")
        with self._patch_deps_one(None):
            imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        rec = json.loads((tmp_path / "curl.json").read_text())
        warnings = rec["provenance"]["warnings"]
        assert any("dep fill failed" in w for w in warnings)

    def test_clears_stale_warning_on_success(self, tmp_path):
        _write_record(tmp_path, "curl")
        deps = {"build": [], "host": [], "runtime": []}
        with self._patch_deps_one(deps):
            imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        rec = json.loads((tmp_path / "curl.json").read_text())
        warnings = rec["provenance"]["warnings"]
        assert not any("infinite recursion" in w for w in warnings)
        assert not any("deps not extracted" in w for w in warnings)

    def test_skips_non_nixpkgs_records(self, tmp_path):
        _write_record(tmp_path, "someport", ecosystem="freebsd_ports")
        with self._patch_deps_one({"build": [], "host": [], "runtime": []}) as m:
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert skipped == 1
        m.assert_not_called()

    def test_record_without_attr_counts_as_failed(self, tmp_path):
        rec = _nixpkgs_record("nix")
        rec["extensions"]["nixpkgs"]["attr"] = ""
        (tmp_path / "nix.json").write_text(json.dumps(rec))
        with self._patch_deps_one({"build": [], "host": [], "runtime": []}):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert failed == 1

    def test_multiple_records_mixed(self, tmp_path):
        _write_record(tmp_path, "curl")
        _write_record(tmp_path, "wget")
        _write_record(tmp_path, "openssl", has_deps=True)

        call_count = 0
        def fake_deps(attr, nixpkgs, **kw):
            nonlocal call_count
            call_count += 1
            if attr == "wget":
                return None
            return {"build": [], "host": [], "runtime": []}

        with patch("theseus.importer._nixpkgs_deps_one", side_effect=fake_deps):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)

        assert filled == 1   # curl
        assert skipped == 1  # openssl already had deps
        assert failed == 1   # wget timed out
        assert call_count == 2  # curl + wget (not openssl)

    def test_invalid_json_file_counts_as_failed(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
        with self._patch_deps_one({"build": [], "host": [], "runtime": []}):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert failed == 1
