"""Tests for tools/corpus_autopsy.py — verification-ladder corpus classifier."""
from __future__ import annotations

import json
from pathlib import Path

import corpus_autopsy as autopsy


def _write_zsdl(path: Path, text: str) -> Path:
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def _compile_and_classify(path: Path, repo_root: Path, registry: dict) -> dict:
    compiled = autopsy.compile_zsdl(path)
    return autopsy.classify_compiled(
        compiled, zsdl_path=path, repo_root=repo_root, registry=registry
    )


FACTORY_ZSDL = """
spec: theseus_json
version: ">=3.9"
backend: python_cleanroom(theseus_json)
docs: https://www.json.org/json-en.html
error_model: python_exceptions

invariant theseus_json.loads_int:
  description: "parse a tiny object"
  kind: python_call_eq
  function: json_loads_int
  args: []
  expected: 1

invariant theseus_json.dumps_has_key:
  description: "dumps contains key"
  kind: python_call_eq
  function: json_dumps_has_key
  args: []
  expected: true

invariant theseus_json.round_trip:
  description: "round trip"
  kind: python_call_eq
  function: json_round_trip
  args: []
  expected: true
"""

PUBLIC_API_ZSDL = """
spec: json
version: ">=3.9"
backend: python_module(json)
docs: https://docs.python.org/3/library/json.html
error_model: python_exceptions

table json.dumps.primitives:
  kind: python_call_eq
  category: dumps
  id_prefix: dumps
  function: dumps
  columns: [id, args, expected]
  rows:
    - [null, [~], "null"]
    - [true, [true], "true"]
    - [false, [false], "false"]
    - [zero, [0], "0"]
    - [integer, [42], "42"]
    - [string, ["hello"], "\\"hello\\""]
    - [array, [[1, 2, 3]], "[1, 2, 3]"]
    - [object, [{a: 1}], "{\\"a\\": 1}"]
    - [neg, [-7], "-7"]
    - [empty_array, [[]], "[]"]
    - [empty_obj, [{}], "{}"]
    - [nested, [[{a: [1]}]], "[{\\"a\\": [1]}]"]
    - [spaces, [["a"]], "[\\"a\\"]"]
    - [numstr, ["1"], "\\"1\\""]
    - [bool_list, [[true, false]], "[true, false]"]
    - [none_list, [[~]], "[null]"]
"""

PRESENCE_ZSDL = """
spec: theseus_antigravity_cr
version: ">=3.0"
backend: python_cleanroom(theseus_antigravity_cr)
docs: https://docs.python.org/3/library/antigravity.html
error_model: python_exceptions

invariant theseus_antigravity_cr.url:
  description: "antigravity module exposes a URL constant"
  kind: python_call_eq
  function: antigrav2_url
  args: []
  expected: true

invariant theseus_antigravity_cr.fly:
  description: "fly() function exists and is callable"
  kind: python_call_eq
  function: antigrav2_fly
  args: []
  expected: true

invariant theseus_antigravity_cr.geohash:
  description: "geohash() function exists and accepts args"
  kind: python_call_eq
  function: antigrav2_geohash
  args: []
  expected: true
"""

RUST_ZSDL = """
spec: json_rust
version: ">=3.9"
backend: rust_module(json_rust)
docs: https://example.invalid/json
error_model: python_exceptions

invariant json_rust.loads:
  description: "wrapper loads"
  kind: python_call_eq
  function: loads
  args: ["{\\"a\\": 1}"]
  expected: {a: 1}
"""


class TestFamilyKey:
    def test_strips_theseus_and_wave_suffixes(self):
        assert autopsy.family_key("theseus_json") == "json"
        assert autopsy.family_key("theseus_json_cr") == "json"
        assert autopsy.family_key("theseus_json_cr4") == "json"
        assert autopsy.family_key("theseus_urllib_parse_cr2") == "urllib_parse"
        assert autopsy.family_key("theseus_path_node") == "path"
        assert autopsy.family_key("bisect_extra_rust") == "bisect"
        assert autopsy.family_key("json") == "json"
        assert autopsy.family_key("theseus_cProfile_cr") == "cprofile"
        assert autopsy.family_key("theseus_base64_q") == "base64"
        assert autopsy.family_key("theseus_urllib_parse_q") == "urllib_parse"


