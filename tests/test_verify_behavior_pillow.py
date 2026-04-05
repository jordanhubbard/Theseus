"""
Tests for the python_module backend and PIL.Image-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - PillowLoader: loading PIL.Image via the python_module backend
  - Pattern handlers for python_call_eq with method chaining (one class per category)
  - InvariantRunner integration: all 21 pillow invariants pass
  - CLI: verify-behavior runs pillow.zspec.json end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PILLOW_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pillow.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pillow_spec():
    return vb.SpecLoader().load(PILLOW_SPEC_PATH)


@pytest.fixture(scope="module")
def pillow_mod(pillow_spec):
    return vb.LibraryLoader().load(pillow_spec["library"])


@pytest.fixture(scope="module")
def constants_map(pillow_spec):
    return vb.InvariantRunner().build_constants_map(pillow_spec["constants"])


@pytest.fixture(scope="module")
def registry(pillow_mod, constants_map):
    return vb.PatternRegistry(pillow_mod, constants_map)


# ---------------------------------------------------------------------------
# PillowLoader
# ---------------------------------------------------------------------------

class TestPillowLoader:
    def test_loads_pillow_spec(self, pillow_spec):
        assert isinstance(pillow_spec, dict)

    def test_all_required_sections_present(self, pillow_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pillow_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pillow_spec):
        assert pillow_spec["library"]["backend"] == "python_module"

    def test_module_name_is_pil_image(self, pillow_spec):
        assert pillow_spec["library"]["module_name"] == "PIL.Image"

    def test_loads_pil_image_module(self, pillow_mod):
        from PIL import Image
        assert pillow_mod is Image

    def test_raises_on_nonexistent_module(self):
        with pytest.raises(vb.LibraryNotFoundError, match="Cannot import"):
            vb.LibraryLoader().load({
                "backend": "python_module",
                "module_name": "nonexistent_module_xyz",
            })

    def test_all_invariant_kinds_known(self, pillow_spec):
        for inv in pillow_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pillow_spec):
        ids = [inv["id"] for inv in pillow_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# image_new — Image.new() mode and dimension properties
# ---------------------------------------------------------------------------

class TestImageNew:
    def test_rgb_mode(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 10]],
                "method": "mode",
                "expected": "RGB",
            },
        })
        assert ok, msg

    def test_l_mode(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["L", [4, 4]],
                "method": "mode",
                "expected": "L",
            },
        })
        assert ok, msg

    def test_rgba_mode(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGBA", [2, 2]],
                "method": "mode",
                "expected": "RGBA",
            },
        })
        assert ok, msg

    def test_width(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 7]],
                "method": "width",
                "expected": 10,
            },
        })
        assert ok, msg

    def test_height(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 7]],
                "method": "height",
                "expected": 7,
            },
        })
        assert ok, msg

    def test_size_tuple(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 10]],
                "method": "size",
                "expected": [10, 10],
            },
        })
        assert ok, msg

    def test_fails_on_invalid_mode(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["NOSUCHMODE", [4, 4]],
                "method": "mode",
                "expected": "NOSUCHMODE",
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# pixel — getpixel() returns correct values for solid-color images
# ---------------------------------------------------------------------------

class TestPixel:
    def test_rgb_red(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [1, 1], {"type": "tuple", "value": [255, 0, 0]}],
                "method": "getpixel",
                "method_args": [[0, 0]],
                "expected": [255, 0, 0],
            },
        })
        assert ok, msg

    def test_rgb_green(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [1, 1], {"type": "tuple", "value": [0, 255, 0]}],
                "method": "getpixel",
                "method_args": [[0, 0]],
                "expected": [0, 255, 0],
            },
        })
        assert ok, msg

    def test_rgb_blue(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [1, 1], {"type": "tuple", "value": [0, 0, 255]}],
                "method": "getpixel",
                "method_args": [[0, 0]],
                "expected": [0, 0, 255],
            },
        })
        assert ok, msg

    def test_rgba_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGBA", [1, 1], {"type": "tuple", "value": [10, 20, 30, 128]}],
                "method": "getpixel",
                "method_args": [[0, 0]],
                "expected": [10, 20, 30, 128],
            },
        })
        assert ok, msg

    def test_fails_on_wrong_expected_pixel(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [1, 1], {"type": "tuple", "value": [255, 0, 0]}],
                "method": "getpixel",
                "method_args": [[0, 0]],
                "expected": [0, 0, 0],
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# convert — convert() changes the image mode
# ---------------------------------------------------------------------------

class TestConvert:
    def test_rgb_to_l(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [4, 4]],
                "method": "convert",
                "method_args": ["L"],
                "method_chain": "mode",
                "expected": "L",
            },
        })
        assert ok, msg

    def test_l_to_rgb(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["L", [4, 4]],
                "method": "convert",
                "method_args": ["RGB"],
                "method_chain": "mode",
                "expected": "RGB",
            },
        })
        assert ok, msg

    def test_rgb_to_rgba(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [4, 4]],
                "method": "convert",
                "method_args": ["RGBA"],
                "method_chain": "mode",
                "expected": "RGBA",
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# resize — resize() changes image dimensions
# ---------------------------------------------------------------------------

class TestResize:
    def test_half_size(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 10]],
                "method": "resize",
                "method_args": [[5, 5]],
                "method_chain": "size",
                "expected": [5, 5],
            },
        })
        assert ok, msg

    def test_upscale(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [4, 4]],
                "method": "resize",
                "method_args": [[8, 8]],
                "method_chain": "size",
                "expected": [8, 8],
            },
        })
        assert ok, msg

    def test_resize_width(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 10]],
                "method": "resize",
                "method_args": [[5, 5]],
                "method_chain": "width",
                "expected": 5,
            },
        })
        assert ok, msg

    def test_resize_height(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "new",
                "args": ["RGB", [10, 10]],
                "method": "resize",
                "method_args": [[5, 7]],
                "method_chain": "height",
                "expected": 7,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# constants — Image.Resampling enum values
# ---------------------------------------------------------------------------

class TestConstants:
    def test_nearest_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Resampling.__getitem__",
                "args": ["NEAREST"],
                "method": "value",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_bicubic_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Resampling.__getitem__",
                "args": ["BICUBIC"],
                "method": "value",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_lanczos_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Resampling.__getitem__",
                "args": ["LANCZOS"],
                "method": "value",
                "expected": 1,
            },
        })
        assert ok, msg

    def test_fails_on_unknown_resampling_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Resampling.__getitem__",
                "args": ["NO_SUCH_FILTER"],
                "method": "value",
                "expected": 0,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 21 pillow invariants must pass
# ---------------------------------------------------------------------------

class TestPillowAll:
    def test_all_pass(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod)
        assert len(results) == 21

    def test_no_skips(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_image_new(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod, filter_category="image_new")
        # rgb_mode, l_mode, rgba_mode, rgb_width, rgb_height, size_tuple = 6
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_by_pixel(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod, filter_category="pixel")
        # rgb_red, rgb_green, rgb_blue, rgba_val = 4
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_convert(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod, filter_category="convert")
        # rgb_to_l, l_to_rgb, rgb_to_rgba = 3
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_resize(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod, filter_category="resize")
        # half, upscale, one_by_one, width, height = 5
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_filter_by_constants(self, pillow_spec, pillow_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pillow_spec, pillow_mod, filter_category="constants")
        # nearest_value, bicubic_value, lanczos_value = 3
        assert len(results) == 3
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestPillowCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(PILLOW_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(PILLOW_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "21 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(PILLOW_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "pillow.image_new.rgb_mode" in out
        assert "pillow.pixel.rgb_red" in out

    def test_filter_flag(self, capsys):
        vb.main([str(PILLOW_SPEC_PATH), "--filter", "image_new", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(PILLOW_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 21
        assert all(r["passed"] for r in data)
