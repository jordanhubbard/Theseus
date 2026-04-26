"""
Tests for tools/verify_all_specs.py.

Covers run_spec(), collect_specs(), and main() using synthetic spec fixtures.
"""
import json
import platform
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_all_specs as vas

DT_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "datetime.zspec.json"
PL_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pathlib.zspec.json"


# ---------------------------------------------------------------------------
# collect_specs
# ---------------------------------------------------------------------------

class TestCollectSpecs:
    def test_no_args_returns_all_zspecs(self):
        specs = vas.collect_specs([])
        names = [p.name for p in specs]
        assert "datetime.zspec.json" in names
        assert "zlib.zspec.json" in names

    def test_explicit_file(self):
        specs = vas.collect_specs([str(DT_SPEC_PATH)])
        assert len(specs) == 1
        assert specs[0] == DT_SPEC_PATH

    def test_directory_glob(self):
        zspecs_dir = REPO_ROOT / "_build" / "zspecs"
        specs = vas.collect_specs([str(zspecs_dir)])
        assert len(specs) >= 10  # at least 10 specs present

    def test_nonexistent_path_skipped(self, tmp_path):
        specs = vas.collect_specs([str(tmp_path / "doesnotexist.json")])
        assert specs == []


# ---------------------------------------------------------------------------
# run_spec
# ---------------------------------------------------------------------------

