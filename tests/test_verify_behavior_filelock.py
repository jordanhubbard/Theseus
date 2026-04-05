"""
Tests for the python_module backend and filelock-specific behavioral invariants
in tools/verify_behavior.py.

Organized as:
  - TestFilelockLoader: loading filelock spec and module via python_module backend
  - TestFilelockVersion: __version__ is a string containing a dot
  - TestFilelockClasses: SoftFileLock, BaseFileLock, Timeout name attributes
  - TestFilelockTimeoutException: Timeout.__bases__[0].__name__ == 'TimeoutError'
  - TestFilelockLockAttrs: FileLock instance properties (lock_file, is_locked, timeout)
  - TestFilelockSoftLockAttrs: SoftFileLock instance properties
  - TestFilelockAll: all 12 invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

FILELOCK_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "filelock.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def filelock_spec():
    return vb.SpecLoader().load(FILELOCK_SPEC_PATH)


@pytest.fixture(scope="module")
def filelock_mod(filelock_spec):
    return vb.LibraryLoader().load(filelock_spec["library"])


@pytest.fixture(scope="module")
def constants_map(filelock_spec):
    return vb.InvariantRunner().build_constants_map(filelock_spec["constants"])


@pytest.fixture(scope="module")
def registry(filelock_mod, constants_map):
    return vb.PatternRegistry(filelock_mod, constants_map)


# ---------------------------------------------------------------------------
# TestFilelockLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestFilelockLoader:
    def test_loads_filelock_spec(self, filelock_spec):
        assert isinstance(filelock_spec, dict)

    def test_all_required_sections_present(self, filelock_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in filelock_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, filelock_spec):
        assert filelock_spec["library"]["backend"] == "python_module"

    def test_module_name_is_filelock(self, filelock_spec):
        assert filelock_spec["library"]["module_name"] == "filelock"

    def test_loads_filelock_module(self, filelock_mod):
        import filelock
        assert filelock_mod is filelock

    def test_all_invariant_kinds_known(self, filelock_spec):
        for inv in filelock_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, filelock_spec):
        ids = [inv["id"] for inv in filelock_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestFilelockVersion
# ---------------------------------------------------------------------------

class TestFilelockVersion:
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

    def test_version_is_nonempty_string(self, filelock_mod):
        assert isinstance(filelock_mod.__version__, str)
        assert len(filelock_mod.__version__) > 0


# ---------------------------------------------------------------------------
# TestFilelockClasses
# ---------------------------------------------------------------------------

class TestFilelockClasses:
    def test_softfilelock_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "SoftFileLock.__name__.__eq__",
                "args": ["SoftFileLock"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_basefilelock_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "BaseFileLock.__name__.__eq__",
                "args": ["BaseFileLock"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_timeout_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Timeout.__name__.__eq__",
                "args": ["Timeout"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_public_classes_exposed(self, filelock_mod):
        """FileLock, SoftFileLock, BaseFileLock, and Timeout must be present in the module."""
        assert hasattr(filelock_mod, "FileLock")
        assert hasattr(filelock_mod, "SoftFileLock")
        assert hasattr(filelock_mod, "BaseFileLock")
        assert hasattr(filelock_mod, "Timeout")

    def test_softfilelock_subclass_of_basefilelock(self, filelock_mod):
        """SoftFileLock must inherit from BaseFileLock."""
        assert issubclass(filelock_mod.SoftFileLock, filelock_mod.BaseFileLock)

    def test_filelock_subclass_of_basefilelock(self, filelock_mod):
        """FileLock (platform variant) must inherit from BaseFileLock."""
        assert issubclass(filelock_mod.FileLock, filelock_mod.BaseFileLock)


# ---------------------------------------------------------------------------
# TestFilelockTimeoutException
# ---------------------------------------------------------------------------

class TestFilelockTimeoutException:
    def test_timeout_bases_first_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "Timeout.__bases__.__getitem__",
                "args": [0],
                "method": "__name__",
                "expected": "TimeoutError",
            },
        })
        assert ok, msg

    def test_timeout_is_exception_subclass(self, filelock_mod):
        """Timeout must be a subclass of Exception."""
        assert issubclass(filelock_mod.Timeout, Exception)

    def test_timeout_is_raiseable(self, filelock_mod):
        """Timeout must be raiseable and catchable as Exception."""
        with pytest.raises(Exception):
            raise filelock_mod.Timeout("/tmp/test.lock")


# ---------------------------------------------------------------------------
# TestFilelockLockAttrs — FileLock instance properties
# ---------------------------------------------------------------------------

class TestFilelockLockAttrs:
    def test_lock_file_path(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FileLock",
                "args": ["/tmp/t.lock"],
                "method": "lock_file",
                "expected": "/tmp/t.lock",
            },
        })
        assert ok, msg

    def test_is_locked_false_initially(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FileLock",
                "args": ["/tmp/t.lock"],
                "method": "is_locked",
                "expected": False,
            },
        })
        assert ok, msg

    def test_default_timeout_is_minus_one(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FileLock",
                "args": ["/tmp/t.lock"],
                "method": "timeout",
                "expected": -1,
            },
        })
        assert ok, msg

    def test_lock_has_acquire_and_release(self, filelock_mod):
        """FileLock instances must have acquire and release methods."""
        lock = filelock_mod.FileLock("/tmp/t.lock")
        assert hasattr(lock, "acquire") and callable(lock.acquire)
        assert hasattr(lock, "release") and callable(lock.release)


# ---------------------------------------------------------------------------
# TestFilelockSoftLockAttrs — SoftFileLock instance properties
# ---------------------------------------------------------------------------

class TestFilelockSoftLockAttrs:
    def test_softlock_lock_file_path(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "SoftFileLock",
                "args": ["/tmp/s.lock"],
                "method": "lock_file",
                "expected": "/tmp/s.lock",
            },
        })
        assert ok, msg

    def test_softlock_is_locked_false_initially(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "SoftFileLock",
                "args": ["/tmp/s.lock"],
                "method": "is_locked",
                "expected": False,
            },
        })
        assert ok, msg

    def test_softlock_default_timeout_is_minus_one(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "SoftFileLock",
                "args": ["/tmp/s.lock"],
                "method": "timeout",
                "expected": -1,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestFilelockAll — all 12 invariants must pass
# ---------------------------------------------------------------------------

class TestFilelockAll:
    def test_all_pass(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod)
        assert len(results) == 12

    def test_filter_by_category_version(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_classes(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod, filter_category="classes")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_timeout_exception(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod, filter_category="timeout_exception")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_category_lock_attrs(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod, filter_category="lock_attrs")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_softlock_attrs(self, filelock_spec, filelock_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(filelock_spec, filelock_mod, filter_category="softlock_attrs")
        assert len(results) == 3
        assert all(r.passed for r in results)
