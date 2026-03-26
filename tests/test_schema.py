"""
Tests for schema/package-recipe.schema.json and example records in examples/.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "package-recipe.schema.json"
EXAMPLES_DIR = REPO_ROOT / "examples"

REQUIRED_TOP_LEVEL = [
    "schema_version", "identity", "descriptive", "sources",
    "dependencies", "build", "features", "platforms", "patches",
    "tests", "provenance", "extensions",
]
REQUIRED_IDENTITY = ["canonical_name", "canonical_id", "version", "ecosystem", "ecosystem_id"]
REQUIRED_DEPS = ["build", "host", "runtime", "test"]


def _examples():
    return list(EXAMPLES_DIR.glob("*.json"))


def test_schema_is_valid_json():
    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert data["type"] == "object"
    assert "properties" in data
    assert data["title"] == "Canonical Package Recipe"


def test_schema_required_fields():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(REQUIRED_TOP_LEVEL) <= set(schema["required"])


def test_schema_identity_required_subfields():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    id_props = schema["properties"]["identity"]
    assert set(REQUIRED_IDENTITY) <= set(id_props["required"])


def test_schema_dependency_required_subfields():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    dep_props = schema["properties"]["dependencies"]
    assert set(REQUIRED_DEPS) <= set(dep_props["required"])


def test_examples_exist():
    assert len(_examples()) >= 3, "Expected at least 3 example files"


def test_examples_have_required_top_level_fields():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        for field in REQUIRED_TOP_LEVEL:
            assert field in rec, f"{path.name}: missing required field '{field}'"


def test_examples_identity_fields():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        identity = rec["identity"]
        for field in REQUIRED_IDENTITY:
            assert field in identity, f"{path.name}: identity missing '{field}'"


def test_examples_dependency_keys():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        deps = rec["dependencies"]
        for key in REQUIRED_DEPS:
            assert key in deps, f"{path.name}: dependencies missing '{key}'"
        for key in REQUIRED_DEPS:
            assert isinstance(deps[key], list), f"{path.name}: dependencies.{key} must be a list"


def test_examples_schema_version_is_string():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(rec["schema_version"], str)
        assert rec["schema_version"], f"{path.name}: schema_version must not be empty"


def test_examples_provenance_confidence_range():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        conf = rec["provenance"].get("confidence")
        if conf is not None:
            assert 0.0 <= conf <= 1.0, f"{path.name}: confidence {conf} out of range [0, 1]"


def test_examples_sources_have_type():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        for i, src in enumerate(rec["sources"]):
            assert "type" in src, f"{path.name}: sources[{i}] missing 'type'"


def test_examples_patches_have_path_and_reason():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        for i, patch in enumerate(rec["patches"]):
            assert "path" in patch, f"{path.name}: patches[{i}] missing 'path'"


def test_examples_platforms_structure():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        platforms = rec["platforms"]
        assert isinstance(platforms, dict), f"{path.name}: platforms must be an object"


def test_examples_canonical_id_nonempty():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["identity"]["canonical_id"], f"{path.name}: canonical_id must not be empty"


def test_examples_canonical_name_nonempty():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["identity"]["canonical_name"], f"{path.name}: canonical_name must not be empty"


def test_examples_ecosystem_nonempty():
    for path in _examples():
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["identity"]["ecosystem"], f"{path.name}: ecosystem must not be empty"