class TestRunSpec:
    def test_successful_spec(self):
        result = vas.run_spec(DT_SPEC_PATH)
        assert result["error"] is None
        assert result["canonical_name"] == "datetime"
        assert result["summary"]["total"] >= 15
        assert result["summary"]["failed"] == 0
        assert result["summary"]["passed"] >= 15

    def test_lib_version_populated(self):
        result = vas.run_spec(DT_SPEC_PATH)
        assert result["lib_version"] is not None
        assert "." in result["lib_version"]

    def test_invariants_list_populated(self):
        result = vas.run_spec(DT_SPEC_PATH)
        assert len(result["invariants"]) >= 15
        for inv in result["invariants"]:
            assert "id" in inv
            assert "passed" in inv
            assert "message" in inv
            assert "skip_reason" in inv

    def test_bad_spec_file_returns_error(self, tmp_path):
        bad = tmp_path / "bad.zspec.json"
        bad.write_text("{not valid json}")
        result = vas.run_spec(bad)
        assert result["error"] is not None
        assert result["summary"]["total"] == 0

    def test_missing_library_returns_error(self, tmp_path):
        fake = tmp_path / "fake.zspec.json"
        spec_data = {
            "schema_version": "0.1",
            "identity": {"canonical_name": "fake", "spec_for_versions": "any"},
            "provenance": {"derived_from": [], "not_derived_from": []},
            "library": {"backend": "python_module", "module_name": "definitely_not_a_real_module_xyz", "soname_patterns": []},
            "constants": {}, "types": {}, "wire_formats": {}, "functions": {},
            "invariants": [],
            "error_model": {"return_code_semantics": "", "error_codes": []},
        }
        fake.write_text(json.dumps(spec_data))
        result = vas.run_spec(fake)
        assert result["error"] is not None
        assert "LibraryNotFoundError" in result["error"]

    def test_pathlib_spec(self):
        result = vas.run_spec(PL_SPEC_PATH)
        assert result["error"] is None
        assert result["summary"]["failed"] == 0


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_explicit_spec_exits_0(self, tmp_path):
        out = tmp_path / "out.json"
        rc = vas.main([str(DT_SPEC_PATH), "--out", str(out)])
        assert rc == 0
        assert out.exists()

    def test_output_json_structure(self, tmp_path):
        out = tmp_path / "out.json"
        vas.main([str(DT_SPEC_PATH), str(PL_SPEC_PATH), "--out", str(out)])
        data = json.loads(out.read_text())
        assert "generated_at" in data
        assert "summary" in data
        assert "specs" in data
        assert len(data["specs"]) == 2
        s = data["summary"]
        assert "total_specs" in s
        assert "specs_ok" in s
        assert "specs_failed" in s
        assert "total_invariants" in s

    def test_summary_counts_correct(self, tmp_path):
        out = tmp_path / "out.json"
        vas.main([str(DT_SPEC_PATH), "--out", str(out)])
        data = json.loads(out.read_text())
        s = data["summary"]
        assert s["total_specs"] == 1
        assert s["specs_ok"] == 1
        assert s["specs_failed"] == 0
        assert s["passed"] >= 15
        assert s["failed"] == 0

    def test_no_specs_exits_2(self, tmp_path):
        # Pass an empty directory explicitly — collect_specs returns [] and
        # main() exits 2. Avoid invoking the default glob, which sweeps the
        # full 2,000+ spec corpus on every test run (and has crashed the
        # interpreter on macOS Python 3.10 via a buggy ctypes load:
        # SIGABRT in tools/verify_behavior.py:_load_ctypes).
        empty = tmp_path / "empty"
        empty.mkdir()
        rc = vas.main([str(empty), "--out", str(tmp_path / "out.json")])
        assert rc == 2

    def test_nonexistent_spec_handled(self, tmp_path):
        out = tmp_path / "out.json"
        # Passing a nonexistent file — collect_specs warns and returns []
        rc = vas.main([str(tmp_path / "ghost.zspec.json"), "--out", str(out)])
        assert rc == 2  # no specs found

    def test_failing_spec_exits_1(self, tmp_path):
        """A spec whose invariants assert false causes exit 1.

        Missing-library errors are now counted as 'specs_skipped' (signals
        environment, not contract failure) and do not flip the exit code —
        so the spec under test must use an importable module (sys) and
        contain an invariant that genuinely fails.
        """
        fake_spec = tmp_path / "bad.zspec.json"
        fake_spec.write_text(json.dumps({
            "schema_version": "0.1",
            "identity": {"canonical_name": "bad", "spec_for_versions": "any"},
            "provenance": {"derived_from": [], "not_derived_from": []},
            "library": {"backend": "python_module", "module_name": "sys", "soname_patterns": []},
            "constants": {}, "types": {}, "wire_formats": {}, "functions": {},
            "invariants": [{"id": "x", "description": "x", "category": "x",
                             "kind": "python_call_eq",
                             "spec": {"function": "version_info.major", "args": [], "expected": -999}}],
            "error_model": {"return_code_semantics": "", "error_codes": []},
        }))
        out = tmp_path / "out.json"
        rc = vas.main([str(fake_spec), "--out", str(out)])
        assert rc == 1

    def test_default_output_filename_written(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = vas.main([str(DT_SPEC_PATH)])
        assert rc == 0
        assert (tmp_path / "verify_all_specs_out.json").exists()


# ---------------------------------------------------------------------------
# Integration: real zspecs all pass
# ---------------------------------------------------------------------------

class TestAllSpecsIntegration:
    @pytest.mark.skipif(
        platform.system() == "Darwin",
        reason=(
            "Some ctypes specs (libpcap, lz4, pcre2, etc.) trigger a "
            "Fatal Python error: Aborted on macOS during ctypes.CDLL load — "
            "the load itself dies in C land before Python can catch it. "
            "Linux / FreeBSD do not exhibit this; the test runs there. "
            "Tracked as a follow-up: per-spec subprocess isolation in run_spec."
        ),
    )
    def test_all_real_specs_pass(self, tmp_path):
        out = tmp_path / "all.json"
        rc = vas.main(["--out", str(out)])
        assert rc == 0, f"Some specs failed; see {out}"
        data = json.loads(out.read_text())
        assert data["summary"]["specs_failed"] == 0
        assert data["summary"]["failed"] == 0

    def test_json_is_valid_for_baseline_use(self, tmp_path):
        """Output format matches what --baseline expects (list of {id, passed, message, skip_reason})."""
        import verify_behavior as vb
        out = tmp_path / "all.json"
        vas.main([str(DT_SPEC_PATH), "--out", str(out)])
        data = json.loads(out.read_text())
        # Extract the per-invariant list for the first spec and feed to _diff_results
        inv_list = data["specs"][0]["invariants"]
        bl = tmp_path / "baseline.json"
        bl.write_text(json.dumps(inv_list))
        # Identical baseline → 0 regressions
        assert vb._diff_results(bl, inv_list) == 0
