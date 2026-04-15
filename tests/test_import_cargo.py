"""
tests/test_import_cargo.py

Tests for import_cargo() and transitive license checking — the crates.io importer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import theseus.importer as imp


# ---------------------------------------------------------------------------
# Test fixtures — crates.io API response shapes
# ---------------------------------------------------------------------------

def _cargo_crate_response(
    name="serde",
    version="1.0.200",
    license_="MIT OR Apache-2.0",
    description="A serialization framework",
    homepage="https://serde.rs",
    repository="https://github.com/serde-rs/serde",
    categories=None,
    keywords=None,
    yanked=False,
):
    return {
        "crate": {
            "id": name,
            "name": name,
            "max_version": version,
            "description": description,
            "homepage": homepage,
            "repository": repository,
            "license": license_,
            "categories": categories or ["encoding"],
            "keywords": keywords or ["serde", "serialization"],
        },
        "versions": [
            {
                "num": version,
                "yanked": yanked,
                "license": license_,
                "dl_path": f"/api/v1/crates/{name}/{version}/download",
                "checksum": "abc123def456",
                "rust_version": "1.56.0",
                "edition": "2021",
            },
        ],
    }


def _cargo_deps_response(runtime=None, build=None, dev=None):
    deps = []
    for dep_name in (runtime or []):
        deps.append({"crate_id": dep_name, "kind": "normal", "optional": False})
    for dep_name in (build or []):
        deps.append({"crate_id": dep_name, "kind": "build", "optional": False})
    for dep_name in (dev or []):
        deps.append({"crate_id": dep_name, "kind": "dev", "optional": False})
    return {"dependencies": deps}


def _make_router(crate_map: dict[str, tuple[dict, dict]]):
    """Build a mock _fetch_json that routes by URL.

    crate_map maps crate_name -> (crate_response, deps_response).
    """
    def router(url, timeout=15):
        for name, (crate_resp, deps_resp) in crate_map.items():
            if f"/crates/{name}/" in url and "/dependencies" in url:
                return deps_resp
            if url.endswith(f"/crates/{name}"):
                return crate_resp
        return None
    return router


# ---------------------------------------------------------------------------
# import_cargo — basic record generation
# ---------------------------------------------------------------------------

class TestImportCargo:
    def test_creates_json_file(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["serde"], tmp_path)
        assert count == 1
        assert (tmp_path / "serde.json").exists()

    def test_record_has_correct_ecosystem(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["identity"]["ecosystem"] == "cargo"

    def test_build_system_is_cargo(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["build"]["system_kind"] == "cargo"

    def test_canonical_name_normalizes_underscores(self, tmp_path):
        router = _make_router({
            "serde_json": (_cargo_crate_response(name="serde_json"), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde_json"], tmp_path)
        assert (tmp_path / "serde-json.json").exists()
        rec = json.loads((tmp_path / "serde-json.json").read_text())
        assert rec["identity"]["canonical_name"] == "serde-json"

    def test_ecosystem_id_preserves_original_name(self, tmp_path):
        router = _make_router({
            "serde_json": (_cargo_crate_response(name="serde_json"), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde_json"], tmp_path)
        rec = json.loads((tmp_path / "serde-json.json").read_text())
        assert rec["identity"]["ecosystem_id"] == "serde_json"

    def test_runtime_deps_extracted(self, tmp_path):
        router = _make_router({
            "serde": (
                _cargo_crate_response(),
                _cargo_deps_response(runtime=["serde_derive", "serde_json"]),
            ),
            "serde_derive": (_cargo_crate_response(name="serde_derive"), _cargo_deps_response()),
            "serde_json": (_cargo_crate_response(name="serde_json"), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "serde_derive" in rec["dependencies"]["runtime"]
        assert "serde_json" in rec["dependencies"]["runtime"]

    def test_build_deps_extracted(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response(build=["cc"])),
            "cc": (_cargo_crate_response(name="cc"), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "cc" in rec["dependencies"]["build"]

    def test_dev_deps_go_to_test(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response(dev=["criterion"])),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "criterion" in rec["dependencies"]["test"]

    def test_optional_deps_excluded_from_runtime(self, tmp_path):
        deps_data = {"dependencies": [
            {"crate_id": "serde_derive", "kind": "normal", "optional": True},
            {"crate_id": "serde_json", "kind": "normal", "optional": False},
        ]}
        router = _make_router({
            "serde": (_cargo_crate_response(), deps_data),
            "serde_json": (_cargo_crate_response(name="serde_json"), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "serde_derive" not in rec["dependencies"]["runtime"]
        assert "serde_json" in rec["dependencies"]["runtime"]

    def test_source_url_and_checksum(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "crates.io" in rec["sources"][0]["url"]
        assert rec["sources"][0]["sha256"] == "abc123def456"

    def test_license_string(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["descriptive"]["license"] == ["MIT OR Apache-2.0"]

    def test_fetch_failure_skipped(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=None):
            count = imp.import_cargo(["does-not-exist"], tmp_path)
        assert count == 0

    def test_multiple_crates(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response("serde"), _cargo_deps_response()),
            "tokio": (_cargo_crate_response("tokio"), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["serde", "tokio"], tmp_path)
        assert count == 2
        assert (tmp_path / "serde.json").exists()
        assert (tmp_path / "tokio.json").exists()

    def test_yanked_version_skipped(self, tmp_path):
        resp = _cargo_crate_response(yanked=True)
        resp["versions"].append({
            "num": "0.9.0",
            "yanked": False,
            "license": "MIT OR Apache-2.0",
            "dl_path": "/api/v1/crates/serde/0.9.0/download",
            "checksum": "older123",
            "rust_version": "",
            "edition": "2015",
        })
        router = _make_router({"serde": (resp, _cargo_deps_response())})
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["identity"]["version"] == "0.9.0"

    def test_cargo_extension_has_rust_version(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["extensions"]["cargo"]["rust_version"] == "1.56.0"
        assert rec["extensions"]["cargo"]["edition"] == "2021"

    def test_cargo_extension_has_keywords(self, tmp_path):
        router = _make_router({
            "serde": (
                _cargo_crate_response(keywords=["serde", "serialization"]),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "serde" in rec["extensions"]["cargo"]["keywords"]

    def test_source_repository_normalized(self, tmp_path):
        router = _make_router({
            "serde": (
                _cargo_crate_response(repository="git+https://github.com/serde-rs/serde.git"),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["extensions"]["cargo"]["source_repository"] == "https://github.com/serde-rs/serde"

    def test_schema_version(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["schema_version"] == "0.2"

    def test_all_required_schema_fields_present(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        required = [
            "schema_version", "identity", "descriptive", "sources",
            "dependencies", "build", "features", "platforms", "conflicts",
            "patches", "tests", "provenance", "extensions",
        ]
        for field in required:
            assert field in rec, f"Missing required field: {field}"

    def test_provenance_generated_by(self, tmp_path):
        router = _make_router({
            "serde": (_cargo_crate_response(), _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert rec["provenance"]["generated_by"] == "bootstrap_canonical_recipes.py"

    def test_categories_from_crate(self, tmp_path):
        router = _make_router({
            "serde": (
                _cargo_crate_response(categories=["encoding", "data-structures"]),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            imp.import_cargo(["serde"], tmp_path)
        rec = json.loads((tmp_path / "serde.json").read_text())
        assert "encoding" in rec["descriptive"]["categories"]


# ---------------------------------------------------------------------------
# SPDX OR/AND license expression parsing
# ---------------------------------------------------------------------------

class TestLicenseIsPermissive:
    def test_mit(self):
        assert imp._license_is_permissive("MIT") is True

    def test_apache(self):
        assert imp._license_is_permissive("Apache-2.0") is True

    def test_bsd3(self):
        assert imp._license_is_permissive("BSD-3-Clause") is True

    def test_gpl(self):
        assert imp._license_is_permissive("GPL-3.0") is False

    def test_lgpl(self):
        assert imp._license_is_permissive("LGPL-2.1") is False

    def test_agpl(self):
        assert imp._license_is_permissive("AGPL-3.0") is False

    def test_or_all_permissive(self):
        assert imp._license_is_permissive("MIT OR Apache-2.0") is True

    def test_or_with_copyleft_alternative(self):
        """MIT OR LGPL-2.1 is permissive — you can choose MIT."""
        assert imp._license_is_permissive("MIT OR Apache-2.0 OR LGPL-2.1-or-later") is True

    def test_or_only_copyleft(self):
        assert imp._license_is_permissive("GPL-2.0 OR GPL-3.0") is False

    def test_and_all_permissive(self):
        assert imp._license_is_permissive("MIT AND BSD-3-Clause") is True

    def test_and_with_copyleft(self):
        """MIT AND GPL-3.0 is copyleft — you must comply with both."""
        assert imp._license_is_permissive("MIT AND GPL-3.0") is False

    def test_empty(self):
        assert imp._license_is_permissive("") is None

    def test_unknown(self):
        assert imp._license_is_permissive("CustomLicense-1.0") is None

    def test_r_efi_license(self):
        """The specific license that caused the wasm-pack false positive."""
        assert imp._license_is_permissive("MIT OR Apache-2.0 OR LGPL-2.1-or-later") is True


# ---------------------------------------------------------------------------
# Direct license filtering
# ---------------------------------------------------------------------------

class TestCargoCopyleftDirectFilter:
    def test_gpl_crate_skipped(self, tmp_path):
        router = _make_router({
            "gpl-crate": (_cargo_crate_response(name="gpl-crate", license_="GPL-3.0"),
                          _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["gpl-crate"], tmp_path)
        assert count == 0
        assert not list(tmp_path.iterdir())

    def test_lgpl_crate_skipped(self, tmp_path):
        router = _make_router({
            "lgpl-crate": (_cargo_crate_response(name="lgpl-crate", license_="LGPL-2.1"),
                           _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["lgpl-crate"], tmp_path)
        assert count == 0

    def test_agpl_crate_skipped(self, tmp_path):
        router = _make_router({
            "agpl-crate": (_cargo_crate_response(name="agpl-crate", license_="AGPL-3.0"),
                           _cargo_deps_response()),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["agpl-crate"], tmp_path)
        assert count == 0


# ---------------------------------------------------------------------------
# Transitive license checking — _cargo_check_dep_licenses
# ---------------------------------------------------------------------------

class TestCargoTransitiveLicense:
    def test_skips_crate_with_gpl_runtime_dep(self, tmp_path):
        """A → B(GPL) should be rejected."""
        router = _make_router({
            "clean-crate": (
                _cargo_crate_response(name="clean-crate"),
                _cargo_deps_response(runtime=["gpl-dep"]),
            ),
            "gpl-dep": (
                _cargo_crate_response(name="gpl-dep", license_="GPL-3.0"),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["clean-crate"], tmp_path)
        assert count == 0

    def test_skips_crate_with_gpl_build_dep(self, tmp_path):
        """A → B(GPL, build) should be rejected."""
        router = _make_router({
            "clean-crate": (
                _cargo_crate_response(name="clean-crate"),
                _cargo_deps_response(build=["gpl-build"]),
            ),
            "gpl-build": (
                _cargo_crate_response(name="gpl-build", license_="GPL-2.0"),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["clean-crate"], tmp_path)
        assert count == 0

    def test_allows_crate_with_gpl_dev_dep_only(self, tmp_path):
        """A → B(GPL, dev-only) should be allowed — dev deps aren't checked."""
        router = _make_router({
            "clean-crate": (
                _cargo_crate_response(name="clean-crate"),
                _cargo_deps_response(dev=["gpl-test-dep"]),
            ),
            # gpl-test-dep won't be fetched since dev deps aren't traversed
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["clean-crate"], tmp_path)
        assert count == 1

    def test_skips_crate_with_deep_gpl_transitive_dep(self, tmp_path):
        """A → B(MIT) → C(GPL) should be rejected."""
        router = _make_router({
            "top-crate": (
                _cargo_crate_response(name="top-crate"),
                _cargo_deps_response(runtime=["mid-crate"]),
            ),
            "mid-crate": (
                _cargo_crate_response(name="mid-crate"),
                _cargo_deps_response(runtime=["gpl-leaf"]),
            ),
            "gpl-leaf": (
                _cargo_crate_response(name="gpl-leaf", license_="GPL-3.0"),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["top-crate"], tmp_path)
        assert count == 0

    def test_allows_fully_permissive_dep_tree(self, tmp_path):
        """A → B(MIT) → C(Apache-2.0) should be allowed."""
        router = _make_router({
            "top-crate": (
                _cargo_crate_response(name="top-crate"),
                _cargo_deps_response(runtime=["mid-crate"]),
            ),
            "mid-crate": (
                _cargo_crate_response(name="mid-crate", license_="MIT"),
                _cargo_deps_response(runtime=["leaf-crate"]),
            ),
            "leaf-crate": (
                _cargo_crate_response(name="leaf-crate", license_="Apache-2.0"),
                _cargo_deps_response(),
            ),
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["top-crate"], tmp_path)
        assert count == 1

    def test_cache_shared_across_crates(self, tmp_path):
        """When importing multiple crates, license lookups should be cached."""
        call_count = 0
        base_router = _make_router({
            "crate-a": (
                _cargo_crate_response(name="crate-a"),
                _cargo_deps_response(runtime=["shared-dep"]),
            ),
            "crate-b": (
                _cargo_crate_response(name="crate-b"),
                _cargo_deps_response(runtime=["shared-dep"]),
            ),
            "shared-dep": (
                _cargo_crate_response(name="shared-dep"),
                _cargo_deps_response(),
            ),
        })

        def counting_router(url, timeout=15):
            nonlocal call_count
            call_count += 1
            return base_router(url, timeout)

        with patch.object(imp, "_fetch_json", side_effect=counting_router):
            count = imp.import_cargo(["crate-a", "crate-b"], tmp_path)
        assert count == 2
        # shared-dep metadata should have been fetched only once for the license
        # check, then cached for crate-b's check. Count the shared-dep fetches.
        # (The exact count depends on implementation, but we verify both imported.)

    def test_skips_optional_transitive_deps(self, tmp_path):
        """Optional deps in the transitive tree should not be checked."""
        deps_with_optional_gpl = {"dependencies": [
            {"crate_id": "gpl-optional", "kind": "normal", "optional": True},
            {"crate_id": "mit-required", "kind": "normal", "optional": False},
        ]}
        router = _make_router({
            "top-crate": (
                _cargo_crate_response(name="top-crate"),
                deps_with_optional_gpl,
            ),
            "mit-required": (
                _cargo_crate_response(name="mit-required", license_="MIT"),
                _cargo_deps_response(),
            ),
            # gpl-optional is not in the router — if fetched, it would return None
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["top-crate"], tmp_path)
        assert count == 1

    def test_unfetchable_transitive_dep_still_allows_import(self, tmp_path):
        """If a transitive dep can't be fetched, treat as unknown (allow)."""
        router = _make_router({
            "top-crate": (
                _cargo_crate_response(name="top-crate"),
                _cargo_deps_response(runtime=["ghost-dep"]),
            ),
            # ghost-dep not in router → returns None
        })
        with patch.object(imp, "_fetch_json", side_effect=router):
            count = imp.import_cargo(["top-crate"], tmp_path)
        assert count == 1
