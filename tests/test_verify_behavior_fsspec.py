"""
Tests for the python_module backend with fsspec-specific invariants
in tools/verify_behavior.py.

Organized as:
  - TestFsspecLoader: loading fsspec via the python_module backend
  - TestFsspecVersion: version category invariants
  - TestFsspecFilesystem: filesystem category invariants (file/memory protocols)
  - TestFsspecGetClass: get_class category invariants (LocalFileSystem/MemoryFileSystem)
  - TestFsspecImplementations: implementations category (available_protocols)
  - TestFsspecAbstractFs: abstract_fs category (AbstractFileSystem base class)
  - TestFsspecUrlToFs: url_to_fs category (URL parsing)
  - TestFsspecAll: all 12 invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

FSSPEC_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "fsspec.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fsspec_spec():
    return vb.SpecLoader().load(FSSPEC_SPEC_PATH)


@pytest.fixture(scope="module")
def fsspec_mod(fsspec_spec):
    return vb.LibraryLoader().load(fsspec_spec["library"])


@pytest.fixture(scope="module")
def constants_map(fsspec_spec):
    return vb.InvariantRunner().build_constants_map(fsspec_spec["constants"])


@pytest.fixture(scope="module")
def registry(fsspec_mod, constants_map):
    return vb.PatternRegistry(fsspec_mod, constants_map)


# ---------------------------------------------------------------------------
# TestFsspecLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestFsspecLoader:
    def test_loads_fsspec_spec(self, fsspec_spec):
        assert isinstance(fsspec_spec, dict)

    def test_all_required_sections_present(self, fsspec_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in fsspec_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, fsspec_spec):
        assert fsspec_spec["library"]["backend"] == "python_module"

    def test_module_name_is_fsspec(self, fsspec_spec):
        assert fsspec_spec["library"]["module_name"] == "fsspec"

    def test_loads_fsspec_module(self, fsspec_mod):
        import fsspec
        assert fsspec_mod is fsspec

    def test_all_invariant_kinds_known(self, fsspec_spec):
        for inv in fsspec_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, fsspec_spec):
        ids = [inv["id"] for inv in fsspec_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestFsspecVersion
# ---------------------------------------------------------------------------

class TestFsspecVersion:
    def test_version_is_str(self, registry):
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

    def test_version_is_string_type(self, fsspec_mod):
        """Direct check: __version__ is a non-empty string."""
        assert isinstance(fsspec_mod.__version__, str)
        assert len(fsspec_mod.__version__) > 0

    def test_version_wrong_value_fails(self, registry):
        """Sanity check: __version__ does not contain a space."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": [" "],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestFsspecFilesystem
# ---------------------------------------------------------------------------

class TestFsspecFilesystem:
    def test_file_protocol(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "filesystem",
                "args": ["file"],
                "method": "protocol",
                "expected": ["file", "local"],
            },
        })
        assert ok, msg

    def test_memory_protocol(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "filesystem",
                "args": ["memory"],
                "method": "protocol",
                "expected": "memory",
            },
        })
        assert ok, msg

    def test_file_protocol_len(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "filesystem",
                "args": ["file"],
                "method": "protocol",
                "method_chain": "__len__",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_file_protocol_contains_file(self, fsspec_mod):
        """Direct check: 'file' is one of the file protocol aliases."""
        fs = fsspec_mod.filesystem("file")
        assert "file" in fs.protocol

    def test_memory_protocol_is_string(self, fsspec_mod):
        """Direct check: memory protocol is a plain string, not a tuple."""
        fs = fsspec_mod.filesystem("memory")
        assert isinstance(fs.protocol, str)
        assert fs.protocol == "memory"


# ---------------------------------------------------------------------------
# TestFsspecGetClass
# ---------------------------------------------------------------------------

class TestFsspecGetClass:
    def test_file_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_filesystem_class",
                "args": ["file"],
                "method": "__name__",
                "expected": "LocalFileSystem",
            },
        })
        assert ok, msg

    def test_memory_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "get_filesystem_class",
                "args": ["memory"],
                "method": "__name__",
                "expected": "MemoryFileSystem",
            },
        })
        assert ok, msg

    def test_file_class_is_subclass_of_abstract(self, fsspec_mod):
        """Direct check: LocalFileSystem extends AbstractFileSystem."""
        cls = fsspec_mod.get_filesystem_class("file")
        assert issubclass(cls, fsspec_mod.AbstractFileSystem)

    def test_memory_class_is_subclass_of_abstract(self, fsspec_mod):
        """Direct check: MemoryFileSystem extends AbstractFileSystem."""
        cls = fsspec_mod.get_filesystem_class("memory")
        assert issubclass(cls, fsspec_mod.AbstractFileSystem)


