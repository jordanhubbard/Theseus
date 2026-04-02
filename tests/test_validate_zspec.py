"""
Tests for tools/validate_zspec.py — Z-spec static schema validator.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_zspec as vz


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_spec(**overrides) -> dict:
    """Return a minimal valid spec, with optional field overrides."""
    spec = {
        "schema_version": "0.1",
        "identity": {
            "canonical_name": "test_lib",
            "spec_for_versions": ">=1.0.0",
        },
        "provenance": {
            "derived_from": ["RFC 0000"],
            "not_derived_from": ["source.c"],
        },
        "library": {"soname_patterns": []},
        "constants": {},
        "types": {},
        "functions": {},
        "invariants": [],
        "wire_formats": {},
        "error_model": {
            "return_code_semantics": "0 on success",
            "error_codes": [],
        },
    }
    spec.update(overrides)
    return spec


def _validate(spec: dict) -> list[str]:
    """Run stdlib validator and return error list."""
    import tempfile, json as _json
    tmp = Path(tempfile.mktemp(suffix=".zspec.json"))
    tmp.write_text(_json.dumps(spec))
    errors = vz.validate_file(tmp, schema=None, use_jsonschema=False)
    tmp.unlink(missing_ok=True)
    return errors


# ---------------------------------------------------------------------------
# TestSchemaLoad
# ---------------------------------------------------------------------------

class TestSchemaLoad:
    def test_schema_loads(self):
        schema = vz.load_schema()
        assert schema is not None
        assert schema["type"] == "object"

    def test_schema_has_required_fields(self):
        schema = vz.load_schema()
        assert "required" in schema
        assert "invariants" in schema["required"]

    def test_schema_kind_enum_complete(self):
        """Every kind in KNOWN_KINDS must appear in the schema's kind enum."""
        schema = vz.load_schema()
        inv_schema = schema["properties"]["invariants"]["items"]
        schema_kinds = set(inv_schema["properties"]["kind"]["enum"])
        for kind in vz.KNOWN_KINDS:
            assert kind in schema_kinds, f"kind {kind!r} missing from schema enum"


# ---------------------------------------------------------------------------
# TestMinimalValid
# ---------------------------------------------------------------------------

class TestMinimalValid:
    def test_minimal_spec_is_valid(self):
        assert _validate(_minimal_spec()) == []

    def test_valid_with_invariant(self):
        spec = _minimal_spec()
        spec["invariants"] = [{
            "id": "test.foo",
            "description": "desc",
            "category": "test",
            "kind": "python_call_eq",
            "spec": {"function": "foo", "args": [], "expected": 1},
        }]
        assert _validate(spec) == []


# ---------------------------------------------------------------------------
# TestMissingTopLevel
# ---------------------------------------------------------------------------

class TestMissingTopLevel:
    @pytest.mark.parametrize("field", vz.REQUIRED_TOP_LEVEL)
    def test_missing_top_level_field(self, field):
        spec = _minimal_spec()
        del spec[field]
        errors = _validate(spec)
        assert any(field in e for e in errors), f"expected error for missing '{field}'"


# ---------------------------------------------------------------------------
# TestMissingSubFields
# ---------------------------------------------------------------------------

class TestMissingSubFields:
    def test_missing_identity_canonical_name(self):
        spec = _minimal_spec()
        del spec["identity"]["canonical_name"]
        errors = _validate(spec)
        assert any("canonical_name" in e for e in errors)

    def test_missing_identity_spec_for_versions(self):
        spec = _minimal_spec()
        del spec["identity"]["spec_for_versions"]
        errors = _validate(spec)
        assert any("spec_for_versions" in e for e in errors)

    def test_missing_provenance_derived_from(self):
        spec = _minimal_spec()
        del spec["provenance"]["derived_from"]
        errors = _validate(spec)
        assert any("derived_from" in e for e in errors)

    def test_missing_provenance_not_derived_from(self):
        spec = _minimal_spec()
        del spec["provenance"]["not_derived_from"]
        errors = _validate(spec)
        assert any("not_derived_from" in e for e in errors)

    def test_missing_error_model_return_code_semantics(self):
        spec = _minimal_spec()
        del spec["error_model"]["return_code_semantics"]
        errors = _validate(spec)
        assert any("return_code_semantics" in e for e in errors)

    def test_missing_error_model_error_codes(self):
        spec = _minimal_spec()
        del spec["error_model"]["error_codes"]
        errors = _validate(spec)
        assert any("error_codes" in e for e in errors)


