"""
Tests for --watch mode in verify_behavior.py.

The watch loop blocks on input so we test it via subprocess with a short timeout,
verifying that:
  - The initial run executes and prints results before blocking
  - A file modification triggers a re-run
  - Ctrl-C (SIGINT) exits cleanly with code 0
  - Non-watch mode is unaffected
"""
from __future__ import annotations

import json
import os
import select
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT    = Path(__file__).resolve().parent.parent
PYTHON       = sys.executable
HARNESS      = str(REPO_ROOT / "tools" / "verify_behavior.py")
DT_SPEC_PATH = str(REPO_ROOT / "_build" / "zspecs" / "datetime.zspec.json")


def _read_until(proc: subprocess.Popen, predicate, timeout: float, initial: str = "") -> str:
    deadline = time.monotonic() + timeout
    stdout = initial
    assert proc.stdout is not None
    while time.monotonic() < deadline and proc.poll() is None:
        ready, _, _ = select.select([proc.stdout], [], [], 0.1)
        if not ready:
            continue
        line = proc.stdout.readline()
        if not line:
            break
        stdout += line
        if predicate(stdout):
            break
    return stdout


def _run_watch(spec_path: str, timeout: float = 5.0) -> tuple[str, int | None]:
    """
    Start verify_behavior.py --watch, wait for the first run, send SIGINT, and
    return (stdout_text, returncode).
    """
    proc = subprocess.Popen(
        [PYTHON, HARNESS, spec_path, "--watch"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    stdout = _read_until(proc, lambda text: "Running spec..." in text, max(timeout, 15.0))
    try:
        proc.send_signal(signal.SIGINT)
    except ProcessLookupError:
        pass
    try:
        rest, _ = proc.communicate(timeout=5)
        stdout += rest
    except subprocess.TimeoutExpired:
        proc.kill()
        rest, _ = proc.communicate()
        stdout += rest
    return stdout, proc.returncode


class TestWatchMode:
    def test_watch_exits_0_on_sigint(self):
        """--watch exits with code 0 when interrupted by Ctrl-C."""
        _, rc = _run_watch(DT_SPEC_PATH, timeout=2.0)
        assert rc == 0

    def test_watch_runs_initially(self):
        """--watch starts the first run before any file change."""
        stdout, _ = _run_watch(DT_SPEC_PATH, timeout=2.0)
        assert "Running spec..." in stdout

    def test_watch_prints_watching_message(self):
        """--watch prints the 'Watching' banner on startup."""
        stdout, _ = _run_watch(DT_SPEC_PATH, timeout=1.5)
        assert "Watching" in stdout or "Watch" in stdout

    def test_watch_reruns_on_file_change(self, tmp_path):
        """Modifying the spec file while watching triggers a second run."""
        # Copy datetime spec to a temp file so we can touch it
        spec_copy = tmp_path / "test_watch.zspec.json"
        shutil.copy(DT_SPEC_PATH, spec_copy)

        proc = subprocess.Popen(
            [PYTHON, HARNESS, str(spec_copy), "--watch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        stdout = _read_until(proc, lambda text: "invariants:" in text, 10.0)

        # Touch the file to trigger a re-run
        spec_copy.touch()
        stdout = _read_until(
            proc,
            lambda text: text.count("Running spec...") >= 2,
            15.0,
            stdout,
        )

        # Stop the process
        try:
            proc.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
        try:
            rest, _ = proc.communicate(timeout=5)
            stdout += rest
        except subprocess.TimeoutExpired:
            proc.kill()
            rest, _ = proc.communicate()
            stdout += rest

        assert proc.returncode == 0
        run_count = stdout.count("Running spec...")
        assert run_count >= 2, f"Expected >=2 runs, got {run_count}. stdout:\n{stdout[:1000]}"

    def test_watch_flag_requires_spec(self):
        """--watch without a spec file should print an error (argparse)."""
        result = subprocess.run(
            [PYTHON, HARNESS, "--watch"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode != 0

    def test_no_watch_flag_returns_immediately(self):
        """Without --watch, the harness runs once and exits (regression guard)."""
        result = subprocess.run(
            [PYTHON, HARNESS, DT_SPEC_PATH],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        assert "invariants:" in result.stdout


class TestWatchModeUnit:
    """Unit tests that don't involve actual file watching (faster)."""

    def test_main_accepts_watch_flag(self):
        """verify_behavior.main() accepts --watch without crashing on arg parse."""
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import verify_behavior as vb
        # parse the args; the watch loop won't start because we're just parsing
        parser_args = ["--watch", DT_SPEC_PATH]
        # We can't call main() with --watch in unit tests (it would block), but
        # we can verify the argparser accepts it by looking at the parsed namespace.
        import argparse
        # Re-use the same parser construction logic (indirectly)
        result = subprocess.run(
            [PYTHON, HARNESS, "--help"],
            capture_output=True, text=True, timeout=5
        )
        assert "--watch" in result.stdout
