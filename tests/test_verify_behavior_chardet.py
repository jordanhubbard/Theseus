"""
Tests for the python_module backend and chardet-specific invariants
in tools/verify_behavior.py.

Organized as:
  - TestChardetLoader: loading chardet via the python_module backend
  - TestChardetPatterns: spot-check individual invariant kinds
  - TestChardetAll: all 16 chardet invariants pass; count check
  - TestChardetCLI: CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

CHARDET_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "chardet.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chardet_spec():
    return vb.SpecLoader().load(CHARDET_SPEC_PATH)


@pytest.fixture(scope="module")
def chardet_mod(chardet_spec):
    return vb.LibraryLoader().load(chardet_spec["library"])


@pytest.fixture(scope="module")
def constants_map(chardet_spec):
    return vb.InvariantRunner().build_constants_map(chardet_spec["constants"])


@pytest.fixture(scope="module")
def registry(chardet_mod, constants_map):
    return vb.PatternRegistry(chardet_mod, constants_map)


# ---------------------------------------------------------------------------
# TestChardetLoader — spec and module loading
# ---------------------------------------------------------------------------

class TestChardetLoader:
    def test_loads_chardet_spec(self, chardet_spec):
        assert isinstance(chardet_spec, dict)

    def test_all_required_sections_present(self, chardet_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in chardet_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, chardet_spec):
        assert chardet_spec["library"]["backend"] == "python_module"

    def test_loads_chardet_module(self, chardet_mod):
        import chardet
        assert chardet_mod is chardet

    def test_all_invariant_kinds_known(self, chardet_spec):
        for inv in chardet_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, chardet_spec):
        ids = [inv["id"] for inv in chardet_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestChardetPatterns — spot-check individual invariants via PatternRegistry
# ---------------------------------------------------------------------------

class TestChardetPatterns:
    def test_detect_ascii_hello_encoding(self, registry):
        import base64
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "SGVsbG8sIFdvcmxkIQ=="}],
                "method": "__getitem__",
                "method_args": ["encoding"],
                "expected": "ascii",
            },
        })
        assert ok, msg

    def test_detect_ascii_hello_confidence(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "SGVsbG8sIFdvcmxkIQ=="}],
                "method": "__getitem__",
                "method_args": ["confidence"],
                "expected": 1.0,
            },
        })
        assert ok, msg

    def test_detect_empty_encoding(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": ""}],
                "method": "__getitem__",
                "method_args": ["encoding"],
                "expected": "utf-8",
            },
        })
        assert ok, msg

    def test_detect_empty_confidence(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": ""}],
                "method": "__getitem__",
                "method_args": ["confidence"],
                "expected": 0.1,
            },
        })
        assert ok, msg

    def test_detect_utf8_bom_encoding(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "77u/SGVsbG8="}],
                "method": "__getitem__",
                "method_args": ["encoding"],
                "expected": "UTF-8-SIG",
            },
        })
        assert ok, msg

    def test_detect_utf8_bom_confidence(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "77u/SGVsbG8="}],
                "method": "__getitem__",
                "method_args": ["confidence"],
                "expected": 1.0,
            },
        })
        assert ok, msg

    def test_detect_japanese_encoding(self, registry):
        # 'こんにちは'.encode('utf-8') base64
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "44GT44KT44Gr44Gh44Gv"}],
                "method": "__getitem__",
                "method_args": ["encoding"],
                "expected": "utf-8",
            },
        })
        assert ok, msg

    def test_detect_japanese_confidence(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "44GT44KT44Gr44Gh44Gv"}],
                "method": "__getitem__",
                "method_args": ["confidence"],
                "expected": 0.99,
            },
        })
        assert ok, msg

    def test_detect_fox_encoding(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "VGhlIHF1aWNrIGJyb3duIGZveA=="}],
                "method": "__getitem__",
                "method_args": ["encoding"],
                "expected": "ascii",
            },
        })
        assert ok, msg

    def test_version_starts_with_digit(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["7"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_contains_dot(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["."],
                "expected": True,
            },
        })
        assert ok, msg

    def test_universal_detector_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "UniversalDetector.__name__.__eq__",
                "args": ["UniversalDetector"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrong_encoding_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "detect",
                "args": [{"type": "bytes_b64", "value": "SGVsbG8sIFdvcmxkIQ=="}],
                "method": "__getitem__",
                "method_args": ["encoding"],
                "expected": "latin-1",  # wrong — should be ascii
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestChardetAll — integration: all 16 invariants pass
# ---------------------------------------------------------------------------

class TestChardetAll:
    def test_all_pass(self, chardet_spec, chardet_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(chardet_spec, chardet_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, chardet_spec, chardet_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(chardet_spec, chardet_mod)
        assert len(results) == 16

    def test_no_skips(self, chardet_spec, chardet_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(chardet_spec, chardet_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_version_category(self, chardet_spec, chardet_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(chardet_spec, chardet_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_detect_category(self, chardet_spec, chardet_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(chardet_spec, chardet_mod, filter_category="detect")
        assert len(results) == 12
        assert all(r.passed for r in results)

    def test_filter_universal_detector_category(self, chardet_spec, chardet_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(chardet_spec, chardet_mod, filter_category="universal_detector")
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestChardetCLI — CLI end-to-end
# ---------------------------------------------------------------------------

class TestChardetCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(CHARDET_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(CHARDET_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "16 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(CHARDET_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "chardet.version.starts_with_digit" in out
        assert "chardet.detect_ascii.hello_encoding" in out

    def test_filter_detect_flag(self, capsys):
        vb.main([str(CHARDET_SPEC_PATH), "--filter", "detect", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(CHARDET_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 16
        assert all(r["passed"] for r in data)