# ---------------------------------------------------------------------------
# TestInvariantValidation
# ---------------------------------------------------------------------------

class TestInvariantValidation:
    def _spec_with_inv(self, inv: dict) -> dict:
        spec = _minimal_spec()
        spec["invariants"] = [inv]
        return spec

    def test_valid_invariant_no_errors(self):
        spec = self._spec_with_inv({
            "id": "a.b",
            "description": "d",
            "category": "c",
            "kind": "call_eq",
            "spec": {},
        })
        assert _validate(spec) == []

    @pytest.mark.parametrize("field", vz.REQUIRED_INVARIANT)
    def test_missing_invariant_field(self, field):
        inv = {"id": "a.b", "description": "d", "category": "c", "kind": "call_eq", "spec": {}}
        del inv[field]
        errors = _validate(self._spec_with_inv(inv))
        assert errors, f"expected error for missing invariant field '{field}'"

    def test_unknown_kind_reported(self):
        spec = self._spec_with_inv({
            "id": "a.b",
            "description": "d",
            "category": "c",
            "kind": "not_a_real_kind",
            "spec": {},
        })
        errors = _validate(spec)
        assert any("unknown kind" in e for e in errors)

    def test_known_kind_no_error(self):
        for kind in vz.KNOWN_KINDS:
            spec = self._spec_with_inv({
                "id": "a.b",
                "description": "d",
                "category": "c",
                "kind": kind,
                "spec": {},
            })
            errors = _validate(spec)
            assert not any("unknown kind" in e for e in errors), \
                f"kind {kind!r} wrongly flagged as unknown"

    def test_duplicate_ids_reported(self):
        inv = {"id": "dup.id", "description": "d", "category": "c", "kind": "call_eq", "spec": {}}
        spec = _minimal_spec()
        spec["invariants"] = [inv.copy(), inv.copy()]
        errors = _validate(spec)
        assert any("duplicate id" in e for e in errors)

    def test_invariants_not_array(self):
        spec = _minimal_spec()
        spec["invariants"] = {"not": "an array"}
        errors = _validate(spec)
        assert any("invariants" in e for e in errors)


# ---------------------------------------------------------------------------
# TestBadJSON
# ---------------------------------------------------------------------------

class TestBadJSON:
    def test_invalid_json_reported(self, tmp_path):
        bad = tmp_path / "bad.zspec.json"
        bad.write_text("{not valid json")
        errors = vz.validate_file(bad, schema=None, use_jsonschema=False)
        assert any("invalid JSON" in e for e in errors)

    def test_non_object_json_reported(self, tmp_path):
        bad = tmp_path / "array.zspec.json"
        bad.write_text("[1, 2, 3]")
        errors = vz.validate_file(bad, schema=None, use_jsonschema=False)
        assert any("object" in e for e in errors)

    def test_missing_file_reported(self, tmp_path):
        missing = tmp_path / "does_not_exist.zspec.json"
        errors = vz.validate_file(missing, schema=None, use_jsonschema=False)
        assert any("cannot read file" in e for e in errors)


# ---------------------------------------------------------------------------
# TestRealSpecs
# ---------------------------------------------------------------------------

class TestRealSpecs:
    @pytest.mark.parametrize("spec_path", sorted(REPO_ROOT.glob("zspecs/*.zspec.json")))
    def test_real_spec_is_valid(self, spec_path):
        errors = vz.validate_file(spec_path, schema=None, use_jsonschema=False)
        assert not errors, f"{spec_path.name}:\n" + "\n".join(f"  {e}" for e in errors)


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_all_specs_exit_0(self):
        rc = vz.main([])
        assert rc == 0

    def test_main_explicit_file_exit_0(self):
        rc = vz.main([str(REPO_ROOT / "zspecs" / "zlib.zspec.json")])
        assert rc == 0

    def test_main_bad_spec_exit_1(self, tmp_path):
        bad = tmp_path / "bad.zspec.json"
        bad.write_text(json.dumps({"schema_version": "0.1"}))
        rc = vz.main([str(bad)])
        assert rc == 1

    def test_main_bad_json_exit_1(self, tmp_path):
        bad = tmp_path / "bad.zspec.json"
        bad.write_text("{oops")
        rc = vz.main([str(bad)])
        assert rc == 1
