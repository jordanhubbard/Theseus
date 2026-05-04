"""
Tests for theseus/synthesis/prompt.py — PromptBuilder and extract_source_files.
"""
from __future__ import annotations

import pytest

from theseus.synthesis.prompt import PromptBuilder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_spec(
    canonical_name: str = "testlib",
    backend: str = "python_module",
    invariants: list | None = None,
    derived_from: list | None = None,
    functions: dict | None = None,
) -> dict:
    return {
        "identity": {"canonical_name": canonical_name},
        "library": {"backend": backend, "module_name": canonical_name},
        "provenance": {
            "derived_from": derived_from or ["Test docs — https://example.com"],
            "not_derived_from": ["testlib source code"],
            "notes": ["This is a test spec."],
        },
        "functions": functions or {"do_thing": {"params": [{"name": "x", "type": "int"}], "returns": "int"}},
        "constants": {"CONST_A": 1, "CONST_B": 2},
        "wire_formats": {},
        "error_model": {},
        "invariants": invariants or [
            {
                "id": "testlib.call.one",
                "kind": "python_call_eq",
                "description": "do_thing(1) == 2",
                "spec": {"function": "do_thing", "args": [1], "expected": 2},
                "category": "basic",
            },
            {
                "id": "testlib.call.two",
                "kind": "python_call_eq",
                "description": "do_thing(0) == 0",
                "spec": {"function": "do_thing", "args": [0], "expected": 0},
                "category": "edge",
            },
        ],
    }


@pytest.fixture
def builder() -> PromptBuilder:
    return PromptBuilder()


@pytest.fixture
def spec() -> dict:
    return _make_spec()


# ---------------------------------------------------------------------------
# initial_prompt
# ---------------------------------------------------------------------------

class TestInitialPrompt:
    def test_returns_two_strings(self, builder: PromptBuilder, spec: dict) -> None:
        system, user = builder.initial_prompt(spec, "python")
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user, str) and len(user) > 0

    def test_contains_canonical_name(self, builder: PromptBuilder, spec: dict) -> None:
        system, user = builder.initial_prompt(spec, "python")
        assert "testlib" in user

    def test_system_prompt_has_clean_room_rule(self, builder: PromptBuilder, spec: dict) -> None:
        system, _ = builder.initial_prompt(spec, "python")
        assert "NOT seen" in system or "clean-room" in system.lower() or "NOT" in system

    def test_contains_all_invariant_ids(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "python")
        for inv in spec["invariants"]:
            assert inv["id"] in user

    def test_contains_provenance_derived_from(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "python")
        assert "Test docs" in user

    def test_python_deliverable_instructions(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "python")
        assert "testlib.py" in user
        assert "<file" in user

    def test_c_deliverable_instructions(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "c")
        assert ".c" in user and ".h" in user
        assert "shared library" in user

    def test_javascript_deliverable_instructions(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "javascript")
        assert "index.js" in user

    def test_invariant_count_mentioned(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "python")
        assert "2 total" in user or "2" in user

    def test_constants_included(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "python")
        assert "CONST_A" in user or "CONST_B" in user

    def test_not_derived_from_included(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.initial_prompt(spec, "python")
        assert "testlib source code" in user


# ---------------------------------------------------------------------------
# revision_prompt
# ---------------------------------------------------------------------------

class TestRevisionPrompt:
    def test_contains_failed_invariant_ids(self, builder: PromptBuilder, spec: dict) -> None:
        failed = [{"id": "testlib.call.one", "message": "got 3, expected 2"}]
        _, user = builder.revision_prompt(
            spec, "python",
            previous_source={"testlib.py": "def do_thing(x): return x * 3"},
            failed_invariants=failed,
            iteration=2,
        )
        assert "testlib.call.one" in user

    def test_contains_error_message(self, builder: PromptBuilder, spec: dict) -> None:
        failed = [{"id": "testlib.call.one", "message": "got 3, expected 2"}]
        _, user = builder.revision_prompt(
            spec, "python",
            previous_source={"testlib.py": "def do_thing(x): return x * 3"},
            failed_invariants=failed,
            iteration=2,
        )
        assert "got 3, expected 2" in user

    def test_contains_previous_source(self, builder: PromptBuilder, spec: dict) -> None:
        source = {"testlib.py": "def do_thing(x): return x * 3"}
        _, user = builder.revision_prompt(
            spec, "python",
            previous_source=source,
            failed_invariants=[{"id": "testlib.call.one", "message": "err"}],
            iteration=2,
        )
        assert "def do_thing" in user

    def test_iteration_number_mentioned(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.revision_prompt(
            spec, "python",
            previous_source={},
            failed_invariants=[{"id": "testlib.call.one", "message": "err"}],
            iteration=3,
        )
        assert "3" in user

    def test_passing_count_mentioned(self, builder: PromptBuilder, spec: dict) -> None:
        # 2 total invariants, 1 failing → 1 passing
        _, user = builder.revision_prompt(
            spec, "python",
            previous_source={},
            failed_invariants=[{"id": "testlib.call.one", "message": "err"}],
            iteration=2,
        )
        assert "1" in user  # at least the passing count

    def test_file_block_format_in_deliverable(self, builder: PromptBuilder, spec: dict) -> None:
        _, user = builder.revision_prompt(
            spec, "python",
            previous_source={},
            failed_invariants=[{"id": "testlib.call.one", "message": "err"}],
            iteration=2,
        )
        assert "<file" in user


# ---------------------------------------------------------------------------
# extract_source_files
# ---------------------------------------------------------------------------

class TestExtractSourceFiles:
    def test_single_file(self) -> None:
        response = (
            '<file name="foo.py"><content>\n'
            'def hello(): return "world"\n'
            "</content></file>"
        )
        result = PromptBuilder.extract_source_files(response)
        assert "foo.py" in result
        assert 'def hello()' in result["foo.py"]

    def test_multiple_files(self) -> None:
        response = (
            '<file name="foo.py"><content>\nx = 1\n</content></file>\n'
            '<file name="bar.py"><content>\ny = 2\n</content></file>'
        )
        result = PromptBuilder.extract_source_files(response)
        assert set(result.keys()) == {"foo.py", "bar.py"}

    def test_raises_on_empty_response(self) -> None:
        with pytest.raises(ValueError, match="No <file"):
            PromptBuilder.extract_source_files("Here is some text with no file blocks.")

    def test_raises_on_blank_response(self) -> None:
        with pytest.raises(ValueError):
            PromptBuilder.extract_source_files("")

    def test_strips_leading_trailing_newlines_in_content(self) -> None:
        response = '<file name="x.py"><content>\n\ndef f(): pass\n\n</content></file>'
        result = PromptBuilder.extract_source_files(response)
        assert result["x.py"] == "def f(): pass"

    def test_single_quotes_in_name(self) -> None:
        response = "<file name='hello.c'><content>\nint x;\n</content></file>"
        result = PromptBuilder.extract_source_files(response)
        assert "hello.c" in result

    def test_content_with_angle_brackets(self) -> None:
        response = (
            '<file name="a.py"><content>\n'
            'x = "<not a tag>"\n'
            "</content></file>"
        )
        result = PromptBuilder.extract_source_files(response)
        assert "<not a tag>" in result["a.py"]
