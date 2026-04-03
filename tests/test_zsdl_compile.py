"""
Tests for tools/zsdl_compile.py — ZSDL → JSON compiler.

Unit tests cover:
  - Custom YAML tag loading (!b64, !hex, !ascii, !tuple)
  - _resolve() value conversion
  - parse_call_expr() for all chain depths and forms
  - Backend string parsing
  - Constants/functions/error_model section compilation
  - Table compilation (id_prefix, id_from, overrides, describe template)
  - Single invariant block compilation (call-expr form and structured form)
  - Error cases (missing kind, bad chain depth, column mismatch)

Integration tests compile all three ZSDL specs (zstd, difflib, urllib_parse)
and verify the compiled JSON passes the behavioral harness.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import zsdl_compile as zc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_zsdl(text: str) -> dict:
    return yaml.load(text, Loader=zc._LOADER)


def _compile_text(text: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".zspec.zsdl", mode="w",
                                     encoding="utf-8", delete=False) as f:
        f.write(text)
        path = Path(f.name)
    try:
        return zc.ZSDLCompiler().compile_file(path)
    finally:
        path.unlink(missing_ok=True)


def _minimal_header(extra: str = "") -> str:
    return f"spec: mylib\nversion: '>=1.0'\nbackend: python_module(mylib)\n{extra}"


# ---------------------------------------------------------------------------
# YAML tags
# ---------------------------------------------------------------------------

class TestYAMLTags:
    def test_b64_tag(self):
        doc = _load_zsdl("val: !b64 YWJj")
        assert isinstance(doc["val"], zc.B64Value)
        assert doc["val"].value == "YWJj"

    def test_hex_tag(self):
        doc = _load_zsdl("val: !hex deadbeef")
        assert isinstance(doc["val"], zc.HexValue)
        assert doc["val"].value == "deadbeef"

    def test_ascii_tag(self):
        doc = _load_zsdl("val: !ascii hello")
        assert isinstance(doc["val"], zc.AsciiValue)
        assert doc["val"].value == "hello"

    def test_tuple_tag(self):
        doc = _load_zsdl("val: !tuple [1, 2, 3]")
        assert isinstance(doc["val"], zc.TupleValue)
        assert doc["val"].value == [1, 2, 3]


# ---------------------------------------------------------------------------
# _resolve()
# ---------------------------------------------------------------------------

class TestResolve:
    def test_passthrough_str(self):
        assert zc._resolve("hello") == "hello"

    def test_passthrough_int(self):
        assert zc._resolve(42) == 42

    def test_passthrough_none(self):
        assert zc._resolve(None) is None

    def test_passthrough_list(self):
        assert zc._resolve([1, "a", None]) == [1, "a", None]

    def test_passthrough_dict(self):
        assert zc._resolve({"k": "v"}) == {"k": "v"}

    def test_b64(self):
        assert zc._resolve(zc.B64Value("YWJj")) == {"type": "bytes_b64", "value": "YWJj"}

    def test_hex(self):
        assert zc._resolve(zc.HexValue("ff")) == {"type": "bytes_hex", "value": "ff"}

    def test_ascii(self):
        assert zc._resolve(zc.AsciiValue("hi")) == {"type": "bytes_ascii", "value": "hi"}

    def test_tuple(self):
        assert zc._resolve(zc.TupleValue([1, 2])) == {"type": "tuple", "value": [1, 2]}

    def test_nested_list_with_tagged(self):
        result = zc._resolve([zc.B64Value("abc"), "plain"])
        assert result == [{"type": "bytes_b64", "value": "abc"}, "plain"]

    def test_nested_dict_with_tagged(self):
        result = zc._resolve({"data": zc.HexValue("ff")})
        assert result == {"data": {"type": "bytes_hex", "value": "ff"}}


# ---------------------------------------------------------------------------
# parse_call_expr()
# ---------------------------------------------------------------------------

class TestParseCallExpr:
    def test_simple_call(self):
        r = zc.parse_call_expr("unquote('%2Fpath')")
        assert r == {"function": "unquote", "args": ["%2Fpath"]}

    def test_call_no_args(self):
        r = zc.parse_call_expr("ratio()")
        assert r == {"function": "ratio", "args": []}

    def test_call_with_kwargs(self):
        r = zc.parse_call_expr("quote('/path', safe='/')")
        assert r["function"] == "quote"
        assert r["args"] == ["/path"]
        assert r["kwargs"] == {"safe": "/"}

    def test_chain_attr_access(self):
        r = zc.parse_call_expr("urlparse('https://example.com').scheme")
        assert r["function"] == "urlparse"
        assert r["args"] == ["https://example.com"]
        assert r["method"] == "scheme"
        assert "method_chain" not in r

    def test_chain_method_call_no_args(self):
        r = zc.parse_call_expr("SequenceMatcher(None, 'abc', 'xyz').ratio()")
        assert r["function"] == "SequenceMatcher"
        assert r["args"] == [None, "abc", "xyz"]
        assert r["method"] == "ratio"
        assert "method_args" not in r
        assert "method_chain" not in r

    def test_chain_method_with_args(self):
        r = zc.parse_call_expr("PurePosixPath('a.txt').with_suffix('.md')")
        assert r["function"] == "PurePosixPath"
        assert r["method"] == "with_suffix"
        assert r["method_args"] == [".md"]

    def test_double_chain_method_then_attr(self):
        r = zc.parse_call_expr(
            "SequenceMatcher(None, 'ABCDBDE', 'BCDE').find_longest_match().size"
        )
        assert r["function"] == "SequenceMatcher"
        assert r["method"] == "find_longest_match"
        assert "method_args" not in r
        assert r["method_chain"] == "size"

    def test_double_chain_attr_then_attr(self):
        r = zc.parse_call_expr("date.fromisoformat('2024-01-01').year")
        assert r["function"] == "date.fromisoformat"
        assert r["method"] == "year"

    def test_dict_arg(self):
        r = zc.parse_call_expr('urlencode({"a": "1", "b": "2"})')
        assert r["function"] == "urlencode"
        assert r["args"] == [{"a": "1", "b": "2"}]

    def test_null_arg(self):
        r = zc.parse_call_expr("SequenceMatcher(None, 'a', 'b').ratio()")
        assert r["args"][0] is None

    def test_negative_number(self):
        r = zc.parse_call_expr("some_fn(-1)")
        assert r["args"] == [-1]

    def test_list_arg(self):
        r = zc.parse_call_expr("get_close_matches('word', ['a', 'b'])")
        assert r["args"] == ["word", ["a", "b"]]

    def test_depth_exceeds_two_raises(self):
        with pytest.raises(ValueError, match="depth"):
            zc.parse_call_expr("fn(1).a().b().c")

    def test_bad_syntax_raises(self):
        with pytest.raises(ValueError):
            zc.parse_call_expr("not valid python !!!")


# ---------------------------------------------------------------------------
# Backend parsing
# ---------------------------------------------------------------------------

class TestBackendParsing:
    def _lib(self, backend_str: str, **extras) -> dict:
        doc = {"spec": "x", "version": ">=1", "backend": backend_str}
        doc.update(extras)
        return zc.ZSDLCompiler()._compile_library(doc)

    def test_python_module(self):
        lib = self._lib("python_module(hashlib)")
        assert lib["backend"] == "python_module"
        assert lib["module_name"] == "hashlib"
        assert lib["soname_patterns"] == []

    def test_python_module_dotted(self):
        lib = self._lib("python_module(urllib.parse)")
        assert lib["module_name"] == "urllib.parse"

    def test_ctypes(self):
        lib = self._lib("ctypes(zstd)")
        assert "backend" not in lib
        assert lib["soname_patterns"] == ["zstd"]

    def test_ctypes_with_version_function(self):
        lib = self._lib("ctypes(zstd)", version_function="ZSTD_versionString",
                        min_version_prefix="1.")
        assert lib["version_function"] == "ZSTD_versionString"
        assert lib["min_version_prefix"] == "1."

    def test_cli(self):
        lib = self._lib("cli(curl)")
        assert lib["backend"] == "cli"
        assert lib["command"] == "curl"
        assert lib["soname_patterns"] == []

    def test_node(self):
        lib = self._lib("node(semver)")
        assert lib["backend"] == "cli"
        assert lib["command"] == "node"
        assert lib["module_name"] == "semver"


# ---------------------------------------------------------------------------
# Constants compilation
# ---------------------------------------------------------------------------

class TestConstantsCompilation:
    def test_dict_of_dicts_becomes_array(self):
        raw = {
            "levels": {
                "LEVEL_1": {"value": 1, "description": "Fast"},
                "LEVEL_9": {"value": 9, "description": "Slow"},
            }
        }
        result = zc.ZSDLCompiler()._compile_constants(raw)
        assert "levels" in result
        arr = result["levels"]
        assert len(arr) == 2
        assert {"name": "LEVEL_1", "value": 1, "description": "Fast"} in arr
        assert {"name": "LEVEL_9", "value": 9, "description": "Slow"} in arr

    def test_empty_constants(self):
        assert zc.ZSDLCompiler()._compile_constants({}) == {}
        assert zc.ZSDLCompiler()._compile_constants(None) == {}


# ---------------------------------------------------------------------------
# Error model compilation
# ---------------------------------------------------------------------------

class TestErrorModelCompilation:
    def test_python_exceptions_shorthand(self):
        result = zc.ZSDLCompiler()._compile_error_model("python_exceptions")
        assert result["return_code_semantics"].startswith("Python exceptions")
        assert result["stream_error_field"] == "null"
        assert result["error_codes"] == []

    def test_full_error_model(self):
        raw = {
            "semantics": "Uses error codes",
            "stickiness": "Stateless",
            "stderr": "ZSTD_getErrorName(code)",
            "codes": {
                "ERR_OK": {"value": 0, "meaning": "Success"},
            }
        }
        result = zc.ZSDLCompiler()._compile_error_model(raw)
        assert result["return_code_semantics"] == "Uses error codes"
        assert result["stream_error_field"] == "ZSTD_getErrorName(code)"
        assert len(result["error_codes"]) == 1
        assert result["error_codes"][0]["name"] == "ERR_OK"

    def test_none_error_model(self):
        result = zc.ZSDLCompiler()._compile_error_model(None)
        assert result["error_codes"] == []


# ---------------------------------------------------------------------------
# Table compilation
# ---------------------------------------------------------------------------

class TestTableCompilation:
    def _compile_table(self, tbl_text: str, canonical: str = "mylib") -> list:
        doc = _load_zsdl(tbl_text)
        # The YAML key is the label
        label = next(iter(doc))
        return zc.ZSDLCompiler()._compile_table(label, doc[label], canonical)

    def test_basic_table(self):
        text = """
