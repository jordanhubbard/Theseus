"""
Tests for the python_module backend and colorama-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestColoramaLoader: loading colorama via the python_module backend
  - TestColoramaVersion: version category invariants
  - TestColoramaFore: fore category invariants (Fore.RED, GREEN, BLUE, RESET)
  - TestColoramaBack: back category invariants (Back.RED, GREEN, RESET)
  - TestColoramaStyle: style category invariants (Style.BRIGHT, DIM, NORMAL, RESET_ALL)
  - TestColoramaAll: all 12 colorama invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

COLORAMA_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "colorama.zspec.json"

ESC = "\u001b"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def colorama_spec():
    return vb.SpecLoader().load(COLORAMA_SPEC_PATH)


@pytest.fixture(scope="module")
def colorama_mod(colorama_spec):
    return vb.LibraryLoader().load(colorama_spec["library"])


@pytest.fixture(scope="module")
def constants_map(colorama_spec):
    return vb.InvariantRunner().build_constants_map(colorama_spec["constants"])


@pytest.fixture(scope="module")
def registry(colorama_mod, constants_map):
    return vb.PatternRegistry(colorama_mod, constants_map)


# ---------------------------------------------------------------------------
# TestColoramaLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestColoramaLoader:
    def test_loads_colorama_spec(self, colorama_spec):
        assert isinstance(colorama_spec, dict)

    def test_all_required_sections_present(self, colorama_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in colorama_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, colorama_spec):
        assert colorama_spec["library"]["backend"] == "python_module"

    def test_module_name_is_colorama(self, colorama_spec):
        assert colorama_spec["library"]["module_name"] == "colorama"

    def test_loads_colorama_module(self, colorama_mod):
        import colorama
        assert colorama_mod is colorama

    def test_all_invariant_kinds_known(self, colorama_spec):
        for inv in colorama_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, colorama_spec):
        ids = [inv["id"] for inv in colorama_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestColoramaVersion
# ---------------------------------------------------------------------------

class TestColoramaVersion:
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

    def test_version_is_string(self, colorama_mod):
        assert isinstance(colorama_mod.__version__, str)
        assert len(colorama_mod.__version__) > 0

    def test_version_has_at_least_two_parts(self, colorama_mod):
        parts = colorama_mod.__version__.split(".")
        assert len(parts) >= 2


# ---------------------------------------------------------------------------
# TestColoramaFore
# ---------------------------------------------------------------------------

class TestColoramaFore:
    def test_fore_red(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Fore.RED.__eq__",
                "args": [f"{ESC}[31m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_fore_green(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Fore.GREEN.__eq__",
                "args": [f"{ESC}[32m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_fore_blue(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Fore.BLUE.__eq__",
                "args": [f"{ESC}[34m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_fore_reset(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Fore.RESET.__eq__",
                "args": [f"{ESC}[39m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_fore_constants_are_strings(self, colorama_mod):
        """All Fore constants are strings (subclass of str)."""
        import colorama
        assert isinstance(colorama_mod.Fore.RED, str)
        assert isinstance(colorama_mod.Fore.GREEN, str)
        assert isinstance(colorama_mod.Fore.BLUE, str)
        assert isinstance(colorama_mod.Fore.RESET, str)

    def test_fore_red_wrong_value_fails(self, registry):
        """Sanity check: Fore.RED != ESC[32m (green)."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Fore.RED.__eq__",
                "args": [f"{ESC}[32m"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestColoramaBack
# ---------------------------------------------------------------------------

class TestColoramaBack:
    def test_back_red(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Back.RED.__eq__",
                "args": [f"{ESC}[41m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_back_green(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Back.GREEN.__eq__",
                "args": [f"{ESC}[42m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_back_reset(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Back.RESET.__eq__",
                "args": [f"{ESC}[49m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_back_constants_are_strings(self, colorama_mod):
        """All Back constants are strings."""
        assert isinstance(colorama_mod.Back.RED, str)
        assert isinstance(colorama_mod.Back.GREEN, str)
        assert isinstance(colorama_mod.Back.RESET, str)

    def test_back_fore_codes_differ(self, colorama_mod):
        """Background and foreground codes for the same color are different."""
        assert colorama_mod.Back.RED != colorama_mod.Fore.RED
        assert colorama_mod.Back.GREEN != colorama_mod.Fore.GREEN


# ---------------------------------------------------------------------------
# TestColoramaStyle
# ---------------------------------------------------------------------------

class TestColoramaStyle:
    def test_style_bright(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Style.BRIGHT.__eq__",
                "args": [f"{ESC}[1m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_style_dim(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Style.DIM.__eq__",
                "args": [f"{ESC}[2m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_style_normal(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Style.NORMAL.__eq__",
                "args": [f"{ESC}[22m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_style_reset_all(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Style.RESET_ALL.__eq__",
                "args": [f"{ESC}[0m"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_style_constants_are_strings(self, colorama_mod):
        """All Style constants are strings."""
        assert isinstance(colorama_mod.Style.BRIGHT, str)
        assert isinstance(colorama_mod.Style.DIM, str)
        assert isinstance(colorama_mod.Style.NORMAL, str)
        assert isinstance(colorama_mod.Style.RESET_ALL, str)

    def test_style_bright_dim_normal_all_distinct(self, colorama_mod):
        """BRIGHT, DIM, and NORMAL are all distinct codes."""
        assert colorama_mod.Style.BRIGHT != colorama_mod.Style.DIM
        assert colorama_mod.Style.DIM != colorama_mod.Style.NORMAL
        assert colorama_mod.Style.BRIGHT != colorama_mod.Style.NORMAL


# ---------------------------------------------------------------------------
# TestColoramaAll — all 12 colorama invariants must pass
# ---------------------------------------------------------------------------

class TestColoramaAll:
    def test_all_pass(self, colorama_spec, colorama_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(colorama_spec, colorama_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, colorama_spec, colorama_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(colorama_spec, colorama_mod)
        assert len(results) == 12

    def test_filter_by_category_version(self, colorama_spec, colorama_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(colorama_spec, colorama_mod, filter_category="version")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_fore(self, colorama_spec, colorama_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(colorama_spec, colorama_mod, filter_category="fore")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_category_back(self, colorama_spec, colorama_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(colorama_spec, colorama_mod, filter_category="back")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_style(self, colorama_spec, colorama_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(colorama_spec, colorama_mod, filter_category="style")
        assert len(results) == 4
        assert all(r.passed for r in results)
