"""
tests/test_remote.py

Tests for theseus/remote.py — build command generation and dispatch.
"""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import theseus.remote as remote


# ---------------------------------------------------------------------------
# build_command
# ---------------------------------------------------------------------------

class TestBuildCommand:
    def test_freebsd_fetch_and_build(self):
        cmd = remote.build_command("freebsd_ports", "/tmp/work", {})
        assert "make -C /tmp/work" in cmd
        assert "fetch" in cmd
        assert "build" in cmd
        assert "&&" in cmd

    def test_freebsd_default_portsdir(self):
        cmd = remote.build_command("freebsd_ports", "/tmp/work", {})
        assert "PORTSDIR=/usr/ports" in cmd

    def test_freebsd_custom_portsdir(self):
        cmd = remote.build_command(
            "freebsd_ports", "/tmp/work", {"ports_root": "/home/jkh/ports"}
        )
        assert "PORTSDIR=/home/jkh/ports" in cmd

    def test_freebsd_work_path_embedded(self):
        cmd = remote.build_command("freebsd_ports", "/custom/path", {})
        assert "/custom/path" in cmd

    def test_nixpkgs_nix_build(self):
        cmd = remote.build_command("nixpkgs", "/tmp/work", {})
        assert "nix-build" in cmd
        assert "--no-out-link" in cmd

    def test_nixpkgs_callpackage_path(self):
        cmd = remote.build_command("nixpkgs", "/tmp/nix-work", {})
        assert "/tmp/nix-work/default.nix" in cmd

    def test_nixpkgs_import_nixpkgs(self):
        cmd = remote.build_command("nixpkgs", "/tmp/work", {})
        assert "import <nixpkgs>" in cmd

    def test_nixpkgs_via_docker(self):
        cmd = remote.build_command("nixpkgs", "/tmp/work", {"nix_via_docker": True})
        assert "docker run" in cmd
        assert "nixos/nix" in cmd
        assert "/tmp/work" in cmd

    def test_nixpkgs_no_docker_by_default(self):
        cmd = remote.build_command("nixpkgs", "/tmp/work", {})
        assert "docker" not in cmd

    def test_unknown_driver_exit_1(self):
        cmd = remote.build_command("unknown_driver", "/tmp/work", {})
        assert "exit 1" in cmd
        assert "unknown_driver" in cmd

    def test_freebsd_stderr_merged(self):
        cmd = remote.build_command("freebsd_ports", "/tmp/work", {})
        assert "2>&1" in cmd

    def test_nixpkgs_stderr_merged(self):
        cmd = remote.build_command("nixpkgs", "/tmp/work", {})
        assert "2>&1" in cmd


# ---------------------------------------------------------------------------
# _ssh_dest
# ---------------------------------------------------------------------------

class TestSshDest:
    def test_user_and_host(self):
        assert remote._ssh_dest({"user": "jkh", "host": "freebsd.local"}) == "jkh@freebsd.local"

    def test_host_only(self):
        assert remote._ssh_dest({"host": "freebsd.local"}) == "freebsd.local"

    def test_default_host_localhost(self):
        assert remote._ssh_dest({}) == "localhost"

    def test_empty_user_omitted(self):
        assert remote._ssh_dest({"user": "", "host": "myhost"}) == "myhost"


# ---------------------------------------------------------------------------
# _build_local
# ---------------------------------------------------------------------------

