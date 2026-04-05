"""
Tests for the python_module backend with the certifi behavioral spec.

Organized as:
  - TestCertifiLoader: loading certifi via the python_module backend
  - TestCertifiVersion: version category invariants (__version__ format)
  - TestCertifiWhere: where category invariants (certifi.where() path properties)
  - TestCertifiContents: contents category invariants (path string structure)
  - TestCertifiAll: all 11 certifi invariants pass
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

CERTIFI_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "certifi.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def certifi_spec():
    return vb.SpecLoader().load(CERTIFI_SPEC_PATH)


@pytest.fixture(scope="module")
def certifi_mod(certifi_spec):
    return vb.LibraryLoader().load(certifi_spec["library"])


@pytest.fixture(scope="module")
def constants_map(certifi_spec):
    return vb.InvariantRunner().build_constants_map(certifi_spec["constants"])


@pytest.fixture(scope="module")
def registry(certifi_mod, constants_map):
    return vb.PatternRegistry(certifi_mod, constants_map)


# ---------------------------------------------------------------------------
# TestCertifiLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestCertifiLoader:
    def test_loads_certifi_spec(self, certifi_spec):
        assert isinstance(certifi_spec, dict)

    def test_all_required_sections_present(self, certifi_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in certifi_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, certifi_spec):
        assert certifi_spec["library"]["backend"] == "python_module"

    def test_module_name_is_certifi(self, certifi_spec):
        assert certifi_spec["library"]["module_name"] == "certifi"

    def test_loads_certifi_module(self, certifi_mod):
        import certifi
        assert certifi_mod is certifi

    def test_all_invariant_kinds_known(self, certifi_spec):
        for inv in certifi_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, certifi_spec):
        ids = [inv["id"] for inv in certifi_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_eleven(self, certifi_spec):
        assert len(certifi_spec["invariants"]) == 11


# ---------------------------------------------------------------------------
# TestCertifiVersion
# ---------------------------------------------------------------------------

class TestCertifiVersion:
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

    def test_version_contains_two_dots(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.count",
                "args": ["."],
                "expected": 2,
            },
        })
        assert ok, msg

    def test_version_is_nonempty_string(self, certifi_mod):
        assert isinstance(certifi_mod.__version__, str)
        assert len(certifi_mod.__version__) > 0

    def test_version_parts_are_numeric(self, certifi_mod):
        """date-based version: each part separated by '.' is a numeric string."""
        parts = certifi_mod.__version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit(), f"Non-numeric version part: {part!r}"


# ---------------------------------------------------------------------------
# TestCertifiWhere
# ---------------------------------------------------------------------------

class TestCertifiWhere:
    def test_where_ends_with_pem(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "endswith",
                "method_args": [".pem"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_where_ends_with_cacert_pem(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "endswith",
                "method_args": ["cacert.pem"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_where_contains_cacert(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "__contains__",
                "method_args": ["cacert"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_where_contains_certifi(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "__contains__",
                "method_args": ["certifi"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_where_is_absolute_path(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "startswith",
                "method_args": ["/"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_where_does_not_end_with_slash(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "endswith",
                "method_args": ["/"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_where_returns_string(self, certifi_mod):
        assert isinstance(certifi_mod.where(), str)

    def test_where_path_exists(self, certifi_mod):
        """The CA bundle file must actually exist on disk."""
        path = certifi_mod.where()
        assert os.path.exists(path), f"certifi.where() path does not exist: {path!r}"

    def test_where_path_is_file(self, certifi_mod):
        """The CA bundle path must point to a regular file, not a directory."""
        path = certifi_mod.where()
        assert os.path.isfile(path), f"certifi.where() is not a regular file: {path!r}"

    def test_where_is_not_dot_relative(self, certifi_mod):
        """certifi.where() must return an absolute path, not a relative one."""
        path = certifi_mod.where()
        assert not path.startswith("."), f"certifi.where() is a relative path: {path!r}"


# ---------------------------------------------------------------------------
# TestCertifiContents
# ---------------------------------------------------------------------------

class TestCertifiContents:
    def test_pem_occurs_once(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "count",
                "method_args": [".pem"],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_path_has_slashes(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "__contains__",
                "method_args": ["/"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_not_dot_relative(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "where",
                "args": [],
                "method": "startswith",
                "method_args": ["."],
                "expected": False,
            },
        })
        assert ok, msg

    def test_pem_file_readable(self, certifi_mod):
        """The CA bundle file can be opened and read."""
        path = certifi_mod.where()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(512)
        assert len(content) > 0, "certifi CA bundle file is empty"

    def test_pem_file_contains_certificate_header(self, certifi_mod):
        """The CA bundle PEM file contains at least one certificate block."""
        path = certifi_mod.where()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(4096)
        assert "CERTIFICATE" in content, \
            "certifi CA bundle does not contain any certificate data"


# ---------------------------------------------------------------------------
# TestCertifiAll — all 11 spec invariants must pass
# ---------------------------------------------------------------------------

class TestCertifiAll:
    def test_all_pass(self, certifi_spec, certifi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(certifi_spec, certifi_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, certifi_spec, certifi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(certifi_spec, certifi_mod)
        assert len(results) == 11

    def test_filter_by_category_version(self, certifi_spec, certifi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(certifi_spec, certifi_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_category_where(self, certifi_spec, certifi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(certifi_spec, certifi_mod, filter_category="where")
        assert len(results) == 6
        assert all(r.passed for r in results)

    def test_filter_by_category_contents(self, certifi_spec, certifi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(certifi_spec, certifi_mod, filter_category="contents")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_no_invariants_skipped(self, certifi_spec, certifi_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(certifi_spec, certifi_mod)
        skipped = [r for r in results if r.skip_reason is not None]
        assert not skipped, f"Unexpectedly skipped: {[r.inv_id for r in skipped]}"