'table mylib.foo':
  kind: python_call_eq
  category: test
  function: myfn
  columns: [id, args, expected]
  rows:
    - [case_a, ["x"], "X"]
    - [case_b, ["y"], "Y"]
"""
        invs = self._compile_table(text)
        assert len(invs) == 2
        assert invs[0]["id"] == "mylib.case_a"
        assert invs[1]["id"] == "mylib.case_b"
        assert invs[0]["spec"]["function"] == "myfn"
        assert invs[0]["spec"]["expected"] == "X"

    def test_id_prefix(self):
        text = """
'table mylib.things':
  kind: python_call_eq
  id_prefix: sha256
  function: fn
  columns: [id, args, expected]
  rows:
    - [empty, [], ""]
"""
        invs = self._compile_table(text)
        assert invs[0]["id"] == "mylib.sha256.empty"

    def test_id_from(self):
        text = """
'table mylib.consts':
  kind: constant_eq
  id_prefix: constant
  id_from: name
  columns: [name, expected_value]
  rows:
    - [Z_OK, 0]
    - [Z_STREAM_END, 1]
"""
        invs = self._compile_table(text)
        assert invs[0]["id"] == "mylib.constant.Z_OK"
        assert invs[1]["id"] == "mylib.constant.Z_STREAM_END"
        assert invs[0]["spec"]["name"] == "Z_OK"

    def test_override_dict(self):
        text = """
