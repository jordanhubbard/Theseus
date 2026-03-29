"""
tests/test_fill_nixpkgs_deps.py

Tests for the nixpkgs dep-fill pass: _nixpkgs_deps_batch, _nixpkgs_deps_one,
and fill_nixpkgs_deps.
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
# _nixpkgs_deps_batch
# ---------------------------------------------------------------------------

class TestNixpkgsDepsBatch:
    @patch("theseus.importer.subprocess.run")
    def test_success_returns_dep_map(self, mock_run, tmp_path):
        payload = {"curl": {"build": ["cmake"], "host": ["zlib"], "runtime": ["openssl"]}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        result = imp._nixpkgs_deps_batch(["curl"], tmp_path)
        assert result["curl"] == {"build": ["cmake"], "host": ["zlib"], "runtime": ["openssl"]}

    @patch("theseus.importer.subprocess.run")
    def test_nonzero_returncode_returns_none_for_all(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = imp._nixpkgs_deps_batch(["curl", "zlib"], tmp_path)
        assert result["curl"] is None
        assert result["zlib"] is None

    @patch("theseus.importer.subprocess.run", side_effect=subprocess.TimeoutExpired("nix-instantiate", 60))
    def test_timeout_returns_none_for_all(self, mock_run, tmp_path):
        result = imp._nixpkgs_deps_batch(["curl"], tmp_path)
        assert result["curl"] is None

    @patch("theseus.importer.subprocess.run")
    def test_invalid_json_returns_none_for_all(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="not-json", stderr="")
        result = imp._nixpkgs_deps_batch(["curl"], tmp_path)
        assert result["curl"] is None

    @patch("theseus.importer.subprocess.run")
    def test_per_pkg_failed_flag_treated_as_none(self, mock_run, tmp_path):
        # _failed: true means the per-package tryEval caught an error in Nix.
        payload = {"curl": {"build": [], "host": [], "runtime": [], "_failed": True}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        result = imp._nixpkgs_deps_batch(["curl"], tmp_path)
        assert result["curl"] is None

    @patch("theseus.importer.subprocess.run")
    def test_attrs_appear_in_expression(self, mock_run, tmp_path):
        payload = {"pkg_a": {"build": [], "host": [], "runtime": []},
                   "pkg_b": {"build": [], "host": [], "runtime": []}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        imp._nixpkgs_deps_batch(["pkg_a", "pkg_b"], tmp_path)
        expr = mock_run.call_args[0][0][-1]   # last arg is the Nix expression
        assert "pkg_a" in expr
        assert "pkg_b" in expr

    @patch("theseus.importer.subprocess.run")
    def test_strict_flag_present(self, mock_run, tmp_path):
        # Batch eval uses --strict so all thunks are forced before JSON serialization.
        payload = {"curl": {"build": [], "host": [], "runtime": []}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        imp._nixpkgs_deps_batch(["curl"], tmp_path)
        cmd = mock_run.call_args[0][0]
        assert "--strict" in cmd

    @patch("theseus.importer.subprocess.run")
    def test_try_eval_in_expression(self, mock_run, tmp_path):
        # Each package in the batch is wrapped in tryEval for error isolation.
        payload = {"curl": {"build": [], "host": [], "runtime": []}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        imp._nixpkgs_deps_batch(["curl"], tmp_path)
        expr = mock_run.call_args[0][0][-1]
        assert "tryEval" in expr

    @patch("theseus.importer.subprocess.run")
    def test_custom_timeout_passed(self, mock_run, tmp_path):
        payload = {"curl": {"build": [], "host": [], "runtime": []}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
        imp._nixpkgs_deps_batch(["curl"], tmp_path, timeout=15)
        assert mock_run.call_args[1]["timeout"] == 15


# ---------------------------------------------------------------------------
# _nixpkgs_deps_one (thin wrapper around batch)
# ---------------------------------------------------------------------------

class TestNixpkgsDepsOne:
    @patch("theseus.importer._nixpkgs_deps_batch")
    def test_success_returns_dep_lists(self, mock_batch, tmp_path):
        deps = {"build": ["cmake"], "host": ["zlib"], "runtime": ["openssl"]}
        mock_batch.return_value = {"curl": deps}
        result = imp._nixpkgs_deps_one("curl", tmp_path)
        assert result == deps

    @patch("theseus.importer._nixpkgs_deps_batch")
    def test_none_when_batch_returns_none(self, mock_batch, tmp_path):
        mock_batch.return_value = {"curl": None}
        assert imp._nixpkgs_deps_one("curl", tmp_path) is None

    @patch("theseus.importer._nixpkgs_deps_batch")
    def test_delegates_timeout(self, mock_batch, tmp_path):
        mock_batch.return_value = {"curl": {"build": [], "host": [], "runtime": []}}
        imp._nixpkgs_deps_one("curl", tmp_path, timeout=15)
        mock_batch.assert_called_once_with(["curl"], tmp_path, timeout=15)


# ---------------------------------------------------------------------------
# fill_nixpkgs_deps
# ---------------------------------------------------------------------------

def _patch_batch(side_effect=None, return_value=None):
    """Patch _nixpkgs_deps_batch for fill_nixpkgs_deps tests."""
    if side_effect:
        return patch("theseus.importer._nixpkgs_deps_batch", side_effect=side_effect)
    return patch("theseus.importer._nixpkgs_deps_batch", return_value=return_value)


class TestFillNixpkgsDeps:
    def test_fills_empty_deps(self, tmp_path):
        _write_record(tmp_path, "curl")
        deps = {"build": ["cmake"], "host": ["zlib"], "runtime": []}

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: deps for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert filled == 1
        assert skipped == 0
        assert failed == 0
        rec = json.loads((tmp_path / "curl.json").read_text())
        assert rec["dependencies"]["build"] == ["cmake"]
        assert rec["dependencies"]["host"] == ["zlib"]

    def test_skips_record_with_existing_deps(self, tmp_path):
        _write_record(tmp_path, "curl", has_deps=True)
        with _patch_batch(return_value={}) as m:
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert filled == 0
        assert skipped == 1
        m.assert_not_called()

    def test_overwrite_forces_refill(self, tmp_path):
        _write_record(tmp_path, "curl", has_deps=True)
        deps = {"build": ["new"], "host": [], "runtime": []}

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: deps for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            filled, skipped, failed = imp.fill_nixpkgs_deps(
                tmp_path, tmp_path, overwrite=True
            )
        assert filled == 1
        rec = json.loads((tmp_path / "curl.json").read_text())
        assert rec["dependencies"]["build"] == ["new"]

    def test_failed_eval_increments_failed(self, tmp_path):
        _write_record(tmp_path, "curl")

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: None for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert failed == 1
        assert filled == 0

    def test_failed_eval_updates_warning(self, tmp_path):
        _write_record(tmp_path, "curl")

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: None for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        rec = json.loads((tmp_path / "curl.json").read_text())
        warnings = rec["provenance"]["warnings"]
        assert any("dep fill failed" in w for w in warnings)

    def test_clears_stale_warning_on_success(self, tmp_path):
        _write_record(tmp_path, "curl")
        deps = {"build": [], "host": [], "runtime": []}

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: deps for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        rec = json.loads((tmp_path / "curl.json").read_text())
        warnings = rec["provenance"]["warnings"]
        assert not any("infinite recursion" in w for w in warnings)
        assert not any("deps not extracted" in w for w in warnings)

    def test_skips_non_nixpkgs_records(self, tmp_path):
        _write_record(tmp_path, "someport", ecosystem="freebsd_ports")
        with _patch_batch(return_value={}) as m:
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert skipped == 1
        m.assert_not_called()

    def test_record_without_attr_counts_as_failed(self, tmp_path):
        rec = _nixpkgs_record("nix")
        rec["extensions"]["nixpkgs"]["attr"] = ""
        (tmp_path / "nix.json").write_text(json.dumps(rec))

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: {"build": [], "host": [], "runtime": []} for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert failed == 1

    def test_multiple_records_batched(self, tmp_path):
        _write_record(tmp_path, "curl")
        _write_record(tmp_path, "wget")
        _write_record(tmp_path, "openssl", has_deps=True)

        call_count = 0
        def fake_batch(attrs, nixpkgs, **kw):
            nonlocal call_count
            call_count += 1
            return {
                a: None if a == "wget" else {"build": [], "host": [], "runtime": []}
                for a in attrs
            }

        with _patch_batch(side_effect=fake_batch):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)

        assert filled == 1    # curl
        assert skipped == 1   # openssl already had deps
        assert failed == 1    # wget returned None
        assert call_count == 1  # curl + wget evaluated in one batch call

    def test_invalid_json_file_counts_as_failed(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")

        def fake_batch(attrs, nixpkgs, **kw):
            return {a: {"build": [], "host": [], "runtime": []} for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            filled, skipped, failed = imp.fill_nixpkgs_deps(tmp_path, tmp_path)
        assert failed == 1

    def test_batching_uses_batch_size(self, tmp_path):
        for i in range(5):
            _write_record(tmp_path, f"pkg{i}")

        batches_seen = []
        def fake_batch(attrs, nixpkgs, **kw):
            batches_seen.append(list(attrs))
            return {a: {"build": [], "host": [], "runtime": []} for a in attrs}

        with _patch_batch(side_effect=fake_batch):
            imp.fill_nixpkgs_deps(tmp_path, tmp_path, batch_size=2)

        # 5 packages with batch_size=2 → 3 batches (2+2+1)
        assert len(batches_seen) == 3
        total_attrs = sum(len(b) for b in batches_seen)
        assert total_attrs == 5
