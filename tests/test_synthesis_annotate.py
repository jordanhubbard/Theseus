"""
Tests for theseus/synthesis/annotate.py — SynthesisAnnotator.
"""
import datetime
from pathlib import Path

import pytest

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from theseus.synthesis.annotate import SynthesisAnnotator, zsdl_path_for_spec_json
from theseus.synthesis.runner import SynthesisResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**kwargs) -> SynthesisResult:
    defaults = dict(
        canonical_name="testlib",
        backend_lang="python",
        status="success",
        model="claude-cli",
        attempted_at="2026-04-13T00:00:00Z",
        iterations=1,
        attempts=[],
        final_pass_count=5,
        final_fail_count=0,
        total_invariants=5,
        notes="Succeeded in 1 iteration.",
        infeasible_reason=None,
        failed_invariant_details={},
    )
    defaults.update(kwargs)
    return SynthesisResult(**defaults)


def _make_zsdl(tmp_path: Path, content: str = "spec: testlib\nversion: '>=1.0'\nbackend: python_module(testlib)\n") -> Path:
    p = tmp_path / "testlib.zspec.zsdl"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSynthesisAnnotator:
    def test_appends_synthesis_block(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        original = zsdl.read_text(encoding="utf-8")
        result = _make_result()
        SynthesisAnnotator().annotate(zsdl, result)
        after = zsdl.read_text(encoding="utf-8")
        assert after.startswith(original)
        assert "synthesis:" in after

    def test_preserves_original_content_exactly(self, tmp_path: Path) -> None:
        content = "spec: testlib\nversion: '>=1.0'\n# A comment\nbackend: python_module(testlib)\n"
        zsdl = _make_zsdl(tmp_path, content)
        result = _make_result()
        SynthesisAnnotator().annotate(zsdl, result)
        after = zsdl.read_text(encoding="utf-8")
        assert after.startswith(content)

    def test_status_in_block(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(status="partial")
        SynthesisAnnotator().annotate(zsdl, result)
        assert "status: partial" in zsdl.read_text(encoding="utf-8")

    def test_model_in_block(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(model="claude-opus-4-6")
        SynthesisAnnotator().annotate(zsdl, result)
        assert "claude-opus-4-6" in zsdl.read_text(encoding="utf-8")

    def test_counts_in_block(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(final_pass_count=10, final_fail_count=3, total_invariants=13)
        SynthesisAnnotator().annotate(zsdl, result)
        text = zsdl.read_text(encoding="utf-8")
        assert "pass_count: 10" in text
        assert "fail_count: 3" in text
        assert "total_invariants: 13" in text

    def test_null_infeasible_reason(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(infeasible_reason=None)
        SynthesisAnnotator().annotate(zsdl, result)
        assert "infeasible_reason: null" in zsdl.read_text(encoding="utf-8")

    def test_non_null_infeasible_reason(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(infeasible_reason="algorithm_underdetermined")
        SynthesisAnnotator().annotate(zsdl, result)
        assert "algorithm_underdetermined" in zsdl.read_text(encoding="utf-8")

    def test_failed_invariant_details_appear(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(
            status="partial",
            final_fail_count=1,
            failed_invariant_details={
                "testlib.call.one": {"status": "failed", "reason": "got wrong value"},
                "testlib.call.two": {"status": "failed", "reason": "timeout"},
            },
        )
        SynthesisAnnotator().annotate(zsdl, result)
        text = zsdl.read_text(encoding="utf-8")
        assert "testlib.call.one" in text
        assert "testlib.call.two" in text
        assert "got wrong value" in text

    def test_raises_on_double_annotate_without_flag(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result()
        ann = SynthesisAnnotator()
        ann.annotate(zsdl, result)
        with pytest.raises(ValueError, match="already exists"):
            ann.annotate(zsdl, result)

    def test_overwrites_existing_with_flag(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result1 = _make_result(status="failed")
        result2 = _make_result(status="success")
        ann = SynthesisAnnotator()
        ann.annotate(zsdl, result1)
        ann.annotate(zsdl, result2, overwrite_existing=True)
        text = zsdl.read_text(encoding="utf-8")
        assert "status: success" in text
        # Only one synthesis: block
        assert text.count("synthesis:") == 1

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        result = _make_result()
        with pytest.raises(FileNotFoundError):
            SynthesisAnnotator().annotate(tmp_path / "nonexistent.zspec.zsdl", result)

    @pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
    def test_appended_block_is_valid_yaml(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(
            notes="All good: no issues",
            failed_invariant_details={
                "testlib.inv.1": {"status": "failed", "reason": "value mismatch"},
            },
        )
        SynthesisAnnotator().annotate(zsdl, result)
        text = zsdl.read_text(encoding="utf-8")
        # Extract just the synthesis block
        idx = text.find("\nsynthesis:")
        synth_text = text[idx:] if idx >= 0 else text
        parsed = _yaml.safe_load(synth_text)
        assert parsed is not None
        assert "synthesis" in parsed

    def test_empty_invariant_annotations_block(self, tmp_path: Path) -> None:
        zsdl = _make_zsdl(tmp_path)
        result = _make_result(failed_invariant_details={})
        SynthesisAnnotator().annotate(zsdl, result)
        text = zsdl.read_text(encoding="utf-8")
        assert "invariant_annotations: {}" in text


class TestZsdlPathForSpecJson:
    def test_standard_path(self, tmp_path: Path) -> None:
        # Create a fake Makefile to mark the repo root
        (tmp_path / "Makefile").touch()
        (tmp_path / "_build" / "zspecs").mkdir(parents=True)
        spec_json = tmp_path / "_build" / "zspecs" / "zlib.zspec.json"
        spec_json.touch()
        result = zsdl_path_for_spec_json(spec_json)
        assert result == tmp_path / "zspecs" / "zlib.zspec.zsdl"

    def test_suffix_is_zsdl(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").touch()
        (tmp_path / "_build" / "zspecs").mkdir(parents=True)
        spec_json = tmp_path / "_build" / "zspecs" / "hashlib.zspec.json"
        spec_json.touch()
        result = zsdl_path_for_spec_json(spec_json)
        assert result.suffix == ".zsdl"
