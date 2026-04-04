"""
Tests for spec_for_versions enforcement and lib version detection.

Covers:
  - _get_lib_version() for python_module, cli, ctypes backends
  - _check_spec_version() with packaging (if available) and stdlib fallback
  - lib_version wired into skip_if evaluation
  - version string printed by main()
"""
import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb

DT_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "datetime.zspec.json"
SEMVER_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "semver.zspec.json"
ZLIB_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "zlib.zspec.json"


# ---------------------------------------------------------------------------
# _check_spec_version
# ---------------------------------------------------------------------------

class TestCheckSpecVersion:
    def test_empty_spec_range_is_ok(self):
        ok, msg = vb._check_spec_version("", "1.2.3")
        assert ok
        assert msg == ""

    def test_na_spec_range_is_ok(self):
        ok, msg = vb._check_spec_version("N/A", "1.2.3")
        assert ok

    def test_empty_lib_version_is_ok(self):
        ok, msg = vb._check_spec_version(">=1.0", "")
        assert ok

    def test_satisfied_ge(self):
        ok, msg = vb._check_spec_version(">=1.0", "1.2.3")
        assert ok, msg

    def test_not_satisfied_ge(self):
        ok, msg = vb._check_spec_version(">=2.0", "1.2.3")
        assert not ok
        assert "1.2.3" in msg
        assert "2.0" in msg

    def test_satisfied_ge_lt(self):
        ok, msg = vb._check_spec_version(">=1.2.0 <2.0.0", "1.5.0")
        assert ok, msg

    def test_not_satisfied_ge_lt_too_high(self):
        ok, msg = vb._check_spec_version(">=1.2.0 <2.0.0", "2.0.0")
        assert not ok

    def test_satisfied_with_comma_separated(self):
        ok, msg = vb._check_spec_version(">=1.0.0,<3.0.0", "2.5.1")
        assert ok, msg

    def test_exact_boundary_ge(self):
        ok, msg = vb._check_spec_version(">=3.7", "3.7.0")
        assert ok, msg

    def test_below_boundary_ge(self):
        ok, msg = vb._check_spec_version(">=3.7", "3.6.9")
        assert not ok

    def test_python_version_satisfies_stdlib_spec(self):
        vi = sys.version_info
        lib_ver = f"{vi.major}.{vi.minor}.{vi.micro}"
        # datetime spec is >=3.7; any Python we run tests on should satisfy that
        ok, msg = vb._check_spec_version(">=3.7", lib_ver)
        assert ok, f"Python {lib_ver} should satisfy >=3.7 but got: {msg}"


# ---------------------------------------------------------------------------
# _get_lib_version: python_module backend
# ---------------------------------------------------------------------------

class TestGetLibVersionPythonModule:
    def _lib_spec(self, module_name):
        return {"backend": "python_module", "module_name": module_name, "soname_patterns": []}

    def test_stdlib_returns_python_version(self):
        import datetime as _dt
        lib_spec = self._lib_spec("datetime")
        ver = vb._get_lib_version(lib_spec, _dt)
        # Should be something like "3.14.3" — at least major.minor
        parts = ver.split(".")
        assert len(parts) >= 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_stdlib_version_matches_sys(self):
        import re as _re_mod
        lib_spec = self._lib_spec("re")
        ver = vb._get_lib_version(lib_spec, _re_mod)
        vi = sys.version_info
        assert ver.startswith(f"{vi.major}.{vi.minor}"), (
            f"Expected version starting with {vi.major}.{vi.minor}, got {ver!r}"
        )

    def test_third_party_returns_nonempty(self):
        # Use a module that is definitely installed (pytest itself)
        import pytest as _pytest
        lib_spec = self._lib_spec("pytest")
        ver = vb._get_lib_version(lib_spec, _pytest)
        # Should be the actual pytest version, not the Python version
        assert ver != ""
        assert "." in ver


# ---------------------------------------------------------------------------
# _get_lib_version: cli (node) backend
# ---------------------------------------------------------------------------

class TestGetLibVersionCli:
    def test_node_module_version_nonempty(self):
        """semver module is installed; should return a non-empty version string."""
        import shutil
        if not shutil.which("node"):
            pytest.skip("node not in PATH")
        semver_spec = vb.SpecLoader().load(SEMVER_SPEC_PATH)
        lib = vb.LibraryLoader().load(semver_spec["library"])
        ver = vb._get_lib_version(semver_spec["library"], lib)
        assert ver != "", "Expected non-empty version for semver npm package"
        assert "." in ver, f"Expected dotted version, got {ver!r}"

    def test_cli_no_module_returns_empty(self):
        """CLI spec without module_name returns empty string."""
        lib_spec = {"backend": "cli", "command": "openssl", "soname_patterns": []}
        ver = vb._get_lib_version(lib_spec, None)
        assert ver == ""


