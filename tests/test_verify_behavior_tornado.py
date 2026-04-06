"""
Tests for the python_module backend with the tornado behavioral spec.

Organized as:
  - TestTornadoLoader: loading tornado via the python_module backend
  - TestTornadoVersion: version category invariants (version string and version_info)
  - TestTornadoEscape: escape category invariants (HTML/URL/JSON encoding)
  - TestTornadoClasses: classes category invariants (core public class names)
  - TestTornadoAll: all 15 tornado invariants pass
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

TORNADO_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "tornado.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tornado_spec():
    return vb.SpecLoader().load(TORNADO_SPEC_PATH)


@pytest.fixture(scope="module")
def tornado_mod(tornado_spec):
    return vb.LibraryLoader().load(tornado_spec["library"])


@pytest.fixture(scope="module")
def constants_map(tornado_spec):
    return vb.InvariantRunner().build_constants_map(tornado_spec["constants"])


@pytest.fixture(scope="module")
def registry(tornado_mod, constants_map):
    return vb.PatternRegistry(tornado_mod, constants_map)


# ---------------------------------------------------------------------------
# TestTornadoLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestTornadoLoader:
    def test_loads_tornado_spec(self, tornado_spec):
        assert isinstance(tornado_spec, dict)

    def test_all_required_sections_present(self, tornado_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in tornado_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, tornado_spec):
        assert tornado_spec["library"]["backend"] == "python_module"

    def test_module_name_is_tornado(self, tornado_spec):
        assert tornado_spec["library"]["module_name"] == "tornado"

    def test_loads_tornado_module(self, tornado_mod):
        import tornado
        assert tornado_mod is tornado

    def test_all_invariant_kinds_known(self, tornado_spec):
        for inv in tornado_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, tornado_spec):
        ids = [inv["id"] for inv in tornado_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_invariant_count_is_fifteen(self, tornado_spec):
        assert len(tornado_spec["invariants"]) == 15


# ---------------------------------------------------------------------------
# TestTornadoVersion
# ---------------------------------------------------------------------------

class TestTornadoVersion:
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

    def test_version_info_major_is_6(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "version_info.__getitem__",
                "args": [0],
                "expected": 6,
            },
        })
        assert ok, msg

    def test_version_is_nonempty_string(self, tornado_mod):
        assert isinstance(tornado_mod.version, str)
        assert len(tornado_mod.version) > 0

    def test_version_info_is_tuple(self, tornado_mod):
        assert isinstance(tornado_mod.version_info, tuple)

    def test_version_info_length_ge_3(self, tornado_mod):
        assert len(tornado_mod.version_info) >= 3


# ---------------------------------------------------------------------------
# TestTornadoEscape
# ---------------------------------------------------------------------------

class TestTornadoEscape:
    def test_xhtml_escape_tag(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.xhtml_escape",
                "args": ["<b>"],
                "expected": "&lt;b&gt;",
            },
        })
        assert ok, msg

    def test_xhtml_escape_full(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.xhtml_escape",
                "args": ["<b>hello</b>"],
                "expected": "&lt;b&gt;hello&lt;/b&gt;",
            },
        })
        assert ok, msg

    def test_xhtml_unescape_entities(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.xhtml_unescape",
                "args": ["&lt;b&gt;"],
                "expected": "<b>",
            },
        })
        assert ok, msg

    def test_url_escape_space(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.url_escape",
                "args": ["hello world"],
                "expected": "hello+world",
            },
        })
        assert ok, msg

    def test_url_unescape_plus(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.url_unescape",
                "args": ["hello+world"],
                "expected": "hello world",
            },
        })
        assert ok, msg

    def test_json_decode_key(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.json_decode",
                "args": ['{"a":1}'],
                "method": "__getitem__",
                "method_args": ["a"],
                "expected": 1,
            },
        })
        assert ok, msg

    def test_json_encode_is_callable(self, tornado_mod):
        import tornado.escape
        assert callable(tornado.escape.json_encode)

    def test_json_encode_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "escape.json_encode.__name__.__eq__",
                "args": ["json_encode"],
                "expected": True,
            },
        })
        assert ok, msg


# ---------------------------------------------------------------------------
# TestTornadoClasses
# ---------------------------------------------------------------------------

class TestTornadoClasses:
    def test_request_handler_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "web.RequestHandler.__name__.__eq__",
                "args": ["RequestHandler"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_application_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "web.Application.__name__.__eq__",
                "args": ["Application"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_ioloop_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ioloop.IOLoop.__name__.__eq__",
                "args": ["IOLoop"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_httpclient_error_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "httpclient.HTTPError.__name__.__eq__",
                "args": ["HTTPClientError"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_httprequest_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "httpclient.HTTPRequest.__name__.__eq__",
                "args": ["HTTPRequest"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_submodules_accessible(self, tornado_mod):
        """Submodule preloads make web/ioloop/httpclient/escape accessible as attributes."""
        import tornado.web
        import tornado.ioloop
        import tornado.httpclient
        import tornado.escape
        assert hasattr(tornado_mod, "web")
        assert hasattr(tornado_mod, "ioloop")
        assert hasattr(tornado_mod, "httpclient")
        assert hasattr(tornado_mod, "escape")


# ---------------------------------------------------------------------------
# TestTornadoAll — all 15 spec invariants must pass
# ---------------------------------------------------------------------------

class TestTornadoAll:
    def test_all_pass(self, tornado_spec, tornado_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tornado_spec, tornado_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, tornado_spec, tornado_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tornado_spec, tornado_mod)
        assert len(results) == 15

    def test_filter_by_category_version(self, tornado_spec, tornado_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tornado_spec, tornado_mod, filter_category="version")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_category_escape(self, tornado_spec, tornado_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tornado_spec, tornado_mod, filter_category="escape")
        assert len(results) == 7
        assert all(r.passed for r in results)

    def test_filter_by_category_classes(self, tornado_spec, tornado_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tornado_spec, tornado_mod, filter_category="classes")
        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_no_invariants_skipped(self, tornado_spec, tornado_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(tornado_spec, tornado_mod)
        skipped = [r for r in results if r.skip_reason is not None]
        assert not skipped, f"Unexpectedly skipped: {[r.inv_id for r in skipped]}"
