"""
Tests for the python_module backend and pathspec-specific pattern handlers
in tools/verify_behavior.py.

Organized as:
  - TestPathspecLoader: loading pathspec via the python_module backend
  - TestPathspecVersion: version category invariants
  - TestPathspecMatchFile: match_file category invariants (PathSpec.from_lines + match_file chain)
  - TestPathspecDirectory: directory category invariants (directory pattern matching)
  - TestPathspecPatterns: patterns category invariants (GitWildMatchPattern)
  - TestPathspecLookupPattern: lookup_pattern category invariants
  - TestPathspecError: error category invariants (invalid pattern type raises KeyError)
  - TestPathspecAll: all 14 pathspec invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

PATHSPEC_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "pathspec.zspec.json"


# ---------------------------------------------------------------------------
# Skip entire module if pathspec is not installed
# ---------------------------------------------------------------------------

def _pathspec_available() -> bool:
    try:
        import pathspec  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _pathspec_available(),
    reason="pathspec not installed on this system",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pathspec_spec():
    return vb.SpecLoader().load(PATHSPEC_SPEC_PATH)


@pytest.fixture(scope="module")
def pathspec_mod(pathspec_spec):
    return vb.LibraryLoader().load(pathspec_spec["library"])


@pytest.fixture(scope="module")
def constants_map(pathspec_spec):
    return vb.InvariantRunner().build_constants_map(pathspec_spec["constants"])


@pytest.fixture(scope="module")
def registry(pathspec_mod, constants_map):
    return vb.PatternRegistry(pathspec_mod, constants_map)


# ---------------------------------------------------------------------------
# TestPathspecLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestPathspecLoader:
    def test_loads_pathspec_spec(self, pathspec_spec):
        assert isinstance(pathspec_spec, dict)

    def test_all_required_sections_present(self, pathspec_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in pathspec_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, pathspec_spec):
        assert pathspec_spec["library"]["backend"] == "python_module"

    def test_module_name_is_pathspec(self, pathspec_spec):
        assert pathspec_spec["library"]["module_name"] == "pathspec"

    def test_loads_pathspec_module(self, pathspec_mod):
        import pathspec
        assert pathspec_mod is pathspec

    def test_all_invariant_kinds_known(self, pathspec_spec):
        for inv in pathspec_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, pathspec_spec):
        ids = [inv["id"] for inv in pathspec_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestPathspecVersion
# ---------------------------------------------------------------------------

class TestPathspecVersion:
    def test_version_is_string(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__class__.__name__.__eq__",
                "args": ["str"],
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

    def test_version_non_empty(self, pathspec_mod):
        """Direct check: __version__ is a non-empty string."""
        assert isinstance(pathspec_mod.__version__, str)
        assert len(pathspec_mod.__version__) > 0

    def test_version_has_dot(self, pathspec_mod):
        """Direct check: version string has at least one dot."""
        assert "." in pathspec_mod.__version__


# ---------------------------------------------------------------------------
# TestPathspecMatchFile
# ---------------------------------------------------------------------------

class TestPathspecMatchFile:
    def test_py_pattern_matches_py(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["*.py"]],
                "method": "match_file",
                "method_args": ["hello.py"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_py_pattern_no_match_txt(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["*.py"]],
                "method": "match_file",
                "method_args": ["hello.txt"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_txt_pattern_matches_txt(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["*.txt"]],
                "method": "match_file",
                "method_args": ["readme.txt"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_txt_pattern_no_match_py(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["*.txt"]],
                "method": "match_file",
                "method_args": ["readme.py"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_negation_excludes_test_files(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["*.py", "!test_*.py"]],
                "method": "match_file",
                "method_args": ["test_foo.py"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_negation_keeps_non_test_py(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["*.py", "!test_*.py"]],
                "method": "match_file",
                "method_args": ["hello.py"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_gitignore_backend(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitignore", ["*.py"]],
                "method": "match_file",
                "method_args": ["app.py"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_match_file_returns_bool(self, pathspec_mod):
        """Direct check: match_file returns a bool, not a truthy/falsy object."""
        spec = pathspec_mod.PathSpec.from_lines("gitwildmatch", ["*.py"])
        assert spec.match_file("hello.py") is True
        assert spec.match_file("hello.txt") is False


# ---------------------------------------------------------------------------
# TestPathspecDirectory
# ---------------------------------------------------------------------------

class TestPathspecDirectory:
    def test_src_dir_matches_file_under_src(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["src/"]],
                "method": "match_file",
                "method_args": ["src/foo.py"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_src_dir_no_match_other(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["gitwildmatch", ["src/"]],
                "method": "match_file",
                "method_args": ["other/foo.py"],
                "expected": False,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestPathspecPatterns
# ---------------------------------------------------------------------------

class TestPathspecPatterns:
    def test_gitwildmatch_regex_pattern(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "patterns.GitWildMatchPattern",
                "args": ["*.py"],
                "method": "regex",
                "method_chain": "pattern",
                "expected": "^(?:.+/)?[^/]*\\.py(?:(?P<ps_d>/)|$)",
            },
        })
        assert ok, msg

    def test_gitwildmatch_regex_is_compiled(self, pathspec_mod):
        """Direct check: GitWildMatchPattern produces a compiled regex object."""
        import re
        gp = pathspec_mod.patterns.GitWildMatchPattern("*.py")
        assert isinstance(gp.regex, re.Pattern)

    def test_gitwildmatch_regex_matches_py_files(self, pathspec_mod):
        """Direct check: the compiled regex matches a .py filename."""
        gp = pathspec_mod.patterns.GitWildMatchPattern("*.py")
        assert gp.regex.search("hello.py") is not None
        assert gp.regex.search("hello.txt") is None


# ---------------------------------------------------------------------------
# TestPathspecLookupPattern
# ---------------------------------------------------------------------------

class TestPathspecLookupPattern:
    def test_lookup_gitwildmatch_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "lookup_pattern",
                "args": ["gitwildmatch"],
                "method": "__name__",
                "expected": "GitWildMatchPattern",
            },
        })
        assert ok, msg

    def test_lookup_pattern_returns_class(self, pathspec_mod):
        """Direct check: lookup_pattern returns a class (callable)."""
        cls = pathspec_mod.lookup_pattern("gitwildmatch")
        assert callable(cls)
        assert cls.__name__ == "GitWildMatchPattern"


# ---------------------------------------------------------------------------
# TestPathspecError
# ---------------------------------------------------------------------------

class TestPathspecError:
    def test_invalid_pattern_type_raises(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_raises",
            "spec": {
                "function": "PathSpec.from_lines",
                "args": ["nonexistent_pattern_type", ["*.py"]],
                "expected_exception": "KeyError",
            },
        })
        assert ok, msg

    def test_invalid_pattern_type_raises_directly(self, pathspec_mod):
        """Direct check: from_lines with unknown pattern type raises KeyError."""
        with pytest.raises(KeyError):
            pathspec_mod.PathSpec.from_lines("nonexistent_pattern_type", ["*.py"])


# ---------------------------------------------------------------------------
# TestPathspecAll — all 14 pathspec invariants must pass
# ---------------------------------------------------------------------------

class TestPathspecAll:
    def test_all_pass(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod)
        assert len(results) == 14

    def test_filter_by_category_version(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_match_file(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod, filter_category="match_file")
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_filter_by_category_directory(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod, filter_category="directory")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_patterns(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod, filter_category="patterns")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_lookup_pattern(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod, filter_category="lookup_pattern")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_error(self, pathspec_spec, pathspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(pathspec_spec, pathspec_mod, filter_category="error")
        assert len(results) == 1
        assert all(r.passed for r in results)
