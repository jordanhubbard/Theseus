"""
Tests for the urllib3 Z-layer behavioral spec.

Organized as:
  - TestUrllib3Loader: loading urllib3 spec and module via the python_module backend
  - TestUrllib3Version: version invariants (2 invariants)
  - TestUrllib3Url: URL parsing invariants (8 invariants)
  - TestUrllib3Retry: Retry config invariants (3 invariants)
  - TestUrllib3Exceptions: exception class name invariants (3 invariants)
  - TestUrllib3Request: request helper invariants (2 invariants)
  - TestUrllib3All: integration — all 18 invariants pass, CLI end-to-end
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

URLLIB3_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "urllib3.zspec.json"

urllib3 = pytest.importorskip("urllib3", reason="urllib3 not installed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def urllib3_spec():
    return vb.SpecLoader().load(URLLIB3_SPEC_PATH)


@pytest.fixture(scope="module")
def urllib3_mod(urllib3_spec):
    return vb.LibraryLoader().load(urllib3_spec["library"])


@pytest.fixture(scope="module")
def constants_map(urllib3_spec):
    return vb.InvariantRunner().build_constants_map(urllib3_spec.get("constants", {}))


@pytest.fixture(scope="module")
def registry(urllib3_mod, constants_map):
    return vb.PatternRegistry(urllib3_mod, constants_map)


# ---------------------------------------------------------------------------
# TestUrllib3Loader
# ---------------------------------------------------------------------------

class TestUrllib3Loader:
    def test_loads_urllib3_spec(self, urllib3_spec):
        assert isinstance(urllib3_spec, dict)

    def test_all_required_sections_present(self, urllib3_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in urllib3_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, urllib3_spec):
        assert urllib3_spec["library"]["backend"] == "python_module"

    def test_loads_urllib3_module(self, urllib3_mod):
        import urllib3 as _urllib3
        assert urllib3_mod is _urllib3

    def test_all_invariant_kinds_known(self, urllib3_spec):
        for inv in urllib3_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, urllib3_spec):
        ids = [inv["id"] for inv in urllib3_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_spec_name(self, urllib3_spec):
        assert urllib3_spec["identity"]["canonical_name"] == "urllib3"


# ---------------------------------------------------------------------------
# TestUrllib3Version
# ---------------------------------------------------------------------------

class TestUrllib3Version:
    def test_version_starts_with_2(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["2."],
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

    def test_version_fails_wrong_prefix(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.startswith",
                "args": ["99."],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestUrllib3Url
# ---------------------------------------------------------------------------

class TestUrllib3Url:
    def _parse(self, registry, url, attr, expected):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.parse_url",
                "args": [url],
                "method": attr,
                "expected": expected,
            },
        })
        return ok, msg

    def test_host(self, registry):
        ok, msg = self._parse(registry, "http://example.com:8080/path", "host", "example.com")
        assert ok, msg

    def test_port(self, registry):
        ok, msg = self._parse(registry, "http://example.com:8080/path", "port", 8080)
        assert ok, msg

    def test_scheme(self, registry):
        ok, msg = self._parse(registry, "http://example.com:8080/path", "scheme", "http")
        assert ok, msg

    def test_path(self, registry):
        ok, msg = self._parse(registry, "http://example.com:8080/path", "path", "/path")
        assert ok, msg

    def test_simple_host(self, registry):
        ok, msg = self._parse(registry, "http://example.com/path", "host", "example.com")
        assert ok, msg

    def test_simple_scheme(self, registry):
        ok, msg = self._parse(registry, "http://example.com/path", "scheme", "http")
        assert ok, msg

    def test_simple_path(self, registry):
        ok, msg = self._parse(registry, "http://example.com/path", "path", "/path")
        assert ok, msg

    def test_auth(self, registry):
        ok, msg = self._parse(registry, "https://user:pass@host/", "auth", "user:pass")
        assert ok, msg

    def test_port_wrong_expected(self, registry):
        ok, msg = self._parse(registry, "http://example.com:8080/path", "port", 9999)
        assert not ok


# ---------------------------------------------------------------------------
# TestUrllib3Retry
# ---------------------------------------------------------------------------

class TestUrllib3Retry:
    def test_total_3(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.retry.Retry",
                "args": [3],
                "method": "total",
                "expected": 3,
            },
        })
        assert ok, msg

    def test_total_0(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.retry.Retry",
                "args": [0],
                "method": "total",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_read_attr(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.retry.Retry",
                "args": [],
                "kwargs": {"total": 5, "read": 2},
                "method": "read",
                "expected": 2,
            },
        })
        assert ok, msg

    def test_total_wrong_expected(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.retry.Retry",
                "args": [3],
                "method": "total",
                "expected": 999,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestUrllib3Exceptions
# ---------------------------------------------------------------------------

class TestUrllib3Exceptions:
    def test_max_retry_error_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.MaxRetryError.__name__.__eq__",
                "args": ["MaxRetryError"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_connect_timeout_error_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.ConnectTimeoutError.__name__.__eq__",
                "args": ["ConnectTimeoutError"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_http_error_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.HTTPError.__name__.__eq__",
                "args": ["HTTPError"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrong_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "exceptions.HTTPError.__name__.__eq__",
                "args": ["NotTheRightName"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestUrllib3Request
# ---------------------------------------------------------------------------

class TestUrllib3Request:
    def test_make_headers_keep_alive_key_present(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.request.make_headers",
                "args": [],
                "kwargs": {"keep_alive": True},
                "method": "__contains__",
                "method_args": ["connection"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_make_headers_keep_alive_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.request.make_headers",
                "args": [],
                "kwargs": {"keep_alive": True},
                "method": "__getitem__",
                "method_args": ["connection"],
                "expected": "keep-alive",
            },
        })
        assert ok, msg

    def test_make_headers_no_keep_alive_key_absent(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "util.request.make_headers",
                "args": [],
                "kwargs": {},
                "method": "__contains__",
                "method_args": ["connection"],
                "expected": False,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestUrllib3All — integration: all 18 invariants pass
# ---------------------------------------------------------------------------

class TestUrllib3All:
    def test_all_pass(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod)
        assert len(results) == 18

    def test_no_skips(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_url_category(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod, filter_category="url")
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_filter_by_retry_category(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod, filter_category="retry")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_exceptions_category(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod, filter_category="exceptions")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_version_category(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_request_category(self, urllib3_spec, urllib3_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(urllib3_spec, urllib3_mod, filter_category="request")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(URLLIB3_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(URLLIB3_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "18 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(URLLIB3_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "urllib3.version.starts_with_2" in out
        assert "urllib3.url.parse_url.auth" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(URLLIB3_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 18
        assert all(r["passed"] for r in data)
