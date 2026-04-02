"""
Tests for tools/validate_record.py.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

import validate_record as vr

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    name="zlib", ecosystem="nixpkgs", version="1.3.1",
    confidence=0.95, license=None, sources=None, patches=None,
):
    return {
        "schema_version": "0.2",
        "identity": {
            "canonical_name": name,
            "canonical_id": f"pkg:{name}",
            "version": version,
            "ecosystem": ecosystem,
            "ecosystem_id": f"pkgs/{name}",
        },
        "descriptive": {
            "summary": "A test package",
            "homepage": "https://example.com/",
            "license": license if license is not None else ["MIT"],
            "categories": [],
            "maintainers": [],
        },
        "conflicts": [],
        "sources": sources if sources is not None else [{"type": "archive", "url": "https://example.com/pkg.tar.gz"}],
        "dependencies": {"build": [], "host": [], "runtime": [], "test": []},
        "build": {"system_kind": "autotools"},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": patches if patches is not None else [],
        "tests": {},
        "provenance": {
            "confidence": confidence,
            "generated_by": "test",
            "unmapped": [],
            "warnings": [],
        },
        "extensions": {},
    }


def _errors(issues):
    return [i for i in issues if "ERROR" in i]


def _warns(issues):
    return [i for i in issues if "WARN" in i]


# ---------------------------------------------------------------------------
# validate_record: valid records
# ---------------------------------------------------------------------------

def test_valid_record_produces_no_issues():
    rec = _make_record()
    assert vr.validate_record(rec, "test.json") == []


def test_valid_record_all_ecosystems():
    for eco in ("nixpkgs", "freebsd_ports"):
        rec = _make_record(ecosystem=eco)
        assert _errors(vr.validate_record(rec, "test.json")) == []


# ---------------------------------------------------------------------------
# validate_record: missing required fields
# ---------------------------------------------------------------------------

def test_missing_top_level_field():
    rec = _make_record()
    del rec["identity"]
    issues = vr.validate_record(rec, "t.json")
    assert any("identity" in i and "ERROR" in i for i in issues)


def test_missing_all_required_top_level():
    issues = vr.validate_record({}, "empty.json")
    errors = _errors(issues)
    for field in vr.REQUIRED_TOP:
        assert any(field in e for e in errors), f"expected error for missing '{field}'"


def test_missing_identity_subfield():
    rec = _make_record()
    del rec["identity"]["canonical_name"]
    issues = vr.validate_record(rec, "t.json")
    assert any("canonical_name" in i and "ERROR" in i for i in issues)


def test_missing_dependency_key():
    rec = _make_record()
    del rec["dependencies"]["test"]
    issues = vr.validate_record(rec, "t.json")
    assert any("dependencies.test" in i and "ERROR" in i for i in issues)


def test_missing_source_type():
    rec = _make_record(sources=[{"url": "https://example.com"}])
    issues = vr.validate_record(rec, "t.json")
    assert any("sources[0]" in i and "ERROR" in i for i in issues)


def test_missing_patch_path():
    rec = _make_record(patches=[{"reason": "fix build"}])
    issues = vr.validate_record(rec, "t.json")
    assert any("patches[0]" in i and "ERROR" in i for i in issues)


# ---------------------------------------------------------------------------
# validate_record: type errors
# ---------------------------------------------------------------------------

def test_identity_not_object():
    rec = _make_record()
    rec["identity"] = "not an object"
    issues = vr.validate_record(rec, "t.json")
    assert any("identity" in i and "ERROR" in i for i in issues)


def test_dependencies_not_object():
    rec = _make_record()
    rec["dependencies"] = []
    issues = vr.validate_record(rec, "t.json")
    assert any("dependencies" in i and "ERROR" in i for i in issues)


def test_dependency_array_contains_non_string():
    rec = _make_record()
    rec["dependencies"]["build"] = [42, "cmake"]
    issues = vr.validate_record(rec, "t.json")
    assert any("dependencies.build[0]" in i and "ERROR" in i for i in issues)


def test_license_not_array():
    rec = _make_record()
    rec["descriptive"]["license"] = "MIT"
    issues = vr.validate_record(rec, "t.json")
    assert any("license" in i and "ERROR" in i for i in issues)


def test_features_not_object():
    rec = _make_record()
    rec["features"] = "not an object"
    issues = vr.validate_record(rec, "t.json")
    assert any("features" in i and "ERROR" in i for i in issues)


def test_sources_not_array():
    rec = _make_record()
    rec["sources"] = {"type": "archive"}
    issues = vr.validate_record(rec, "t.json")
    assert any("sources" in i and "ERROR" in i for i in issues)


def test_patches_not_array():
    rec = _make_record()
    rec["patches"] = {"path": "p.patch"}
    issues = vr.validate_record(rec, "t.json")
    assert any("patches" in i and "ERROR" in i for i in issues)


def test_platforms_include_not_array():
    rec = _make_record()
    rec["platforms"]["include"] = "linux"
    issues = vr.validate_record(rec, "t.json")
    assert any("platforms.include" in i and "ERROR" in i for i in issues)


def test_conflicts_not_array():
    rec = _make_record()
    rec["conflicts"] = "openssl30"
    issues = vr.validate_record(rec, "t.json")
    assert any("conflicts" in i and "ERROR" in i for i in issues)


def test_conflicts_contains_non_string():
    rec = _make_record()
    rec["conflicts"] = [42]
    issues = vr.validate_record(rec, "t.json")
    assert any("conflicts[0]" in i and "ERROR" in i for i in issues)


def test_conflicts_valid_list():
    rec = _make_record()
    rec["conflicts"] = ["openssl30", "libressl"]
    assert _errors(vr.validate_record(rec, "t.json")) == []


def test_maintainers_not_array():
    rec = _make_record()
    rec["descriptive"]["maintainers"] = "someone"
    issues = vr.validate_record(rec, "t.json")
    assert any("maintainers" in i and "ERROR" in i for i in issues)


def test_deprecated_not_bool():
    rec = _make_record()
    rec["descriptive"]["deprecated"] = "yes"
    issues = vr.validate_record(rec, "t.json")
    assert any("deprecated" in i and "ERROR" in i for i in issues)


def test_deprecated_valid_bool():
    rec = _make_record()
    rec["descriptive"]["deprecated"] = True
    assert _errors(vr.validate_record(rec, "t.json")) == []


# ---------------------------------------------------------------------------
# validate_record: value range checks
# ---------------------------------------------------------------------------

def test_confidence_too_high():
    rec = _make_record(confidence=1.5)
    issues = vr.validate_record(rec, "t.json")
    assert any("confidence" in i and "ERROR" in i for i in issues)


def test_confidence_negative():
    rec = _make_record(confidence=-0.1)
    issues = vr.validate_record(rec, "t.json")
    assert any("confidence" in i and "ERROR" in i for i in issues)


def test_confidence_boundary_values():
    for conf in (0.0, 0.5, 1.0):
        rec = _make_record(confidence=conf)
        issues = vr.validate_record(rec, "t.json")
        assert not _errors(issues), f"confidence={conf} should be valid"


def test_schema_version_empty_string():
    rec = _make_record()
    rec["schema_version"] = ""
    issues = vr.validate_record(rec, "t.json")
    assert _errors(issues)


# ---------------------------------------------------------------------------
# validate_record: warnings
# ---------------------------------------------------------------------------

def test_unknown_ecosystem_produces_warning():
    rec = _make_record(ecosystem="homebrew")
    issues = vr.validate_record(rec, "t.json")
    assert _errors(issues) == []
    assert any("ecosystem" in i and "WARN" in i for i in issues)


def test_unknown_build_system_produces_warning():
    rec = _make_record()
    rec["build"]["system_kind"] = "bazelbuild"
    issues = vr.validate_record(rec, "t.json")
    assert _errors(issues) == []
    assert any("system_kind" in i and "WARN" in i for i in issues)


def test_strict_flags_empty_summary():
    rec = _make_record()
    rec["descriptive"]["summary"] = ""
    issues_normal = vr.validate_record(rec, "t.json", strict=False)
    issues_strict = vr.validate_record(rec, "t.json", strict=True)
    assert _errors(issues_normal) == []
    assert any("summary" in i and "WARN" in i for i in issues_strict)


def test_strict_flags_unmapped_fields():
    rec = _make_record()
    rec["provenance"]["unmapped"] = ["LICENSE", "homepage"]
    issues_normal = vr.validate_record(rec, "t.json", strict=False)
    issues_strict = vr.validate_record(rec, "t.json", strict=True)
    assert _errors(issues_normal) == []
    assert any("unmapped" in i and "WARN" in i for i in issues_strict)


def test_strict_flags_warnings_field():
    rec = _make_record()
    rec["provenance"]["warnings"] = ["version not found"]
    issues_strict = vr.validate_record(rec, "t.json", strict=True)
    assert any("warnings" in i and "WARN" in i for i in issues_strict)


# ---------------------------------------------------------------------------
# validate_paths: file and directory dispatch
# ---------------------------------------------------------------------------

def test_validate_file_valid(tmp_path):
    rec = _make_record()
    f = tmp_path / "rec.json"
    f.write_text(json.dumps(rec), encoding="utf-8")
    invalid, total = vr.validate_paths([f], strict=False, quiet=True)
    assert total == 1
    assert invalid == 0


def test_validate_file_invalid(tmp_path):
    rec = _make_record()
    del rec["identity"]["canonical_name"]
    f = tmp_path / "rec.json"
    f.write_text(json.dumps(rec), encoding="utf-8")
    invalid, total = vr.validate_paths([f], strict=False, quiet=True)
    assert total == 1
    assert invalid == 1


def test_validate_directory_skips_manifest(tmp_path):
    # manifest.json should be ignored
    rec = _make_record()
    (tmp_path / "manifest.json").write_text(json.dumps(rec), encoding="utf-8")
    (tmp_path / "zlib.json").write_text(json.dumps(rec), encoding="utf-8")
    invalid, total = vr.validate_paths([tmp_path], strict=False, quiet=True)
    assert total == 1


def test_validate_directory_skips_invalid_json(tmp_path):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    invalid, total = vr.validate_paths([tmp_path], strict=False, quiet=True)
    assert total == 1
    assert invalid == 1


def test_validate_directory_skips_non_records(tmp_path):
    (tmp_path / "meta.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    invalid, total = vr.validate_paths([tmp_path], strict=False, quiet=True)
    assert total == 0


def test_validate_all_examples_pass():
    examples_dir = REPO_ROOT / "examples"
    invalid, total = vr.validate_paths([examples_dir], strict=False, quiet=True)
    assert total >= 3
    assert invalid == 0


def test_validate_nonexistent_path(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    invalid, total = vr.validate_paths([missing], strict=False, quiet=True)
    assert invalid >= 1


# ---------------------------------------------------------------------------
# behavioral_spec field tests
# ---------------------------------------------------------------------------

def test_behavioral_spec_not_a_string_is_error():
    rec = _make_record()
    rec["behavioral_spec"] = 123
    issues = vr.validate_record(rec, "test.json")
    assert any("behavioral_spec" in i and "string" in i for i in issues)


def test_behavioral_spec_missing_file_is_error(tmp_path):
    rec = _make_record()
    rec["behavioral_spec"] = "zspecs/does_not_exist.zspec.json"
    issues = vr.validate_record(rec, "test.json")
    assert any("behavioral_spec" in i and "not found" in i for i in issues)


def test_behavioral_spec_valid_zlib_passes():
    """A record pointing at the real zlib spec should produce no behavioral errors."""
    rec = _make_record()
    rec["behavioral_spec"] = "zspecs/zlib.zspec.json"
    issues = vr.validate_record(rec, "test.json")
    # Filter to just behavioral_spec issues (non-WARN)
    errors = [i for i in issues if "behavioral_spec" in i and "ERROR" in i]
    assert not errors, errors


def test_behavioral_spec_valid_openssl_passes():
    """A record pointing at the real openssl spec should produce no behavioral errors."""
    rec = _make_record()
    rec["behavioral_spec"] = "zspecs/openssl.zspec.json"
    issues = vr.validate_record(rec, "test.json")
    errors = [i for i in issues if "behavioral_spec" in i and "ERROR" in i]
    assert not errors, errors


def test_examples_with_behavioral_spec_pass():
    """All example records that have behavioral_spec set should validate cleanly."""
    examples_dir = REPO_ROOT / "examples"
    invalid, total = vr.validate_paths([examples_dir], strict=False, quiet=True)
    assert invalid == 0
