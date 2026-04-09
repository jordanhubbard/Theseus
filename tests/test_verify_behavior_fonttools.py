"""
Tests for the python_module backend with the fontTools behavioral spec.

Organized as:
  - TestFontToolsLoader: loading the fontTools spec and module
  - TestFontToolsVersion: version category invariants
  - TestFontToolsTtlib: ttlib category invariants (TTFont, TTCollection, TTLibError)
  - TestFontToolsApi: api category invariants (misc, pens)
  - TestFontToolsAll: all 10 fontTools invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

FONTTOOLS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "fontTools.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fonttools_spec():
    return vb.SpecLoader().load(FONTTOOLS_SPEC_PATH)


@pytest.fixture(scope="module")
def fonttools_mod(fonttools_spec):
    return vb.LibraryLoader().load(fonttools_spec["library"])


@pytest.fixture(scope="module")
def constants_map(fonttools_spec):
    return vb.InvariantRunner().build_constants_map(fonttools_spec["constants"])


@pytest.fixture(scope="module")
def registry(fonttools_mod, constants_map):
    return vb.PatternRegistry(fonttools_mod, constants_map)


# ---------------------------------------------------------------------------
# TestFontToolsLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestFontToolsLoader:
    def test_loads_fonttools_spec(self, fonttools_spec):
        assert isinstance(fonttools_spec, dict)

    def test_all_required_sections_present(self, fonttools_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in fonttools_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, fonttools_spec):
        assert fonttools_spec["library"]["backend"] == "python_module"

    def test_module_name_is_fontTools(self, fonttools_spec):
        assert fonttools_spec["library"]["module_name"] == "fontTools"

    def test_loads_fonttools_module(self, fonttools_mod):
        import fontTools
        assert fonttools_mod is fontTools

    def test_all_invariant_kinds_known(self, fonttools_spec):
        for inv in fonttools_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, fonttools_spec):
        ids = [inv["id"] for inv in fonttools_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_ten(self, fonttools_spec):
        assert len(fonttools_spec["invariants"]) == 18

    def test_submodules_loaded(self, fonttools_mod):
        """Submodules must be accessible as attributes after library load."""
        import fontTools.ttLib
        import fontTools.pens.basePen
        assert hasattr(fonttools_mod, "ttLib")
        assert hasattr(fonttools_mod, "pens")
        assert hasattr(fonttools_mod, "misc")


# ---------------------------------------------------------------------------
# TestFontToolsVersion
# ---------------------------------------------------------------------------

class TestFontToolsVersion:
    def test_version_contains_dot(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.__contains__",
                "args": ["."],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_is_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version.__class__.__name__.__eq__",
                "args": ["str"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_version_nonempty(self, fonttools_mod):
        assert isinstance(fonttools_mod.version, str)
        assert len(fonttools_mod.version) > 0

    def test_version_matches_dunder_version(self, fonttools_mod):
        """fontTools.version and fontTools.__version__ must be the same string."""
        assert fonttools_mod.version == fonttools_mod.__version__


# ---------------------------------------------------------------------------
# TestFontToolsTtlib
# ---------------------------------------------------------------------------

class TestFontToolsTtlib:
    def test_ttlib_module_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ttLib.__name__.__eq__",
                "args": ["fontTools.ttLib"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TTFont_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ttLib.TTFont.__name__.__eq__",
                "args": ["TTFont"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TTCollection_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ttLib.TTCollection.__name__.__eq__",
                "args": ["TTCollection"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TTLibError_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ttLib.TTLibError.__name__.__eq__",
                "args": ["TTLibError"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_TTLibError_is_exception(self, fonttools_mod):
        """TTLibError must be a subclass of Exception."""
        assert issubclass(fonttools_mod.ttLib.TTLibError, Exception)

    def test_TTFont_is_class(self, fonttools_mod):
        """TTFont must be a class."""
        assert isinstance(fonttools_mod.ttLib.TTFont, type)


# ---------------------------------------------------------------------------
# TestFontToolsApi
# ---------------------------------------------------------------------------

class TestFontToolsApi:
    def test_misc_module_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "misc.__name__.__eq__",
                "args": ["fontTools.misc"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_AbstractPen_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pens.basePen.AbstractPen.__name__.__eq__",
                "args": ["AbstractPen"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_BasePen_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "pens.basePen.BasePen.__name__.__eq__",
                "args": ["BasePen"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_AbstractPen_is_class(self, fonttools_mod):
        """AbstractPen must be a class (abstract base)."""
        assert isinstance(fonttools_mod.pens.basePen.AbstractPen, type)

    def test_BasePen_subclasses_AbstractPen(self, fonttools_mod):
        """BasePen must be a subclass of AbstractPen."""
        assert issubclass(
            fonttools_mod.pens.basePen.BasePen,
            fonttools_mod.pens.basePen.AbstractPen,
        )


# ---------------------------------------------------------------------------
# TestFontToolsAll — all 10 fontTools invariants must pass
# ---------------------------------------------------------------------------

class TestFontToolsAll:
    def test_all_pass(self, fonttools_spec, fonttools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fonttools_spec, fonttools_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, fonttools_spec, fonttools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fonttools_spec, fonttools_mod)
        assert len(results) == 18

    def test_filter_by_category_version(self, fonttools_spec, fonttools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fonttools_spec, fonttools_mod, filter_category="version")
        assert len(results) >= 2
        assert all(r.passed for r in results)

    def test_filter_by_category_ttlib(self, fonttools_spec, fonttools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fonttools_spec, fonttools_mod, filter_category="ttlib")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_category_api(self, fonttools_spec, fonttools_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fonttools_spec, fonttools_mod, filter_category="api")
        assert len(results) == 3
        assert all(r.passed for r in results)
