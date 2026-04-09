"""
Tests for the chalk Z-layer spec (chalk v5, ESM).

chalk.zspec.zsdl: color methods, text styles, level:0 stripping.
Also tests the ESM support in the node backend (dynamic import() path).
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT       = Path(__file__).resolve().parent.parent
CHALK_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "chalk.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chalk_spec():
    return vb.SpecLoader().load(CHALK_SPEC_PATH)


@pytest.fixture(scope="module")
def chalk_lib(chalk_spec):
    try:
        return vb.LibraryLoader().load(chalk_spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"chalk not available: {exc}")


# ---------------------------------------------------------------------------
# Library metadata
# ---------------------------------------------------------------------------

class TestChalkLibrary:
    def test_esm_flag_set(self, chalk_lib):
        assert chalk_lib.esm is True

    def test_module_name(self, chalk_lib):
        assert chalk_lib.module_name == "chalk"

    def test_command_is_node(self, chalk_lib):
        assert "node" in chalk_lib.command


# ---------------------------------------------------------------------------
# Color invariants
# ---------------------------------------------------------------------------

class TestChalkColors:
    def _run(self, chalk_spec, chalk_lib, inv_id):
        inv = next(i for i in chalk_spec["invariants"] if i["id"] == inv_id)
        ok, msg = vb.PatternRegistry(chalk_lib, {}).run(inv)
        assert ok, msg

    def test_red(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.red")

    def test_green(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.green")


# ---------------------------------------------------------------------------
# Style invariants
# ---------------------------------------------------------------------------

class TestChalkStyles:
    def _run(self, chalk_spec, chalk_lib, inv_id):
        inv = next(i for i in chalk_spec["invariants"] if i["id"] == inv_id)
        ok, msg = vb.PatternRegistry(chalk_lib, {}).run(inv)
        assert ok, msg

    def test_bold(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.bold")

    def test_italic(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.italic")

    def test_underline(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.underline")

    def test_bgBlue(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.bgBlue")


# ---------------------------------------------------------------------------
# Stripping (level:0)
# ---------------------------------------------------------------------------

class TestChalkStrip:
    def _run(self, chalk_spec, chalk_lib, inv_id):
        inv = next(i for i in chalk_spec["invariants"] if i["id"] == inv_id)
        ok, msg = vb.PatternRegistry(chalk_lib, {}).run(inv)
        assert ok, msg

    def test_strip_red(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.strip_red")

    def test_strip_bold(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.strip_bold")

    def test_strip_bgBlue(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.strip_bgBlue")

    def test_strip_underline(self, chalk_spec, chalk_lib):
        self._run(chalk_spec, chalk_lib, "chalk.strip_underline")


# ---------------------------------------------------------------------------
# ESM path coverage — verifies the async-import() branch is exercised
# ---------------------------------------------------------------------------

class TestESMPath:
    def test_esm_flag_propagated_to_lib(self, chalk_lib):
        assert chalk_lib.esm is True

    def test_esm_module_call_succeeds(self, chalk_spec, chalk_lib):
        """InvariantRunner successfully runs all invariants using the ESM path."""
        results = vb.InvariantRunner().run_all(chalk_spec, chalk_lib)
        assert all(r.passed or r.skip_reason for r in results)


# ---------------------------------------------------------------------------
# Full run via InvariantRunner
# ---------------------------------------------------------------------------

class TestChalkAll:
    def test_all_pass(self, chalk_spec, chalk_lib):
        results = vb.InvariantRunner().run_all(chalk_spec, chalk_lib)
        failures = [r for r in results if not r.passed and not r.skip_reason]
        assert not failures, "\n".join(f"{r.inv_id}: {r.message}" for r in failures)

    def test_invariant_count(self, chalk_spec):
        assert len(chalk_spec["invariants"]) == 25