# ---------------------------------------------------------------------------
# TestFsspecImplementations
# ---------------------------------------------------------------------------

class TestFsspecImplementations:
    def test_file_in_protocols(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_protocols",
                "args": [],
                "method": "__contains__",
                "method_args": ["file"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_memory_in_protocols(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_protocols",
                "args": [],
                "method": "__contains__",
                "method_args": ["memory"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_ftp_in_protocols(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "available_protocols",
                "args": [],
                "method": "__contains__",
                "method_args": ["ftp"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_protocols_is_list(self, fsspec_mod):
        """Direct check: available_protocols() returns a list."""
        result = fsspec_mod.available_protocols()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_bogus_protocol_not_in_list(self, fsspec_mod):
        """Sanity check: a nonsense protocol is not in the list."""
        result = fsspec_mod.available_protocols()
        assert "notaprotocol_xyz" not in result


# ---------------------------------------------------------------------------
# TestFsspecAbstractFs
# ---------------------------------------------------------------------------

class TestFsspecAbstractFs:
    def test_abstract_fs_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "AbstractFileSystem.__name__.__eq__",
                "args": ["AbstractFileSystem"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_abstract_fs_is_class(self, fsspec_mod):
        """Direct check: AbstractFileSystem is a class (type)."""
        import inspect
        assert inspect.isclass(fsspec_mod.AbstractFileSystem)

    def test_abstract_fs_wrong_name_fails(self, registry):
        """Sanity check: wrong name comparison returns False."""
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "AbstractFileSystem.__name__.__eq__",
                "args": ["WrongName"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestFsspecUrlToFs
# ---------------------------------------------------------------------------

class TestFsspecUrlToFs:
    def test_memory_url_path(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "url_to_fs",
                "args": ["memory://foo/bar"],
                "method": "__getitem__",
                "method_args": [1],
                "expected": "/foo/bar",
            },
        })
        assert ok, msg

    def test_url_to_fs_returns_tuple(self, fsspec_mod):
        """Direct check: url_to_fs returns a (fs, path) 2-tuple."""
        result = fsspec_mod.url_to_fs("memory://foo/bar")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_url_to_fs_file_class(self, fsspec_mod):
        """Direct check: file:// URL resolves to LocalFileSystem."""
        fs, path = fsspec_mod.url_to_fs("file:///tmp/x")
        assert type(fs).__name__ == "LocalFileSystem"

    def test_url_to_fs_memory_class(self, fsspec_mod):
        """Direct check: memory:// URL resolves to MemoryFileSystem."""
        fs, path = fsspec_mod.url_to_fs("memory://foo/bar")
        assert type(fs).__name__ == "MemoryFileSystem"


# ---------------------------------------------------------------------------
# TestFsspecAll — all 12 invariants must pass
# ---------------------------------------------------------------------------

class TestFsspecAll:
    def test_all_pass(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod)
        assert len(results) == 12

    def test_filter_by_category_version(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_filesystem(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod, filter_category="filesystem")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_get_class(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod, filter_category="get_class")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_implementations(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod, filter_category="implementations")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_abstract_fs(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod, filter_category="abstract_fs")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_url_to_fs(self, fsspec_spec, fsspec_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(fsspec_spec, fsspec_mod, filter_category="url_to_fs")
        assert len(results) == 1
        assert all(r.passed for r in results)