'table mylib.q':
  kind: python_call_eq
  function: fn
  columns: [id, args, expected]
  rows:
    - [plain, ["a"], "A"]
    - [override_row, ["b"], "B", {category: "special"}]
"""
        invs = self._compile_table(text)
        assert "category" not in invs[0] or invs[0].get("category") == ""
        assert invs[1]["spec"]["category"] == "special"

    def test_null_kwargs_omitted(self):
        text = """
'table mylib.q':
  kind: python_call_eq
  function: fn
  columns: [id, args, kwargs, expected]
  rows:
    - [no_kwargs, ["a"], ~, "A"]
"""
        invs = self._compile_table(text)
        assert "kwargs" not in invs[0]["spec"]

    def test_kwargs_passed_through(self):
        text = """
'table mylib.q':
  kind: python_call_eq
  function: quote
  columns: [id, args, kwargs, expected]
  rows:
    - [with_safe, ["/path"], {safe: "/"}, "/path"]
"""
        invs = self._compile_table(text)
        assert invs[0]["spec"]["kwargs"] == {"safe": "/"}

    def test_describe_template(self):
        text = """
'table mylib.consts':
  kind: constant_eq
  id_from: name
  describe: "Constant {name} == {expected_value}"
  columns: [name, expected_value]
  rows:
    - [MY_CONST, 42]
