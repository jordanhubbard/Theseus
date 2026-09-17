"""JSON gold-set format spike: public-API oracle, held-out guard, no wrappers."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

import cleanroom_verify as cv
import held_out_guard
import zsdl_compile
from theseus.synthesis.prompt import PromptBuilder

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_MD = ROOT / "gold" / "json" / "package.md"
PUBLIC_ZSDL = ROOT / "zspecs" / "theseus_json.zspec.zsdl"
LAYER2_ZSDL = ROOT / "zspecs" / "json.zspec.zsdl"
HELD_OUT_ZSDL = ROOT / "gold" / "json" / "held_out.zspec.zsdl"
IMPL = ROOT / "cleanroom" / "python" / "theseus_json" / "__init__.py"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "package.md must begin with YAML frontmatter"
    _, rest = text.split("---\n", 1)
    body = rest.split("\n---\n", 1)
    assert len(body) == 2, "package.md frontmatter must be closed with ---"
    return yaml.safe_load(body[0])


def _write_compiled(tmp_path: Path, zsdl: Path, name: str = "spec.zspec.json") -> Path:
    compiled = zsdl_compile.ZSDLCompiler().compile_file(zsdl)
    path = tmp_path / name
    path.write_text(json.dumps(compiled), encoding="utf-8")
    return path


def test_package_md_declares_three_artifacts():
    meta = _frontmatter(PACKAGE_MD)
    assert meta["family"] == "json"
    assert meta["public_oracle"] == "zspecs/json.zspec.zsdl"
    assert meta["cleanroom_oracle"] == "zspecs/theseus_json.zspec.zsdl"
    assert meta["held_out_oracle"] == "gold/json/held_out.zspec.zsdl"
    assert meta["implementation"] == "cleanroom/python/theseus_json"
    assert meta["blocks"] == "json"
    assert set(meta["exports"]) >= {"dumps", "loads", "JSONDecodeError"}
    assert meta["qualification"] == "none"
    for rel in (
        meta["public_oracle"],
        meta["cleanroom_oracle"],
        meta["held_out_oracle"],
        meta["implementation"] + "/__init__.py",
    ):
        assert (ROOT / rel).exists(), rel


def test_implementation_exports_public_api_not_wrappers():
    text = IMPL.read_text(encoding="utf-8")
    assert "def dumps(" in text
    assert "def loads(" in text
    assert "class JSONDecodeError" in text
    assert "def json_loads_int" not in text
    assert "def json_dumps_has_key" not in text
    assert "def json_round_trip" not in text


def test_cleanroom_spec_calls_dumps_loads_with_arguments():
    compiled = zsdl_compile.ZSDLCompiler().compile_file(PUBLIC_ZSDL)
    assert compiled["backend_lang"] == "python_cleanroom"
    assert compiled.get("blocks") == "json"
    fns = {inv["spec"]["function"] for inv in compiled["invariants"]}
    assert fns == {"dumps", "loads"}
    assert any(inv["spec"].get("args") for inv in compiled["invariants"])
    assert any(inv["kind"] == "python_call_raises" for inv in compiled["invariants"])
    assert not any(
        (inv["spec"].get("args") in ([], None))
        and inv["kind"] == "python_call_eq"
        for inv in compiled["invariants"]
    )
    compact = next(
        inv for inv in compiled["invariants"] if inv["id"].endswith("compact_separators")
    )
    sep = compact["spec"]["kwargs"]["separators"]
    assert sep == {"type": "tuple", "value": [",", ":"]}
    assert cv._resolve_typed(sep) == (",", ":")


def test_held_out_is_outside_zspecs_and_disjoint():
    assert HELD_OUT_ZSDL.parent != ROOT / "zspecs"
    assert not (ROOT / "zspecs" / "held_out.zspec.zsdl").exists()
    public = zsdl_compile.ZSDLCompiler().compile_file(PUBLIC_ZSDL)
    held = zsdl_compile.ZSDLCompiler().compile_file(HELD_OUT_ZSDL)
    public_ids = {inv["id"] for inv in public["invariants"]}
    held_ids = {inv["id"] for inv in held["invariants"]}
    assert public_ids.isdisjoint(held_ids)
    public_args = {
        json.dumps(inv["spec"].get("args"), sort_keys=True, default=str)
        for inv in public["invariants"]
    }
    held_args = {
        json.dumps(inv["spec"].get("args"), sort_keys=True, default=str)
        for inv in held["invariants"]
    }
    assert public_args.isdisjoint(held_args)


def test_public_oracle_passes_in_isolation(tmp_path):
    path = _write_compiled(tmp_path, PUBLIC_ZSDL, "theseus_json.zspec.json")
    result = cv.verify(str(path))
    assert result.get("fail", 1) == 0, result.get("errors")
    assert result.get("pass", 0) >= 16


def test_held_out_oracle_passes_in_isolation(tmp_path):
    path = _write_compiled(tmp_path, HELD_OUT_ZSDL, "held_out.zspec.json")
    result = cv.verify(str(path))
    assert result.get("fail", 1) == 0, result.get("errors")
    assert result.get("pass", 0) >= 8


def test_held_out_guard_rejects_leaks_and_passes_public_prompt():
    assert held_out_guard.check(PUBLIC_ZSDL, HELD_OUT_ZSDL) == []
    public = zsdl_compile.ZSDLCompiler().compile_file(PUBLIC_ZSDL)
    held = zsdl_compile.ZSDLCompiler().compile_file(HELD_OUT_ZSDL)
    leaked = json.loads(json.dumps(public))
    leaked["invariants"].append(
        {
            "id": "leak",
            "kind": "python_call_eq",
            "spec": {"function": "loads", "args": ["1.5e2"], "expected": 150.0},
        }
    )
    prompt = PromptBuilder().initial_prompt(leaked, "python_cleanroom")[1]
    assert "1.5e2" in prompt
    tokens = held_out_guard.distinctive_tokens(held, public)
    assert "1.5e2" in tokens
    assert "loads" not in tokens
    assert "JSONDecodeError" not in tokens
    assert held_out_guard.leaked_tokens(prompt, tokens)


def test_layer2_json_oracle_still_exists():
    compiled = zsdl_compile.ZSDLCompiler().compile_file(LAYER2_ZSDL)
    assert compiled["library"]["backend"] == "python_module"
    assert compiled["library"]["module_name"] == "json"
    assert len(compiled["invariants"]) >= 16


def test_resolve_typed_nested_tuple():
    assert cv._resolve_typed({"type": "tuple", "value": [",", ":"]}) == (",", ":")
    assert cv._resolve_typed([{"type": "null", "value": None}]) == [None]
    assert cv._resolve_typed({"a": {"type": "tuple", "value": [1, 2]}}) == {"a": (1, 2)}


def test_cleanroom_verify_kwargs_and_raises(tmp_path, monkeypatch):
    root = tmp_path / "python"
    impl = root / "theseus_sample"
    impl.mkdir(parents=True)
    (impl / "__init__.py").write_text(
        "class Boom(ValueError):\n    pass\n"
        "def dumps(obj, separators=None):\n"
        "    item_sep = ', ' if separators is None else separators[0]\n"
        "    return '[' + item_sep.join(str(x) for x in obj) + ']'\n"
        "def bad(x):\n"
        "    raise Boom('no')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cv, "_CLEANROOM_PYTHON", root)
    spec = {
        "identity": {"canonical_name": "theseus_sample"},
        "backend_lang": "python_cleanroom",
        "blocks": "not_a_real_blocked_mod_xyz",
        "invariants": [
            {
                "id": "eq",
                "kind": "python_call_eq",
                "spec": {
                    "function": "dumps",
                    "args": [[1, 2, 3]],
                    "kwargs": {"separators": {"type": "tuple", "value": [",", ":"]}},
                    "expected": "[1,2,3]",
                },
            },
            {
                "id": "raises",
                "kind": "python_call_raises",
                "spec": {
                    "function": "bad",
                    "args": [1],
                    "expected_exception": "Boom",
                },
            },
        ],
    }
    path = tmp_path / "sample.zspec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    result = cv.verify(str(path))
    assert result["fail"] == 0, result.get("errors")
    assert result["pass"] == 2
    script = cv._python_invariant_script("theseus_sample", spec["invariants"][0])
    assert "import json" not in script
    assert "separators" in script
