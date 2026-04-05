"""
Tests for the decorator Z-layer behavioral spec (decorator.zspec.zsdl).

Covers:
  - SpecLoader: loading decorator spec via python_module backend
  - python_call_eq handler with decorator-specific patterns
  - InvariantRunner integration: all 12 invariants pass
  - CLI: verify-behavior runs decorator.zspec.json end-to-end

Categories verified:
  version (2)        — isgeneratorfunction/iscoroutinefunction(None) return False
  function_maker (4) — FunctionMaker.create produces correctly named functions; __qualname__ matches
  dispatch (1)       — dispatch_on is a plain function (not a generator)
  identity (1)       — FunctionMaker.create result has correct __name__
  exceptions (4)     — isgeneratorfunction/iscoroutinefunction handle non-callable args defensively
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import verify_behavior as vb

DECORATOR_SPEC_PATH = REPO_ROOT / "_build" / "zspecs" / "decorator.zspec.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def decorator_spec():
    return vb.SpecLoader().load(DECORATOR_SPEC_PATH)


@pytest.fixture(scope="module")
def decorator_mod(decorator_spec):
    return vb.LibraryLoader().load(decorator_spec["library"])


@pytest.fixture(scope="module")
def constants_map(decorator_spec):
    return vb.InvariantRunner().build_constants_map(decorator_spec["constants"])


@pytest.fixture(scope="module")
def registry(decorator_mod, constants_map):
    return vb.PatternRegistry(decorator_mod, constants_map)


# ---------------------------------------------------------------------------
# SpecLoader / module loader
# ---------------------------------------------------------------------------

class TestDecoratorSpecLoader:
    def test_loads_decorator_spec(self, decorator_spec):
        assert isinstance(decorator_spec, dict)

    def test_all_required_sections_present(self, decorator_spec):
        for section in vb.REQUIRED_SECTIONS:
            assert section in decorator_spec, f"Missing section: {section}"

    def test_backend_is_python_module(self, decorator_spec):
        assert decorator_spec["library"]["backend"] == "python_module"

    def test_module_name_is_decorator(self, decorator_spec):
        assert decorator_spec["library"]["module_name"] == "decorator"

    def test_loads_decorator_module(self, decorator_mod):
        import decorator
        assert decorator_mod is decorator

    def test_all_invariant_kinds_known(self, decorator_spec):
        for inv in decorator_spec["invariants"]:
            assert inv["kind"] in vb.KNOWN_KINDS, \
                f"Unknown kind {inv['kind']!r} in invariant {inv['id']}"

    def test_all_invariant_ids_unique(self, decorator_spec):
        ids = [inv["id"] for inv in decorator_spec["invariants"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# version — isgeneratorfunction / iscoroutinefunction return False for None
# ---------------------------------------------------------------------------

class TestDecoratorVersion:
    def test_isgeneratorfunction_none_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "isgeneratorfunction",
                "args": [None],
                "expected": False,
            },
        })
        assert ok, msg

    def test_iscoroutinefunction_none_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "iscoroutinefunction",
                "args": [None],
                "expected": False,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_expected(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "isgeneratorfunction",
                "args": [None],
                "expected": True,
            },
        })
        assert not ok

    def test_decorator_module_is_importable(self, decorator_mod):
        import decorator
        assert decorator_mod is decorator

    def test_version_is_string(self, decorator_mod):
        assert isinstance(decorator_mod.__version__, str)

    def test_version_starts_with_digit(self, decorator_mod):
        assert decorator_mod.__version__[0].isdigit()


# ---------------------------------------------------------------------------
# function_maker — FunctionMaker.create produces correctly named functions
# ---------------------------------------------------------------------------

class TestDecoratorFunctionMaker:
    def test_create_simple_sig_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionMaker.create",
                "args": ["foo(x)", "return x", {}],
                "method": "__name__",
                "expected": "foo",
            },
        })
        assert ok, msg

    def test_create_two_arg_sig_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionMaker.create",
                "args": ["bar(a, b)", "return a+b", {}],
                "method": "__name__",
                "expected": "bar",
            },
        })
        assert ok, msg

    def test_create_no_arg_sig_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionMaker.create",
                "args": ["baz()", "pass", {}],
                "method": "__name__",
                "expected": "baz",
            },
        })
        assert ok, msg

    def test_create_qualname_matches_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionMaker.create",
                "args": ["f(x)", "return x", {}],
                "method": "__qualname__",
                "expected": "f",
            },
        })
        assert ok, msg

    def test_create_wrong_name_fails(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionMaker.create",
                "args": ["foo(x)", "return x", {}],
                "method": "__name__",
                "expected": "not_foo",
            },
        })
        assert not ok

    def test_functionmaker_class_exists(self, decorator_mod):
        assert hasattr(decorator_mod, "FunctionMaker")
        assert isinstance(decorator_mod.FunctionMaker, type)

    def test_functionmaker_name_attr(self, decorator_mod):
        assert decorator_mod.FunctionMaker.__name__ == "FunctionMaker"

    def test_functionmaker_module_attr(self, decorator_mod):
        assert decorator_mod.FunctionMaker.__module__ == "decorator"


# ---------------------------------------------------------------------------
# dispatch — dispatch_on is a plain function (not a generator)
# ---------------------------------------------------------------------------

class TestDecoratorDispatch:
    def test_dispatch_on_not_generator(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "isgeneratorfunction",
                "args": ["dispatch_on"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_dispatch_on_is_callable(self, decorator_mod):
        assert callable(decorator_mod.dispatch_on)

    def test_dispatch_on_module_is_decorator(self, decorator_mod):
        assert decorator_mod.dispatch_on.__module__ == "decorator"

    def test_dispatch_on_name_attr(self, decorator_mod):
        assert decorator_mod.dispatch_on.__name__ == "dispatch_on"


# ---------------------------------------------------------------------------
# identity — core public callables belong to the decorator module
# ---------------------------------------------------------------------------

class TestDecoratorIdentity:
    def test_create_result_has_correct_name(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "FunctionMaker.create",
                "args": ["add(a, b)", "return a+b", {}],
                "method": "__name__",
                "expected": "add",
            },
        })
        assert ok, msg

    def test_decorate_callable(self, decorator_mod):
        assert callable(decorator_mod.decorate)

    def test_decorate_module_is_decorator(self, decorator_mod):
        assert decorator_mod.decorate.__module__ == "decorator"

    def test_decorator_fn_callable(self, decorator_mod):
        assert callable(decorator_mod.decorator)

    def test_decorator_fn_module(self, decorator_mod):
        assert decorator_mod.decorator.__module__ == "decorator"

    def test_contextmanager_callable(self, decorator_mod):
        assert callable(decorator_mod.contextmanager)

    def test_contextmanager_module(self, decorator_mod):
        assert decorator_mod.contextmanager.__module__ == "decorator"


# ---------------------------------------------------------------------------
# exceptions — isgeneratorfunction/iscoroutinefunction handle non-callable args
# ---------------------------------------------------------------------------

class TestDecoratorExceptions:
    def test_isgeneratorfunction_string_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "isgeneratorfunction",
                "args": ["hello"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_iscoroutinefunction_string_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "iscoroutinefunction",
                "args": ["hello"],
                "expected": False,
            },
        })
        assert ok, msg

    def test_isgeneratorfunction_int_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "isgeneratorfunction",
                "args": [42],
                "expected": False,
            },
        })
        assert ok, msg

    def test_iscoroutinefunction_int_is_false(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "iscoroutinefunction",
                "args": [42],
                "expected": False,
            },
        })
        assert ok, msg

    def test_fails_on_wrong_value(self, registry):
        ok, msg = registry.run({
            "kind": "python_call_eq",
            "spec": {
                "function": "isgeneratorfunction",
                "args": ["hello"],
                "expected": True,
            },
        })
        assert not ok


# ---------------------------------------------------------------------------
# InvariantRunner integration — all 12 decorator invariants must pass
# ---------------------------------------------------------------------------

class TestDecoratorAll:
    def test_all_pass(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod)
        failed = [r for r in results if not r.passed]
        assert not failed, f"Failed invariants: {[r.inv_id for r in failed]}"

    def test_invariant_count(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod)
        assert len(results) == 12

    def test_no_skips(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod)
        skipped = [r for r in results if r.skip_reason]
        assert not skipped

    def test_filter_by_version_category(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod, filter_category="version")
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_filter_by_function_maker_category(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod, filter_category="function_maker")
        assert len(results) == 4
        assert all(r.passed for r in results)

    def test_filter_by_dispatch_category(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod, filter_category="dispatch")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_identity_category(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod, filter_category="identity")
        assert len(results) == 1
        assert all(r.passed for r in results)

    def test_filter_by_exceptions_category(self, decorator_spec, decorator_mod):
        runner = vb.InvariantRunner()
        results = runner.run_all(decorator_spec, decorator_mod, filter_category="exceptions")
        assert len(results) == 4
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestDecoratorCLI:
    def test_exit_code_0_all_pass(self):
        rc = vb.main([str(DECORATOR_SPEC_PATH)])
        assert rc == 0

    def test_verbose_flag_shows_all(self, capsys):
        vb.main([str(DECORATOR_SPEC_PATH), "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "12 invariants" in out

    def test_list_flag(self, capsys):
        rc = vb.main([str(DECORATOR_SPEC_PATH), "--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "decorator.api" in out
        assert "decorator.function_maker" in out

    def test_filter_flag(self, capsys):
        vb.main([str(DECORATOR_SPEC_PATH), "--filter", "function_maker", "--verbose"])
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_json_out(self, tmp_path):
        import json
        out_file = tmp_path / "results.json"
        vb.main([str(DECORATOR_SPEC_PATH), "--json-out", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 12
        assert all(r["passed"] for r in data)