"""
        invs = self._compile_table(text)
        assert invs[0]["description"] == "Constant MY_CONST == 42"

    def test_column_mismatch_raises(self):
        text = """
'table mylib.bad':
  kind: python_call_eq
  function: fn
  columns: [id, args, expected]
  rows:
    - [only_two_vals, ["x"]]
"""
        with pytest.raises(zc.CompileError, match="row has"):
            self._compile_table(text)

    def test_shared_spec_fields(self):
        """Fields from table header (other than meta) go into each row's spec."""
        text = """
'table mylib.hash':
  kind: hash_known_vector
  category: known_vector
  algorithm: sha256
  columns: [id, data_b64, expected_hex]
  rows:
    - [empty, "", "e3b0c4"]
"""
        invs = self._compile_table(text)
        assert invs[0]["spec"]["algorithm"] == "sha256"
        assert invs[0]["spec"]["data_b64"] == ""
        assert invs[0]["spec"]["expected_hex"] == "e3b0c4"


# ---------------------------------------------------------------------------
# Invariant block compilation
# ---------------------------------------------------------------------------

class TestInvariantCompilation:
    def _compile_inv(self, full_id: str, block_text: str,
                     canonical: str = "mylib") -> dict:
        block = _load_zsdl(block_text)
        return zc.ZSDLCompiler()._compile_invariant(full_id, block, canonical)

    def test_call_eq_form(self):
        block = """
call: urlparse("https://example.com").scheme
eq: "https"
category: urlparse
"""
        inv = self._compile_inv("mylib.urlparse.scheme", block)
        assert inv["id"] == "mylib.urlparse.scheme"
        assert inv["kind"] == "python_call_eq"
        assert inv["spec"]["function"] == "urlparse"
        assert inv["spec"]["method"] == "scheme"
        assert inv["spec"]["expected"] == "https"
        assert inv["category"] == "urlparse"

    def test_call_raises_form(self):
        block = """
call: loads("bad json")
raises: ValueError
"""
        inv = self._compile_inv("mylib.loads.error", block)
        assert inv["kind"] == "python_call_raises"
        assert inv["spec"]["expected_exception"] == "ValueError"

    def test_structured_form(self):
        block = """
kind: version_prefix
function: ZSTD_versionString
expected_prefix_b64: MS4=
"""
        inv = self._compile_inv("zstd.version.prefix", block)
        assert inv["kind"] == "version_prefix"
        assert inv["spec"]["function"] == "ZSTD_versionString"
        assert inv["spec"]["expected_prefix_b64"] == "MS4="

    def test_auto_description(self):
        block = "kind: call_eq\nfunction: fn\nargs: []\nexpected: 0"
        inv = self._compile_inv("mylib.fn.test", block)
        assert "call_eq" in inv["description"]
        assert "mylib.fn.test" in inv["description"]

    def test_explicit_description(self):
        block = "kind: call_eq\ndescription: 'My desc'\nfunction: fn\nargs: []\nexpected: 0"
        inv = self._compile_inv("mylib.fn.test", block)
        assert inv["description"] == "My desc"

    def test_rfc_maps_to_rfc_reference(self):
        block = "kind: python_call_eq\ncall: fn()\neq: 1\nrfc: 'RFC 3986 §3.1'"
        inv = self._compile_inv("mylib.fn.test", block)
        assert inv["rfc_reference"] == "RFC 3986 §3.1"

    def test_missing_kind_raises(self):
        block = "function: fn\nargs: []\nexpected: 0"
        with pytest.raises(zc.CompileError, match="kind"):
            self._compile_inv("mylib.fn.test", block)

    def test_call_without_eq_raises(self):
        block = "call: fn()"
        with pytest.raises(zc.CompileError, match="eq"):
            self._compile_inv("mylib.fn.test", block)