class TestBuildLocal:
    def _target(self, **kw):
        return {"name": "local", "local": True, **kw}

    @patch("theseus.remote.subprocess.run")
    def test_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        result = remote._build_local("freebsd_ports", tmp_path, "mypkg", self._target())
        assert result.success is True
        assert result.returncode == 0
        assert result.driver == "freebsd_ports"
        assert result.target == "local"

    @patch("theseus.remote.subprocess.run")
    def test_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error\n")
        result = remote._build_local("freebsd_ports", tmp_path, "mypkg", self._target())
        assert result.success is False
        assert result.returncode == 1

    @patch("theseus.remote.subprocess.run")
    def test_command_uses_resolved_path(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        remote._build_local("freebsd_ports", tmp_path, "mypkg", self._target())
        cmd_arg = mock_run.call_args[0][0]
        assert str(tmp_path.resolve()) in cmd_arg

    @patch("theseus.remote.subprocess.run")
    def test_uses_shell_true(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        remote._build_local("nixpkgs", tmp_path, "mypkg", self._target())
        assert mock_run.call_args[1].get("shell") is True

    @patch("theseus.remote.subprocess.run")
    def test_nixpkgs_driver(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="drv\n", stderr="")
        result = remote._build_local("nixpkgs", tmp_path, "mypkg", self._target())
        assert result.driver == "nixpkgs"
        assert "nix-build" in result.command


# ---------------------------------------------------------------------------
# _build_remote
# ---------------------------------------------------------------------------

class TestBuildRemote:
    def _target(self, **kw):
        return {"name": "freebsd.local", "host": "freebsd.local", "user": "jkh", **kw}

    def _mock_ssh_run(self, side_effects):
        """Return a patch context manager for _ssh_run with given side_effects."""
        return patch("theseus.remote._ssh_run", side_effect=side_effects)

    def _mock_rsync(self, ok=True, err=""):
        return patch("theseus.remote._rsync_to", return_value=(ok, err))

    def _mock_scp(self, ok=True, err=""):
        return patch("theseus.remote._scp_to", return_value=(ok, err))

    def test_success_full_flow(self, tmp_path):
        ssh_effects = [(0, "", ""), (0, "build output\n", "")]
        with self._mock_ssh_run(ssh_effects), self._mock_rsync(True):
            result = remote._build_remote(
                "freebsd_ports", tmp_path, "mypkg", self._target()
            )
        assert result.success is True
        assert result.stdout == "build output\n"

    def test_mkdir_failure(self, tmp_path):
        with self._mock_ssh_run([(1, "", "permission denied")]):
            result = remote._build_remote(
                "freebsd_ports", tmp_path, "mypkg", self._target()
            )
        assert result.success is False
        assert "remote directory" in result.stderr

    def test_rsync_failure_falls_back_to_scp(self, tmp_path):
        ssh_effects = [(0, "", ""), (0, "ok\n", "")]
        with self._mock_ssh_run(ssh_effects), \
             self._mock_rsync(False, "rsync error"), \
             self._mock_scp(True):
            result = remote._build_remote(
                "freebsd_ports", tmp_path, "mypkg", self._target()
            )
        assert result.success is True

    def test_both_copy_methods_fail(self, tmp_path):
        with self._mock_ssh_run([(0, "", "")]), \
             self._mock_rsync(False, "rsync err"), \
             self._mock_scp(False, "scp err"):
            result = remote._build_remote(
                "freebsd_ports", tmp_path, "mypkg", self._target()
            )
        assert result.success is False
        assert "File copy" in result.stderr

    def test_build_command_failure(self, tmp_path):
        ssh_effects = [(0, "", ""), (2, "", "build failed")]
        with self._mock_ssh_run(ssh_effects), self._mock_rsync(True):
            result = remote._build_remote(
                "freebsd_ports", tmp_path, "mypkg", self._target()
            )
        assert result.success is False
        assert result.returncode == 2

    def test_remote_work_path_contains_canonical_name(self, tmp_path):
        calls = []
        def capture_ssh(dest, cmd, **kw):
            calls.append(cmd)
            return (0, "", "")
        with patch("theseus.remote._ssh_run", side_effect=capture_ssh), \
             self._mock_rsync(True):
            remote._build_remote("nixpkgs", tmp_path, "mypkg-1.2", self._target())
        assert any("mypkg-1.2" in c for c in calls)

    def test_target_name_in_result(self, tmp_path):
        ssh_effects = [(0, "", ""), (0, "", "")]
        with self._mock_ssh_run(ssh_effects), self._mock_rsync(True):
            result = remote._build_remote(
                "freebsd_ports", tmp_path, "mypkg",
                self._target(name="my-target")
            )
        assert result.target == "my-target"


# ---------------------------------------------------------------------------
# build_on_target dispatch
# ---------------------------------------------------------------------------

class TestBuildOnTarget:
    @patch("theseus.remote._build_local")
    def test_dispatches_local(self, mock_local, tmp_path):
        mock_local.return_value = remote.BuildResult(True, "", "", 0)
        remote.build_on_target(
            "freebsd_ports", tmp_path, "pkg", {"local": True}
        )
        mock_local.assert_called_once()

    @patch("theseus.remote._build_remote")
    def test_dispatches_remote(self, mock_remote, tmp_path):
        mock_remote.return_value = remote.BuildResult(True, "", "", 0)
        remote.build_on_target(
            "freebsd_ports", tmp_path, "pkg", {"host": "myhost"}
        )
        mock_remote.assert_called_once()

    @patch("theseus.remote._build_remote")
    def test_not_local_goes_remote(self, mock_remote, tmp_path):
        mock_remote.return_value = remote.BuildResult(True, "", "", 0)
        remote.build_on_target(
            "nixpkgs", tmp_path, "pkg", {"local": False, "host": "h"}
        )
        mock_remote.assert_called_once()
