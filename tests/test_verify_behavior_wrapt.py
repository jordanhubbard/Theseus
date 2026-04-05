"""
Tests for the wrapt Z-layer behavioral spec (wrapt.zspec.zsdl).

Covers:
  - SpecLoader: loading wrapt spec via python_module backend
  - python_call_eq handler with wrapt-specific patterns
  - InvariantRunner integration: all 12 invariants pass
  - CLI: verify-behavior runs wrapt.zspec.json end-to-end

Categories verified:
  version (1)         — __version__ contains a dot
  object_proxy (4)    — ObjectProxy wraps int, str, zero, negative int via __wrapped__
  proxy_class (3)     — ObjectProxy, FunctionWrapper, BoundFunctionWrapper class names
  attributes (2)      — decorator and wrap_function_wrapper are present Python functions
  proxy_identity (2)  — ObjectProxy wraps list and False, identity preserved by equality
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

WRAPT_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "wrapt.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def wrapt_spec():
    return vb.SpecLoader().load(WRAPT_SPEC_PATH)


@pytest.fixture(scope="module")
def wrapt_mod(wrapt_spec):
    return vb.LibraryLoader().load(wrapt_spec["library"])


@pytest.fixture(scope="module")
def constants_map(wrapt_spec):
    return vb.InvariantRunner().build_constants_map(wrapt_spec["constants"])


@pytest.fixture(scope="module")
def registry(wrapt_mod, constants_map):
    return vb.PatternRegistry(wrapt_mod, constants_map)


# ---------------------------------------------------------------------------
# TestWraptSpecLoader — spec loading and module import
# ---------------------------------------------------------------------------

class TestWraptSpecLoader:
    def test_loads_wrapt_spec(self, wrapt_spec):
        assert isinstance(wrapt_spec, dict)

    def test_all_required_sections_present(self, wrapt_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in wrapt_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, wrapt_spec):
        assert wrapt_spec["library"]["backend"] == "python_module"

    def test_module_name_is_wrapt(self, wrapt_spec):
        assert wrapt_spec["library"]["module_name"] == "wrapt"

    def test_loads_wrapt_module(self, wrapt_mod):
        import wrapt
        assert wrapt_mod is wrapt

    def test_all_invariant_kinds_known(self, wrapt_spec):
        for inv in wrapt_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, wrapt_spec):
        ids = [inv["id"] for inv in wrapt_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# TestWraptVersion — __version__ is a string containing a dot
# ---------------------------------------------------------------------------

class TestWraptVersion:
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

    def test_version_is_string(self, wrapt_mod):
        assert isinstance(wrapt_mod.__version__, str)

    def test_version_not_empty(self, wrapt_mod):
        assert len(wrapt_mod.__version__) > 0

    def test_version_starts_with_digit(self, wrapt_mod):
        assert wrapt_mod.__version__[0].isdigit()

    def test_wrong_expected_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "__version__.__contains__",
                "args": ["."],
                "expected": False,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestWraptObjectProxy — ObjectProxy wraps values and exposes __wrapped__
# ---------------------------------------------------------------------------

class TestWraptObjectProxy:
    def test_int_wrapped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [42],
                "method": "__wrapped__",
                "expected": 42,
            },
        })
        assert ok, msg

    def test_str_wrapped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": ["hello"],
                "method": "__wrapped__",
                "expected": "hello",
            },
        })
        assert ok, msg

    def test_zero_wrapped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [0],
                "method": "__wrapped__",
                "expected": 0,
            },
        })
        assert ok, msg

    def test_neg_wrapped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [-1],
                "method": "__wrapped__",
                "expected": -1,
            },
        })
        assert ok, msg

    def test_wrong_expected_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [42],
                "method": "__wrapped__",
                "expected": 99,
            },
        })
        assert not ok

    def test_objectproxy_is_type(self, wrapt_mod):
        assert isinstance(wrapt_mod.ObjectProxy, type)

    def test_objectproxy_requires_arg(self, wrapt_mod):
        with pytest.raises(TypeError):
            wrapt_mod.ObjectProxy()


# ---------------------------------------------------------------------------
# TestWraptProxyClass — class names are correct strings
# ---------------------------------------------------------------------------

class TestWraptProxyClass:
    def test_objectproxy_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy.__name__.__eq__",
                "args": ["ObjectProxy"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_functionwrapper_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionWrapper.__name__.__eq__",
                "args": ["FunctionWrapper"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_boundfunctionwrapper_class_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "BoundFunctionWrapper.__name__.__eq__",
                "args": ["BoundFunctionWrapper"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_objectproxy_name_direct(self, wrapt_mod):
        assert wrapt_mod.ObjectProxy.__name__ == "ObjectProxy"

    def test_functionwrapper_name_direct(self, wrapt_mod):
        assert wrapt_mod.FunctionWrapper.__name__ == "FunctionWrapper"

    def test_boundfunctionwrapper_name_direct(self, wrapt_mod):
        assert wrapt_mod.BoundFunctionWrapper.__name__ == "BoundFunctionWrapper"

    def test_wrong_name_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy.__name__.__eq__",
                "args": ["NotObjectProxy"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestWraptAttributes — key public API members are present as Python functions
# ---------------------------------------------------------------------------

class TestWraptAttributes:
    def test_decorator_is_function(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "decorator.__class__.__name__.__eq__",
                "args": ["function"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_wrap_function_wrapper_is_function(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "wrap_function_wrapper.__class__.__name__.__eq__",
                "args": ["function"],
                "expected": True,
            },
        })
        assert ok, msg

    def test_decorator_callable(self, wrapt_mod):
        assert callable(wrapt_mod.decorator)

    def test_wrap_function_wrapper_callable(self, wrapt_mod):
        assert callable(wrapt_mod.wrap_function_wrapper)

    def test_patch_function_wrapper_callable(self, wrapt_mod):
        assert callable(wrapt_mod.patch_function_wrapper)

    def test_objectproxy_in_module(self, wrapt_mod):
        assert hasattr(wrapt_mod, "ObjectProxy")

    def test_functionwrapper_in_module(self, wrapt_mod):
        assert hasattr(wrapt_mod, "FunctionWrapper")

    def test_boundfunctionwrapper_in_module(self, wrapt_mod):
        assert hasattr(wrapt_mod, "BoundFunctionWrapper")


# ---------------------------------------------------------------------------
# TestWraptProxyIdentity — ObjectProxy preserves wrapped object equality
# ---------------------------------------------------------------------------

class TestWraptProxyIdentity:
    def test_list_wrapped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [[1, 2, 3]],
                "method": "__wrapped__",
                "expected": [1, 2, 3],
            },
        })
        assert ok, msg

    def test_bool_wrapped(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [False],
                "method": "__wrapped__",
                "expected": False,
            },
        })
        assert ok, msg

    def test_wrapped_is_same_object(self, wrapt_mod):
        """Verify ObjectProxy preserves object identity, not just equality."""
        x = [10, 20, 30]
        proxy = wrapt_mod.ObjectProxy(x)
        assert proxy.__wrapped__ is x

    def test_wrapped_string_identity(self, wrapt_mod):
        s = "identity-test"
        proxy = wrapt_mod.ObjectProxy(s)
        assert proxy.__wrapped__ is s

    def test_wrong_wrapped_fails(self, registry):
        ok, _msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "ObjectProxy",
                "args": [[1, 2, 3]],
                "method": "__wrapped__",
                "expected": [4, 5, 6],
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# TestWraptAll — all 12 wrapt invariants must pass
# ---------------------------------------------------------------------------

class TestWraptAll:
    def test_all_pass(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod)
        assert len(results) == 12

    def test_no_skips(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod, filter_category="version")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_object_proxy_category(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod, filter_category="object_proxy")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_proxy_class_category(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod, filter_category="proxy_class")
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_filter_by_attributes_category(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod, filter_category="attributes")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_proxy_identity_category(self, wrapt_spec, wrapt_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(wrapt_spec, wrapt_mod, filter_category="proxy_identity")
        assert len(results) == 2
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# TestWraptCLI — end-to-end CLI tests
# ---------------------------------------------------------------------------

class TestWraptCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(WRAPT_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(WRAPT_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "12 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(WRAPT_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "wrapt.version" in out
        assert "wrapt.object_proxy" in out

    def test_filter_flag(self, capsys):
        vb.main([str(WRAPT_SPEC_PATH), "--filter", "object_proxy", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(WRAPT_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 12
        assert all(r["passed"] for r in data)
