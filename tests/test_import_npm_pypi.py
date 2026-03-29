"""
tests/test_import_npm_pypi.py

Tests for import_pypi(), import_npm(), _parse_pep508(), _npm_canonical_name(),
and the seed_from_ports tool.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import theseus.importer as imp

_SEED_TOOL = Path(__file__).resolve().parent.parent / "tools" / "seed_from_ports.py"
_seed_spec = importlib.util.spec_from_file_location("seed_from_ports", _SEED_TOOL)
seed_mod = importlib.util.module_from_spec(_seed_spec)
_seed_spec.loader.exec_module(seed_mod)

seed_pypi = seed_mod.seed_pypi


# ---------------------------------------------------------------------------
# _parse_pep508
# ---------------------------------------------------------------------------

class TestParsePep508:
    def test_simple_name(self):
        assert imp._parse_pep508("requests") == "requests"

    def test_name_with_version(self):
        assert imp._parse_pep508("requests>=2.0") == "requests"

    def test_name_with_extras(self):
        assert imp._parse_pep508("requests[security]>=2.0") == "requests"

    def test_name_with_marker(self):
        assert imp._parse_pep508('requests; python_version>="3.6"') == "requests"

    def test_name_with_parens(self):
        assert imp._parse_pep508("requests (>=2.0)") == "requests"

    def test_underscore_name(self):
        assert imp._parse_pep508("some_package>=1.0") == "some_package"

    def test_hyphen_name(self):
        assert imp._parse_pep508("some-package>=1.0") == "some-package"

    def test_empty_string_returns_none(self):
        assert imp._parse_pep508("") is None

    def test_name_with_dot(self):
        assert imp._parse_pep508("zope.interface>=4.0") == "zope.interface"


# ---------------------------------------------------------------------------
# _npm_canonical_name
# ---------------------------------------------------------------------------

class TestNpmCanonicalName:
    def test_simple_name(self):
        assert imp._npm_canonical_name("lodash") == "lodash"

    def test_scoped_package(self):
        assert imp._npm_canonical_name("@scope/pkg") == "scope__pkg"

    def test_scoped_with_hyphens(self):
        assert imp._npm_canonical_name("@my-org/my-pkg") == "my-org__my-pkg"

    def test_no_at_sign(self):
        assert imp._npm_canonical_name("express") == "express"


# ---------------------------------------------------------------------------
# import_pypi
# ---------------------------------------------------------------------------

def _pypi_response(name="requests", version="2.31.0", deps=None, license_="Apache-2.0"):
    return {
        "info": {
            "name": name,
            "version": version,
            "summary": f"{name} library",
            "license": license_,
            "home_page": f"https://{name}.example.com",
            "project_urls": {},
            "requires_dist": deps if deps is not None else ["certifi>=2017.4.17", "charset-normalizer<4"],
            "requires_python": ">=3.7",
            "classifiers": ["License :: OSI Approved :: Apache Software License"],
        },
        "urls": [{
            "packagetype": "sdist",
            "url": f"https://files.pythonhosted.org/packages/{name}-{version}.tar.gz",
            "digests": {"sha256": "abc123"},
        }],
    }


class TestImportPypi:
    def test_creates_json_file(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response()):
            count = imp.import_pypi(["requests"], tmp_path)
        assert count == 1
        assert (tmp_path / "requests.json").exists()

    def test_record_has_correct_ecosystem(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response()):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["identity"]["ecosystem"] == "pypi"

    def test_canonical_name_lowercased(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(name="Requests")):
            imp.import_pypi(["Requests"], tmp_path)
        assert (tmp_path / "requests.json").exists()
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["identity"]["canonical_name"] == "requests"

    def test_underscore_normalized_to_hyphen(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(name="some_package")):
            imp.import_pypi(["some_package"], tmp_path)
        assert (tmp_path / "some-package.json").exists()

    def test_runtime_deps_extracted(self, tmp_path):
        deps = ["certifi>=2017.4.17", "idna<4,>=2.5"]
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(deps=deps)):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        runtime = rec["dependencies"]["runtime"]
        assert "certifi" in runtime
        assert "idna" in runtime

    def test_optional_extras_skipped(self, tmp_path):
        deps = ["requests>=2.0", 'PySocks!=1.5.7; extra == "socks"']
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(deps=deps)):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        runtime = rec["dependencies"]["runtime"]
        assert "pysocks" not in [d.lower() for d in runtime]

    def test_source_url_and_sha256(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response()):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["sources"][0]["sha256"] == "abc123"
        assert "pythonhosted.org" in rec["sources"][0]["url"]

    def test_fetch_failure_skipped(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=None):
            count = imp.import_pypi(["does-not-exist"], tmp_path)
        assert count == 0
        assert not list(tmp_path.iterdir())

    def test_build_system_is_pypi(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response()):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["build"]["system_kind"] == "pypi"

    def test_build_deps_include_setuptools(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response()):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert "setuptools" in rec["dependencies"]["build"]

    def test_no_requires_dist_gives_empty_runtime(self, tmp_path):
        data = _pypi_response()
        data["info"]["requires_dist"] = None
        with patch.object(imp, "_fetch_json", return_value=data):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["dependencies"]["runtime"] == []

    def test_multiple_packages(self, tmp_path):
        with patch.object(imp, "_fetch_json", side_effect=[
            _pypi_response("requests"), _pypi_response("flask"),
        ]):
            count = imp.import_pypi(["requests", "flask"], tmp_path)
        assert count == 2
        assert (tmp_path / "requests.json").exists()
        assert (tmp_path / "flask.json").exists()

    def test_pypi_extension_has_requires_python(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_pypi_response()):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["extensions"]["pypi"]["requires_python"] == ">=3.7"

    def test_no_duplicate_runtime_deps(self, tmp_path):
        deps = ["certifi>=2017.4.17", "certifi<5"]  # same name, two constraints
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(deps=deps)):
            imp.import_pypi(["requests"], tmp_path)
        rec = json.loads((tmp_path / "requests.json").read_text())
        assert rec["dependencies"]["runtime"].count("certifi") == 1


# ---------------------------------------------------------------------------
# import_npm
# ---------------------------------------------------------------------------

def _npm_response(name="lodash", version="4.17.21", deps=None, dev_deps=None, peer_deps=None):
    return {
        "name": name,
        "dist-tags": {"latest": version},
        "versions": {
            version: {
                "name": name,
                "version": version,
                "description": f"{name} utility library",
                "license": "MIT",
                "homepage": f"https://{name}.example.com",
                "dependencies": deps or {"semver": "^7.0.0"},
                "devDependencies": dev_deps or {"jest": "^29.0.0"},
                "peerDependencies": peer_deps or {},
                "dist": {
                    "tarball": f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz",
                    "integrity": "sha512-abc123",
                },
                "keywords": ["utility", "lodash"],
                "engines": {"node": ">=12"},
            }
        },
    }


class TestImportNpm:
    def test_creates_json_file(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            count = imp.import_npm(["lodash"], tmp_path)
        assert count == 1
        assert (tmp_path / "lodash.json").exists()

    def test_record_has_correct_ecosystem(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert rec["identity"]["ecosystem"] == "npm"

    def test_scoped_package_filename(self, tmp_path):
        resp = _npm_response(name="@scope/pkg", version="1.0.0")
        with patch.object(imp, "_fetch_json", return_value=resp):
            imp.import_npm(["@scope/pkg"], tmp_path)
        assert (tmp_path / "scope__pkg.json").exists()

    def test_runtime_deps_from_dependencies(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert "semver" in rec["dependencies"]["runtime"]

    def test_build_deps_from_dev_dependencies(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert "jest" in rec["dependencies"]["build"]

    def test_host_deps_from_peer_dependencies(self, tmp_path):
        resp = _npm_response(peer_deps={"react": ">=17"})
        with patch.object(imp, "_fetch_json", return_value=resp):
            imp.import_npm(["some-ui-lib"], tmp_path)
        rec = json.loads((tmp_path / "some-ui-lib.json").read_text())
        assert "react" in rec["dependencies"]["host"]

    def test_source_url_and_integrity(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert "registry.npmjs.org" in rec["sources"][0]["url"]
        assert rec["sources"][0]["integrity"] == "sha512-abc123"

    def test_fetch_failure_skipped(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=None):
            count = imp.import_npm(["does-not-exist"], tmp_path)
        assert count == 0

    def test_build_system_is_npm(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert rec["build"]["system_kind"] == "npm"

    def test_license_string(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert rec["descriptive"]["license"] == ["MIT"]

    def test_dict_license_extracted(self, tmp_path):
        resp = _npm_response()
        resp["versions"]["4.17.21"]["license"] = {"type": "MIT", "url": "..."}
        with patch.object(imp, "_fetch_json", return_value=resp):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert rec["descriptive"]["license"] == ["MIT"]

    def test_multiple_packages(self, tmp_path):
        with patch.object(imp, "_fetch_json", side_effect=[
            _npm_response("lodash"), _npm_response("axios"),
        ]):
            count = imp.import_npm(["lodash", "axios"], tmp_path)
        assert count == 2

    def test_npm_extension_has_engines(self, tmp_path):
        with patch.object(imp, "_fetch_json", return_value=_npm_response()):
            imp.import_npm(["lodash"], tmp_path)
        rec = json.loads((tmp_path / "lodash.json").read_text())
        assert rec["extensions"]["npm"]["engines"] == {"node": ">=12"}

    def test_ecosystem_id_preserves_original_name(self, tmp_path):
        resp = _npm_response(name="@scope/pkg", version="1.0.0")
        with patch.object(imp, "_fetch_json", return_value=resp):
            imp.import_npm(["@scope/pkg"], tmp_path)
        rec = json.loads((tmp_path / "scope__pkg.json").read_text())
        assert rec["identity"]["ecosystem_id"] == "@scope/pkg"

    def test_no_dist_tags_falls_back_to_last_version(self, tmp_path):
        resp = _npm_response()
        resp["dist-tags"] = {}
        with patch.object(imp, "_fetch_json", return_value=resp):
            count = imp.import_npm(["lodash"], tmp_path)
        assert count == 1


# ---------------------------------------------------------------------------
# seed_from_ports (PyPI extraction from freebsd_ports snapshot)
# ---------------------------------------------------------------------------

def _write_port_record(directory: Path, name: str, eco_id: str,
                       pypi_source: bool = True) -> None:
    rec = {
        "identity": {
            "canonical_name": name,
            "ecosystem": "freebsd_ports",
            "ecosystem_id": eco_id,
        },
        "sources": [
            {"type": "master_sites", "url": "PYPI" if pypi_source else "https://example.com"},
        ],
        "dependencies": {},
        "provenance": {"confidence": 0.8},
    }
    (directory / f"{eco_id.replace('/', '__')}.json").write_text(
        json.dumps(rec), encoding="utf-8"
    )


class TestSeedFromPorts:
    def test_finds_py_ports_with_pypi_site(self, tmp_path):
        _write_port_record(tmp_path, "requests", "devel/py-requests", pypi_source=True)
        names = seed_pypi(tmp_path)
        assert "requests" in names

    def test_skips_non_py_ports(self, tmp_path):
        _write_port_record(tmp_path, "curl", "ftp/curl", pypi_source=True)
        names = seed_pypi(tmp_path)
        assert "curl" not in names

    def test_skips_py_ports_without_pypi_site(self, tmp_path):
        _write_port_record(tmp_path, "mylib", "devel/py-mylib", pypi_source=False)
        names = seed_pypi(tmp_path)
        assert "mylib" not in names

    def test_deduplicates_names(self, tmp_path):
        _write_port_record(tmp_path, "requests", "devel/py-requests", pypi_source=True)
        # Write a second record with same canonical name (shouldn't happen but guard)
        rec2 = {
            "identity": {"canonical_name": "requests", "ecosystem": "freebsd_ports",
                         "ecosystem_id": "net/py-requests-alt"},
            "sources": [{"type": "master_sites", "url": "PYPI"}],
            "dependencies": {}, "provenance": {"confidence": 0.8},
        }
        (tmp_path / "net__py-requests-alt.json").write_text(json.dumps(rec2))
        names = seed_pypi(tmp_path)
        assert names.count("requests") == 1

    def test_returns_sorted_list(self, tmp_path):
        _write_port_record(tmp_path, "zlib-ng", "devel/py-zlib-ng", pypi_source=True)
        _write_port_record(tmp_path, "attrs", "devel/py-attrs", pypi_source=True)
        names = seed_pypi(tmp_path)
        assert names == sorted(names)

    def test_skips_manifest(self, tmp_path):
        (tmp_path / "manifest.json").write_text('{"type":"manifest"}')
        _write_port_record(tmp_path, "requests", "devel/py-requests", pypi_source=True)
        names = seed_pypi(tmp_path)
        assert "manifest" not in names

    def test_skips_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json")
        names = seed_pypi(tmp_path)
        assert names == []

    def test_normalizes_underscores_to_hyphens(self, tmp_path):
        _write_port_record(tmp_path, "some_package", "devel/py-some_package", pypi_source=True)
        names = seed_pypi(tmp_path)
        assert "some-package" in names
        assert "some_package" not in names
