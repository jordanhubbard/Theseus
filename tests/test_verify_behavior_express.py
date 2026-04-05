"""
Tests for the express Z-layer behavioral spec.

express.zspec.zsdl covers:
  - app_settings: default express() app settings via app.get(setting)
  - router: express.Router() and express.Route path/method shape
  - routing: Route._handles_method() returning false for fresh routes
  - factory: node_factory_call_eq harness path for express.Router()

All invariants are offline-safe: no HTTP server is started.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT         = Path(__file__).resolve().parent.parent
EXPRESS_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "express.zspec.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import verify_behavior as vb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def express_spec():
    return vb.SpecLoader().load(EXPRESS_SPEC_PATH)


@pytest.fixture(scope="module")
def express_lib(express_spec):
    try:
        return vb.LibraryLoader().load(express_spec["library"])
    except vb.LibraryNotFoundError as exc:
        pytest.skip(f"express backend not available: {exc}")


@pytest.fixture(scope="module")
def registry(express_lib):
    return vb.PatternRegistry(express_lib, {})


# ---------------------------------------------------------------------------
# Library metadata
# ---------------------------------------------------------------------------

class TestExpressLibrary:
    def test_backend_is_cli(self, express_lib):
        assert isinstance(express_lib, vb.CLIBackend)

    def test_module_name(self, express_lib):
        assert express_lib.module_name == "express"

    def test_command_is_node(self, express_lib):
        assert "node" in express_lib.command

    def test_no_esm_flag(self, express_lib):
        assert express_lib.esm is False

    def test_spec_backend_field(self, express_spec):
        assert express_spec["library"]["backend"] == "cli"

    def test_spec_module_name_field(self, express_spec):
        assert express_spec["library"]["module_name"] == "express"


# ---------------------------------------------------------------------------
# App settings — node_factory_call_eq: express() -> app -> app.get(setting)
# ---------------------------------------------------------------------------

class TestExpressAppSettings:
    def _run(self, registry, express_spec, inv_id):
        inv = next(i for i in express_spec["invariants"] if i["id"] == inv_id)
        ok, msg = registry.run(inv)
        assert ok, msg

    def test_default_etag(self, registry, express_spec):
        self._run(registry, express_spec, "express.app_default.etag")

    def test_default_x_powered_by(self, registry, express_spec):
        self._run(registry, express_spec, "express.app_default.x_powered_by")

    def test_default_query_parser(self, registry, express_spec):
        self._run(registry, express_spec, "express.app_default.query_parser")

    def test_default_jsonp_callback_name(self, registry, express_spec):
        self._run(registry, express_spec, "express.app_default.jsonp_callback_name")

    def test_default_subdomain_offset(self, registry, express_spec):
        self._run(registry, express_spec, "express.app_default.subdomain_offset")

    def test_default_trust_proxy(self, registry, express_spec):
        self._run(registry, express_spec, "express.app_default.trust_proxy")

    def test_enabled_x_powered_by(self, registry, express_spec):
        self._run(registry, express_spec, "express.app.enabled_x_powered_by")

    def test_disabled_trust_proxy(self, registry, express_spec):
        self._run(registry, express_spec, "express.app.disabled_trust_proxy")


# ---------------------------------------------------------------------------
# Router — new express.Router().route(path) returns a Route-shaped object
# ---------------------------------------------------------------------------

class TestExpressRouter:
    def _run(self, registry, express_spec, inv_id):
        inv = next(i for i in express_spec["invariants"] if i["id"] == inv_id)
        ok, msg = registry.run(inv)
        assert ok, msg

    def test_fresh_route_shape(self, registry, express_spec):
        self._run(registry, express_spec, "express.router.fresh_route")

    def test_root_route_shape(self, registry, express_spec):
        self._run(registry, express_spec, "express.router.root_route")

    def test_factory_router_route_shape(self, registry, express_spec):
        self._run(registry, express_spec, "express.factory.router_route_shape")


# ---------------------------------------------------------------------------
# Routing — Route._handles_method() returns false before any handlers added
# ---------------------------------------------------------------------------

class TestExpressRouting:
    def _run(self, registry, express_spec, inv_id):
        inv = next(i for i in express_spec["invariants"] if i["id"] == inv_id)
        ok, msg = registry.run(inv)
        assert ok, msg

    def test_get_no_handlers(self, registry, express_spec):
        self._run(registry, express_spec, "express.route_handles.GET_no_handlers")

    def test_post_no_handlers(self, registry, express_spec):
        self._run(registry, express_spec, "express.route_handles.POST_no_handlers")

    def test_put_no_handlers(self, registry, express_spec):
        self._run(registry, express_spec, "express.route_handles.PUT_no_handlers")

    def test_delete_no_handlers(self, registry, express_spec):
        self._run(registry, express_spec, "express.route_handles.DELETE_no_handlers")

    def test_all_no_handlers(self, registry, express_spec):
        self._run(registry, express_spec, "express.route_handles.all_no_handlers")


# ---------------------------------------------------------------------------
# Full run via InvariantRunner
# ---------------------------------------------------------------------------

class TestExpressAll:
    def test_all_pass(self, express_spec, express_lib):
        runner = vb.InvariantRunner()
        results = runner.run_all(express_spec, express_lib)
        failures = [r for r in results if not r.passed and not r.skip_reason]
        assert not failures, "\n".join(
            f"{r.inv_id}: {r.message}" for r in failures
        )

    def test_invariant_count(self, express_spec, express_lib):
        runner = vb.InvariantRunner()
        results = runner.run_all(express_spec, express_lib)
        assert len(results) == 16

    def test_all_ids_unique(self, express_spec):
        ids = [inv["id"] for inv in express_spec["invariants"]]
        assert len(ids) == len(set(ids))

    def test_app_settings_category_count(self, express_spec, express_lib):
        runner = vb.InvariantRunner()
        results = runner.run_all(express_spec, express_lib, filter_category="app_settings")
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_router_category_count(self, express_spec, express_lib):
        runner = vb.InvariantRunner()
        results = runner.run_all(express_spec, express_lib, filter_category="router")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_routing_category_count(self, express_spec, express_lib):
        runner = vb.InvariantRunner()
        results = runner.run_all(express_spec, express_lib, filter_category="routing")
        assert len(results) == 5
        assert all(r.passed for r in results)