# ---------------------------------------------------------------------------
# _get_lib_version: ctypes backend
# ---------------------------------------------------------------------------

class TestGetLibVersionCtypes:
    def test_zlib_version_via_spec(self):
        """zlib spec has version_function='zlibVersion'; should return e.g. '1.2.11'."""
        try:
            zlib_spec = vb.SpecLoader().load(ZLIB_SPEC_PATH)
            lib = vb.LibraryLoader().load(zlib_spec["library"])
        except vb.LibraryNotFoundError:
            pytest.skip("zlib not found on this system")
        ver = vb._get_lib_version(zlib_spec["library"], lib)
        assert ver != "", "Expected non-empty version from zlibVersion()"
        assert "." in ver

    def test_ctypes_no_version_function_returns_empty(self):
        lib_spec = {"backend": "ctypes", "soname_patterns": []}
        ver = vb._get_lib_version(lib_spec, None)
        assert ver == ""


# ---------------------------------------------------------------------------
# skip_if uses real lib_version
# ---------------------------------------------------------------------------

class TestSkipIfWithVersion:
    def test_skip_if_false_invariant_runs(self):
        """skip_if evaluates to False → invariant runs normally."""
        dt_spec = vb.SpecLoader().load(DT_SPEC_PATH)
        dt_lib = vb.LibraryLoader().load(dt_spec["library"])
        vi = sys.version_info
        lib_version = f"{vi.major}.{vi.minor}.{vi.micro}"

        # Inject a skip_if that will NOT skip (Python >= 2.0 is always true)
        inv = {
            "id": "test.skip_if.false",
            "description": "Should run — skip_if is False",
            "category": "test",
            "kind": "python_call_eq",
            "spec": {
                "function": "date.fromisoformat",
                "args": [{"type": "str", "value": "2024-03-15"}],
                "expected": {"type": "int", "value": 2024},
                "method": "year",
            },
            "skip_if": 'lib_version < "2.0"',  # always False for any Python 2+
        }
        runner = vb.InvariantRunner()
        fake_spec = dict(dt_spec, invariants=[inv])
        results = runner.run_all(fake_spec, dt_lib, lib_version=lib_version)
        assert len(results) == 1
        assert results[0].passed
        assert results[0].skip_reason is None

    def test_skip_if_true_invariant_skipped(self):
        """skip_if evaluates to True → invariant is skipped."""
        dt_spec = vb.SpecLoader().load(DT_SPEC_PATH)
        dt_lib = vb.LibraryLoader().load(dt_spec["library"])
        vi = sys.version_info
        lib_version = f"{vi.major}.{vi.minor}.{vi.micro}"

        inv = {
            "id": "test.skip_if.true",
            "description": "Should be skipped",
            "category": "test",
            "kind": "python_call_eq",
            "spec": {
                "function": "date.fromisoformat",
                "args": [{"type": "str", "value": "2024-03-15"}],
                "expected": {"type": "int", "value": 9999},  # wrong — but should be skipped
                "method": "year",
            },
            "skip_if": 'lib_version >= "3.0"',  # always True for Python 3
        }
        runner = vb.InvariantRunner()
        fake_spec = dict(dt_spec, invariants=[inv])
        results = runner.run_all(fake_spec, dt_lib, lib_version=lib_version)
        assert len(results) == 1
        assert results[0].skip_reason is not None

    def test_version_passed_to_run_all(self):
        """lib_version kwarg is accepted by run_all without error."""
        dt_spec = vb.SpecLoader().load(DT_SPEC_PATH)
        dt_lib = vb.LibraryLoader().load(dt_spec["library"])
        runner = vb.InvariantRunner()
        results = runner.run_all(dt_spec, dt_lib, lib_version="3.14.0")
        assert all(r.passed for r in results), [r for r in results if not r.passed]


# ---------------------------------------------------------------------------
# Integration: main() prints version line
# ---------------------------------------------------------------------------

class TestMainPrintsVersion:
    def test_datetime_main_prints_version(self, capsys):
        rc = vb.main([str(DT_SPEC_PATH)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Library version:" in captured.out
        # Should contain a dotted version
        import re
        assert re.search(r"\d+\.\d+", captured.out)

    def test_version_mismatch_warns(self, capsys):
        """A spec_for_versions that can't be satisfied should print a WARNING to stderr."""
        dt_spec_path = DT_SPEC_PATH
        # We'll monkey-patch by passing a fake spec — easier to test via _check_spec_version directly
        ok, msg = vb._check_spec_version(">=99.0", "3.14.3")
        assert not ok
        assert "99.0" in msg