# ---------------------------------------------------------------------------
# Full compiler output structure
# ---------------------------------------------------------------------------

class TestFullCompilerOutput:
    def test_required_sections_present(self):
        text = _minimal_header() + "\ninvariant mylib.x:\n  kind: call_eq\n  function: f\n  args: []\n  expected: 0\n"
        out = _compile_text(text)
        required = [
            "schema_version", "identity", "provenance", "library",
            "constants", "types", "functions", "invariants",
            "wire_formats", "error_model",
        ]
        for key in required:
            assert key in out, f"Missing required key: {key}"

    def test_schema_version(self):
        text = _minimal_header() + "\ninvariant mylib.x:\n  kind: call_eq\n  function: f\n  args: []\n  expected: 0\n"
        out = _compile_text(text)
        assert out["schema_version"] == "0.1"

    def test_identity_fields(self):
        text = _minimal_header("docs: https://example.com\n") + "\ninvariant mylib.x:\n  kind: call_eq\n  function: f\n  args: []\n  expected: 0\n"
        out = _compile_text(text)
        assert out["identity"]["canonical_name"] == "mylib"
        assert out["identity"]["public_docs_url"] == "https://example.com"

    def test_invariants_list(self):
        text = _minimal_header() + "\n"
        text += "invariant mylib.a:\n  kind: call_eq\n  function: fa\n  args: []\n  expected: 0\n"
        text += "invariant mylib.b:\n  kind: call_eq\n  function: fb\n  args: []\n  expected: 1\n"
        out = _compile_text(text)
        assert len(out["invariants"]) == 2
        ids = [inv["id"] for inv in out["invariants"]]
        assert "mylib.a" in ids
        assert "mylib.b" in ids

    def test_table_generates_invariants(self):
        text = _minimal_header() + "\n"
        text += "'table mylib.vals':\n  kind: call_eq\n  function: fn\n  columns: [id, args, expected]\n  rows:\n    - [x, [], 1]\n    - [y, [], 2]\n"
        out = _compile_text(text)
        assert len(out["invariants"]) == 2


# ---------------------------------------------------------------------------
# Integration: compile ZSDL specs and verify with harness
# ---------------------------------------------------------------------------

VERIFY_SCRIPT = REPO_ROOT / "tools" / "verify_behavior.py"

ZSDL_SPECS = [
    ("zstd", 15),
    ("difflib", 17),
    ("urllib_parse", 18),
]


