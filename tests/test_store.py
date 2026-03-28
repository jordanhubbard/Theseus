"""
tests/test_store.py

Tests for theseus/store.py — artifact storage.
"""
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import theseus.store as store


SAMPLE_SPEC = {
    "schema_version": "0.2",
    "identity": {"canonical_name": "mypkg", "version": "1.0"},
    "conflicts": [],
}


# ---------------------------------------------------------------------------
# file:// storage
# ---------------------------------------------------------------------------

class TestStoreFile:
    def test_creates_dest_directory(self, tmp_path):
        dest_root = tmp_path / "artifacts"
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "Makefile").write_text("# port", encoding="utf-8")

        ok, err = store.store(
            f"file://{dest_root}", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert ok is True
        assert err == ""
        assert (dest_root / "mypkg" / "freebsd_ports").is_dir()

    def test_writes_spec_json(self, tmp_path):
        dest_root = tmp_path / "artifacts"
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        store.store(
            f"file://{dest_root}", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        spec_path = dest_root / "mypkg" / "freebsd_ports" / "spec.json"
        assert spec_path.exists()
        loaded = json.loads(spec_path.read_text())
        assert loaded["identity"]["canonical_name"] == "mypkg"

    def test_copies_output_files(self, tmp_path):
        dest_root = tmp_path / "artifacts"
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "Makefile").write_text("PORT=mypkg", encoding="utf-8")
        (out_dir / "distinfo").write_text("SHA256=abc", encoding="utf-8")

        store.store(
            f"file://{dest_root}", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        dest = dest_root / "mypkg" / "freebsd_ports"
        assert (dest / "Makefile").exists()
        assert (dest / "distinfo").exists()

    def test_copies_file_content_intact(self, tmp_path):
        dest_root = tmp_path / "artifacts"
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        content = "{ pkgs }: pkgs.stdenv.mkDerivation { pname = \"mypkg\"; }"
        (out_dir / "default.nix").write_text(content, encoding="utf-8")

        store.store(
            f"file://{dest_root}", "mypkg", "nixpkgs", SAMPLE_SPEC, out_dir
        )
        dest_file = dest_root / "mypkg" / "nixpkgs" / "default.nix"
        assert dest_file.read_text(encoding="utf-8") == content

    def test_returns_error_on_permission_denied(self, tmp_path):
        # Point to a file path that can't be created (parent is a file)
        blocker = tmp_path / "blocker"
        blocker.write_text("block")
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        ok, err = store.store(
            f"file://{blocker}/sub", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert ok is False
        assert err != ""

    def test_unknown_scheme_returns_error(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        ok, err = store.store(
            "ftp://myhost/path", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert ok is False
        assert "Unsupported" in err

    def test_empty_url_returns_error(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        ok, err = store.store("", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir)
        assert ok is False


# ---------------------------------------------------------------------------
# s3:// storage
# ---------------------------------------------------------------------------

class TestStoreS3:
    @patch("theseus.store.shutil.which", return_value=None)
    def test_missing_aws_cli(self, mock_which, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        ok, err = store.store(
            "s3://mybucket/prefix", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert ok is False
        assert "aws" in err.lower()

    @patch("theseus.store.shutil.which", return_value="/usr/bin/aws")
    @patch("theseus.store.subprocess.run")
    def test_success(self, mock_run, mock_which, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "Makefile").write_text("PORT=mypkg")

        ok, err = store.store(
            "s3://mybucket/prefix", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert ok is True
        assert err == ""

    @patch("theseus.store.shutil.which", return_value="/usr/bin/aws")
    @patch("theseus.store.subprocess.run")
    def test_failure_propagated(self, mock_run, mock_which, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="NoSuchBucket")
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "Makefile").write_text("PORT=mypkg")

        ok, err = store.store(
            "s3://mybucket/prefix", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert ok is False
        assert "NoSuchBucket" in err

    @patch("theseus.store.shutil.which", return_value="/usr/bin/aws")
    @patch("theseus.store.subprocess.run")
    def test_endpoint_url_passed_to_aws(self, mock_run, mock_which, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "Makefile").write_text("PORT=mypkg")

        store_cfg = {
            "url": "s3://theseus-artifacts",
            "endpoint_url": "http://ubumeh.local:9000",
            "access_key": "theseus",
            "secret_key": "theseus-store-2026",
        }
        store.store(
            "s3://theseus-artifacts", "mypkg", "freebsd_ports",
            SAMPLE_SPEC, out_dir, store_cfg
        )
        call_args = mock_run.call_args[0][0]
        assert "--endpoint-url" in call_args
        assert "http://ubumeh.local:9000" in call_args

    @patch("theseus.store.shutil.which", return_value="/usr/bin/aws")
    @patch("theseus.store.subprocess.run")
    def test_access_key_set_in_env(self, mock_run, mock_which, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "Makefile").write_text("PORT=mypkg")

        store_cfg = {"access_key": "mykey", "secret_key": "mysecret"}
        store.store(
            "s3://mybucket", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir, store_cfg
        )
        env_used = mock_run.call_args[1]["env"]
        assert env_used["AWS_ACCESS_KEY_ID"] == "mykey"
        assert env_used["AWS_SECRET_ACCESS_KEY"] == "mysecret"

    @patch("theseus.store.shutil.which", return_value="/usr/bin/aws")
    @patch("theseus.store.subprocess.run")
    def test_spec_json_temp_cleaned_up(self, mock_run, mock_which, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        store.store(
            "s3://mybucket/prefix", "mypkg", "freebsd_ports", SAMPLE_SPEC, out_dir
        )
        assert not (out_dir / "_spec.json").exists()


# ---------------------------------------------------------------------------
# Build record log
# ---------------------------------------------------------------------------

class TestAppendBuildRecord:
    def test_creates_reports_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store._append_build_record(
            canonical_name="mypkg",
            driver="freebsd_ports",
            store_url="file:///tmp/x",
            success=True,
            error="",
        )
        assert (tmp_path / "reports").is_dir()
        assert (tmp_path / "reports" / "builds.jsonl").exists()

    def test_record_fields(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store._append_build_record(
            canonical_name="mypkg",
            driver="nixpkgs",
            store_url="s3://bucket/key",
            success=False,
            error="oops",
        )
        line = (tmp_path / "reports" / "builds.jsonl").read_text()
        rec = json.loads(line.strip())
        assert rec["canonical_name"] == "mypkg"
        assert rec["driver"] == "nixpkgs"
        assert rec["success"] is False
        assert rec["error"] == "oops"
        assert "ts" in rec

    def test_appends_multiple_records(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for i in range(3):
            store._append_build_record(
                canonical_name=f"pkg{i}",
                driver="freebsd_ports",
                store_url="file:///tmp",
                success=True,
                error="",
            )
        lines = (tmp_path / "reports" / "builds.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3
        names = [json.loads(l)["canonical_name"] for l in lines]
        assert names == ["pkg0", "pkg1", "pkg2"]