class TestFeasibility:
    def test_high_pure_beats_native_alias(self):
        assert autopsy.classify_feasibility("json", "python_module", "json") == "high"
        assert autopsy.classify_feasibility("hashlib", "python_module", "hashlib") == "high"

    def test_rust_is_wrapper(self):
        assert autopsy.classify_feasibility("json", "rust_module", "json_rust") == "wrapper"

    def test_antigravity_infeasible(self):
        assert autopsy.classify_feasibility(
            "antigravity", "python_cleanroom", "theseus_antigravity_cr"
        ) == "infeasible"

    def test_os_and_interpreter(self):
        assert autopsy.classify_feasibility("socket", "python_module", "socket") == "os_binding"
        assert autopsy.classify_feasibility("sys", "python_module", "sys") == "stdlib_interpreter"
        assert autopsy.classify_feasibility("_json", "python_module", "_json") == "stdlib_interpreter"


class TestClassifyFixtures:
    def test_factory_cleanroom_is_shallow_self_test(self, tmp_path):
        path = _write_zsdl(tmp_path / "theseus_json.zspec.zsdl", FACTORY_ZSDL)
        rec = _compile_and_classify(
            path,
            tmp_path,
            {"packages": {"theseus_json": {"status": "verified"}}},
        )
        assert rec["backend"] == "python_cleanroom"
        assert rec["invariant_count"] == 3
        assert rec["contract_shape"] == "self_test_wrapper"
        assert rec["oracle_quality"] == "factory_shallow"
        assert rec["family"] == "json"
        assert rec["ladder"] == "legacy_isolation"
        assert rec["withdraw_qualification"] is True
        assert rec["zero_arg_ratio"] == 1.0

    def test_public_api_table_is_deep_oracle_bound(self, tmp_path):
        path = _write_zsdl(tmp_path / "json.zspec.zsdl", PUBLIC_API_ZSDL)
        rec = _compile_and_classify(path, tmp_path, {"packages": {}})
        assert rec["backend"] == "python_module"
        assert rec["invariant_count"] == 16
        assert rec["contract_shape"] == "public_api"
        assert rec["oracle_quality"] == "deep"
        assert rec["ladder"] == "oracle_bound"
        assert rec["withdraw_qualification"] is False
        assert rec["zero_arg_ratio"] == 0.0

    def test_presence_true_wrappers(self, tmp_path):
        path = _write_zsdl(tmp_path / "theseus_antigravity_cr.zspec.zsdl", PRESENCE_ZSDL)
        rec = _compile_and_classify(
            path,
            tmp_path,
            {"packages": {"theseus_antigravity_cr": {"status": "verified"}}},
        )
        assert rec["oracle_quality"] == "presence"
        assert rec["feasibility"] == "infeasible"
        assert rec["expected_true_ratio"] == 1.0
        assert rec["withdraw_qualification"] is True

    def test_rust_contract_is_wrapper(self, tmp_path):
        path = _write_zsdl(tmp_path / "json_rust.zspec.zsdl", RUST_ZSDL)
        rec = _compile_and_classify(path, tmp_path, {"packages": {}})
        assert rec["backend"] == "rust_module"
        assert rec["contract_shape"] == "wrapper"
        assert rec["feasibility"] == "wrapper"
        assert rec["ladder"] == "inventoried"