@pytest.mark.parametrize("spec_name,expected_invariants", ZSDL_SPECS)
def test_zsdl_compile_and_verify(spec_name, expected_invariants, tmp_path):
    """Compile a ZSDL spec to JSON, verify invariant count, then run harness."""
    zsdl_path = REPO_ROOT / "zspecs" / f"{spec_name}.zspec.zsdl"
    assert zsdl_path.exists(), f"ZSDL file not found: {zsdl_path}"

    compiler = zc.ZSDLCompiler()
    compiled = compiler.compile_file(zsdl_path)

    assert compiled["schema_version"] == "0.1"
    assert compiled["identity"]["canonical_name"] == spec_name
    assert len(compiled["invariants"]) == expected_invariants

    # Write compiled JSON to tmp file
    json_path = tmp_path / f"{spec_name}.zspec.json"
    json_path.write_text(json.dumps(compiled, indent=2), encoding="utf-8")

    # Run harness; check all invariants pass
    result = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), str(json_path)],
        capture_output=True,
        text=True,
    )
    # Last non-empty line contains pass/fail summary
    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    summary = lines[-1] if lines else ""
    assert "0 failed" in summary, (
        f"{spec_name}: harness reported failures.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert result.returncode == 0, f"{spec_name}: harness exited {result.returncode}"


def test_zsdl_zstd_invariant_ids():
    """Compiled zstd spec has the exact invariant IDs the existing spec has."""
    zsdl_path = REPO_ROOT / "zspecs" / "zstd.zspec.zsdl"
    compiled = zc.ZSDLCompiler().compile_file(zsdl_path)
    ids = {inv["id"] for inv in compiled["invariants"]}
    expected_ids = {
        "zstd.version.prefix",
        "zstd.maxCLevel.eq_22",
        "zstd.isError.zero_not_error",
        "zstd.isError.small_values_not_error",
        "zstd.compressBound.known_value",
        "zstd.compressBound.not_error",
        "zstd.maxCLevel.is_not_error",
        "zstd.versionNumber.not_error",
        "zstd.isError.near_size_max",
        "zstd.compressBound.nonzero_input",
        "zstd.compressBound.zero_input",
        "zstd.compressBound.large_input",
        "zstd.compressBound.256bytes",
        "zstd.compressBound.monotone",
        "zstd.versionNumber.range",
    }
    assert ids == expected_ids


def test_zsdl_difflib_invariant_ids():
    """Compiled difflib spec has the exact invariant IDs from the original JSON spec."""
    zsdl_path = REPO_ROOT / "zspecs" / "difflib.zspec.zsdl"
    compiled = zc.ZSDLCompiler().compile_file(zsdl_path)
    ids = {inv["id"] for inv in compiled["invariants"]}
    expected_ids = {
        "difflib.sequence_matcher.ratio_identical",
        "difflib.sequence_matcher.ratio_disjoint",
        "difflib.sequence_matcher.ratio_empty",
        "difflib.sequence_matcher.quick_ratio_identical",
        "difflib.sequence_matcher.real_quick_ratio_identical",
        "difflib.sequence_matcher.find_longest_match_size",
        "difflib.sequence_matcher.find_longest_match_b_index",
        "difflib.get_close_matches.match_found",
        "difflib.get_close_matches.no_match",
        "difflib.get_close_matches.n_limits_results",
        "difflib.get_close_matches.exact_match",
        "difflib.is_character_junk.space",
        "difflib.is_character_junk.tab",
        "difflib.is_character_junk.letter",
        "difflib.is_line_junk.blank",
        "difflib.is_line_junk.hash_only",
        "difflib.is_line_junk.code_line",
    }
    assert ids == expected_ids


def test_zsdl_urllib_parse_invariant_ids():
    """Compiled urllib_parse spec has all 18 expected invariant IDs."""
    zsdl_path = REPO_ROOT / "zspecs" / "urllib_parse.zspec.zsdl"
    compiled = zc.ZSDLCompiler().compile_file(zsdl_path)
    ids = {inv["id"] for inv in compiled["invariants"]}
    expected_ids = {
        "urllib_parse.urlparse.scheme",
        "urllib_parse.urlparse.netloc",
        "urllib_parse.urlparse.path",
        "urllib_parse.urlparse.query",
        "urllib_parse.urlparse.fragment",
        "urllib_parse.urlparse.port",
        "urllib_parse.urlparse.userinfo",
        "urllib_parse.quote.spaces",
        "urllib_parse.quote.empty_safe",
        "urllib_parse.quote_plus.spaces",
        "urllib_parse.unquote.percent_encoded",
        "urllib_parse.unquote_plus.plus_to_space",
        "urllib_parse.quote_unquote_roundtrip",
        "urllib_parse.urljoin.relative",
        "urllib_parse.urljoin.absolute_overrides",
        "urllib_parse.urlencode.simple",
        "urllib_parse.parse_qs.multi_value",
        "urllib_parse.parse_qs.single_value",
    }
    assert ids == expected_ids