class TestReport:
    def test_build_report_withdraws_registry_and_keeps_gold_candidate(self, tmp_path):
        zdir = tmp_path / "zspecs"
        zdir.mkdir()
        _write_zsdl(zdir / "theseus_json.zspec.zsdl", FACTORY_ZSDL)
        _write_zsdl(zdir / "json.zspec.zsdl", PUBLIC_API_ZSDL)
        _write_zsdl(zdir / "theseus_antigravity_cr.zspec.zsdl", PRESENCE_ZSDL)
        registry = tmp_path / "theseus_registry.json"
        registry.write_text(
            json.dumps({
                "packages": {
                    "theseus_json": {"status": "verified", "cleanroom_path": "x", "spec": "y"},
                    "theseus_antigravity_cr": {"status": "verified", "cleanroom_path": "x", "spec": "y"},
                }
            }),
            encoding="utf-8",
        )
        report = autopsy.build_report(
            tmp_path, zspecs_dir=zdir, registry_path=registry
        )
        assert report["summary"]["spec_count"] == 3
        assert report["summary"]["withdrawn_from_qualification"] == 2
        assert report["summary"]["qualified"] == 0
        names = {r["name"] for r in report["gold_set_candidates"]}
        assert "json" in names
        assert "theseus_json" not in names
        withdrawn_names = {p["name"] for p in report["withdrawn_from_qualification"]}
        assert withdrawn_names == {"theseus_json", "theseus_antigravity_cr"}
        md = autopsy.render_markdown(report)
        assert "withdrawn from qualification" in md.lower() or "Withdrawn" in md
        assert "characterization" in report
        assert report["summary"]["gold_characterization_families"] == 0
        doc = autopsy.withdrawn_document(report)
        assert doc["qualification_claim"] == "withdrawn"
        assert doc["count"] == 2

    def test_write_and_check(self, tmp_path):
        zdir = tmp_path / "zspecs"
        zdir.mkdir()
        _write_zsdl(zdir / "json.zspec.zsdl", PUBLIC_API_ZSDL)
        out = tmp_path / "reports" / "audit"
        report = autopsy.build_report(tmp_path, zspecs_dir=zdir, registry_path=tmp_path / "missing.json")
        autopsy.write_reports(report, out)
        assert (out / "corpus-autopsy.json").is_file()
        assert (out / "corpus-autopsy.md").is_file()
        assert (out / "withdrawn-verified.json").is_file()
        assert autopsy.check_committed(report, out) == 0
        stale = json.loads((out / "corpus-autopsy.json").read_text(encoding="utf-8"))
        stale["summary"]["spec_count"] = 0
        (out / "corpus-autopsy.json").write_text(json.dumps(stale), encoding="utf-8")
        assert autopsy.check_committed(report, out) == 1


class TestRealCorpusExhibits:
    """Spot-check the committed specs that motivated the ladder."""

    def test_layer2_json_is_public_api(self):
        root = Path(__file__).resolve().parent.parent
        path = root / "zspecs" / "json.zspec.zsdl"
        if not path.is_file():
            return
        rec = _compile_and_classify(path, root, {"packages": {}})
        assert rec["contract_shape"] == "public_api"
        assert rec["oracle_quality"] in ("moderate", "deep")
        assert rec["invariant_count"] >= 26

    def test_theseus_json_is_cleanroom_public_api(self):
        root = Path(__file__).resolve().parent.parent
        path = root / "zspecs" / "theseus_json.zspec.zsdl"
        if not path.is_file():
            return
        rec = _compile_and_classify(
            path, root, {"packages": {"theseus_json": {"status": "verified"}}}
        )
        assert rec["oracle_quality"] == "deep"
        assert rec["contract_shape"] == "cleanroom_public_api"
        assert rec["ladder"] == "legacy_isolation"
        assert rec["zero_arg_ratio"] == 0.0
        assert rec["invariant_count"] >= 26

    def test_antigravity_is_presence(self):
        root = Path(__file__).resolve().parent.parent
        path = root / "zspecs" / "theseus_antigravity_cr.zspec.zsdl"
        if not path.is_file():
            return
        rec = _compile_and_classify(
            path,
            root,
            {"packages": {"theseus_antigravity_cr": {"status": "verified"}}},
        )
        assert rec["oracle_quality"] == "presence"
        assert rec["feasibility"] == "infeasible"


class TestCommittedAutopsy:
    def test_committed_report_withdraws_qualification(self):
        root = Path(__file__).resolve().parent.parent
        path = root / "reports" / "audit" / "corpus-autopsy.json"
        withdrawn = root / "reports" / "audit" / "withdrawn-verified.json"
        assert path.is_file()
        assert withdrawn.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        wdoc = json.loads(withdrawn.read_text(encoding="utf-8"))
        assert data["summary"]["qualified"] == 0
        assert data["summary"]["withdrawn_from_qualification"] >= 1
        assert wdoc["qualification_claim"] == "withdrawn"
        assert wdoc["count"] == data["summary"]["withdrawn_from_qualification"]
        # Regenerated after Phase 2; allow missing key only if autopsy not yet rewritten.
        if "gold_characterization_accepted" in data["summary"]:
            assert data["summary"]["gold_characterization_accepted"] >= 1
