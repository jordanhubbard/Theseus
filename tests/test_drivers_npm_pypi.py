"""
tests/test_drivers_npm_pypi.py

Tests for theseus/drivers/pypi.py and theseus/drivers/npm.py.
"""
from __future__ import annotations

import json

import pytest

from theseus.drivers.pypi import render as render_pypi
from theseus.drivers.npm import render as render_npm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pypi_record(name="requests", version="2.31.0", deps=None,
                 license_="Apache-2.0", homepage="https://requests.example.com",
                 requires_python=">=3.7", source_url="https://files.example.com/r.tar.gz"):
    return {
        "identity": {
            "canonical_name": name.lower().replace("_", "-"),
            "canonical_id": f"pkg:{name}",
            "version": version,
            "ecosystem": "pypi",
            "ecosystem_id": name,
        },
        "descriptive": {
            "summary": f"{name} library",
            "homepage": homepage,
            "license": [license_] if license_ else [],
            "categories": ["python"],
            "maintainers": [],
        },
        "conflicts": [],
        "sources": [{"type": "sdist", "url": source_url, "sha256": "abc123"}] if source_url else [],
        "dependencies": {
            "build": ["setuptools", "wheel"],
            "host": [],
            "runtime": deps if deps is not None else ["certifi", "idna"],
            "test": [],
        },
        "build": {"system_kind": "pypi", "configure_args": [], "make_args": []},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": [],
        "tests": {},
        "provenance": {"generated_by": "test", "imported_at": "2026-01-01",
                       "source_path": "", "source_repo_commit": None,
                       "confidence": 0.9, "unmapped": [], "warnings": []},
        "extensions": {"pypi": {"requires_python": requires_python, "classifiers": []}},
    }


def _npm_record(name="lodash", version="4.17.21", runtime_deps=None,
                build_deps=None, peer_deps=None, license_="MIT",
                homepage="https://lodash.com"):
    return {
        "identity": {
            "canonical_name": name,
            "canonical_id": f"pkg:{name}",
            "version": version,
            "ecosystem": "npm",
            "ecosystem_id": name,
        },
        "descriptive": {
            "summary": f"{name} utility",
            "homepage": homepage,
            "license": [license_] if license_ else [],
            "categories": ["javascript"],
            "maintainers": [],
        },
        "conflicts": [],
        "sources": [{"type": "tarball",
                     "url": f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz",
                     "integrity": "sha512-abc"}],
        "dependencies": {
            "build": build_deps if build_deps is not None else ["jest"],
            "host": peer_deps if peer_deps is not None else [],
            "runtime": runtime_deps if runtime_deps is not None else ["semver"],
            "test": [],
        },
        "build": {"system_kind": "npm", "configure_args": [], "make_args": []},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": [],
        "tests": {},
        "provenance": {"generated_by": "test", "imported_at": "2026-01-01",
                       "source_path": "", "source_repo_commit": None,
                       "confidence": 0.85, "unmapped": [], "warnings": []},
        "extensions": {"npm": {"engines": {"node": ">=12"}, "keywords": ["utility"]}},
    }


# ---------------------------------------------------------------------------
# PyPI driver
# ---------------------------------------------------------------------------

class TestPypiDriver:
    def test_returns_requirements_txt_and_pyproject_toml(self):
        out = render_pypi(_pypi_record())
        assert "requirements.txt" in out
        assert "pyproject.toml" in out

    def test_requirements_txt_has_pinned_package(self):
        out = render_pypi(_pypi_record(name="requests", version="2.31.0"))
        assert "requests==2.31.0" in out["requirements.txt"]

    def test_requirements_txt_includes_runtime_deps(self):
        out = render_pypi(_pypi_record(deps=["certifi", "idna"]))
        lines = out["requirements.txt"].splitlines()
        assert "certifi" in lines
        assert "idna" in lines

    def test_requirements_txt_no_version_when_empty(self):
        out = render_pypi(_pypi_record(version=""))
        assert "==" not in out["requirements.txt"].splitlines()[0]

    def test_pyproject_toml_has_name(self):
        out = render_pypi(_pypi_record(name="requests"))
        assert 'name = "requests"' in out["pyproject.toml"]

    def test_pyproject_toml_has_version(self):
        out = render_pypi(_pypi_record(version="2.31.0"))
        assert 'version = "2.31.0"' in out["pyproject.toml"]

    def test_pyproject_toml_has_requires_python(self):
        out = render_pypi(_pypi_record(requires_python=">=3.8"))
        assert 'requires-python = ">=3.8"' in out["pyproject.toml"]

    def test_pyproject_toml_has_license(self):
        out = render_pypi(_pypi_record(license_="MIT"))
        assert "MIT" in out["pyproject.toml"]

    def test_pyproject_toml_has_dependencies(self):
        out = render_pypi(_pypi_record(deps=["certifi", "idna"]))
        toml = out["pyproject.toml"]
        assert '"certifi"' in toml
        assert '"idna"' in toml

    def test_pyproject_toml_has_homepage(self):
        out = render_pypi(_pypi_record(homepage="https://requests.readthedocs.io"))
        assert "https://requests.readthedocs.io" in out["pyproject.toml"]

    def test_pyproject_toml_has_build_system(self):
        out = render_pypi(_pypi_record())
        assert "[build-system]" in out["pyproject.toml"]
        assert "setuptools" in out["pyproject.toml"]

    def test_uses_ecosystem_id_name(self):
        rec = _pypi_record(name="Requests")  # ecosystem_id preserves case
        out = render_pypi(rec)
        assert "Requests==" in out["requirements.txt"]

    def test_no_runtime_deps_skips_section(self):
        out = render_pypi(_pypi_record(deps=[]))
        assert "dependencies" not in out["pyproject.toml"]

    def test_source_url_as_comment(self):
        out = render_pypi(_pypi_record(source_url="https://files.example.com/r.tar.gz"))
        assert "https://files.example.com/r.tar.gz" in out["pyproject.toml"]

    def test_no_source_url_no_comment(self):
        out = render_pypi(_pypi_record(source_url=""))
        assert "# Source:" not in out["pyproject.toml"]


# ---------------------------------------------------------------------------
# npm driver
# ---------------------------------------------------------------------------

class TestNpmDriver:
    def test_returns_package_json_and_npmrc(self):
        out = render_npm(_npm_record())
        assert "package.json" in out
        assert ".npmrc" in out

    def test_package_json_valid_json(self):
        out = render_npm(_npm_record())
        parsed = json.loads(out["package.json"])
        assert isinstance(parsed, dict)

    def test_package_json_has_dependency(self):
        out = render_npm(_npm_record(name="lodash", version="4.17.21"))
        parsed = json.loads(out["package.json"])
        assert "lodash" in parsed["dependencies"]
        assert parsed["dependencies"]["lodash"] == "4.17.21"

    def test_scoped_package_in_dependencies(self):
        out = render_npm(_npm_record(name="@babel/core", version="7.0.0"))
        parsed = json.loads(out["package.json"])
        assert "@babel/core" in parsed["dependencies"]

    def test_package_json_is_private(self):
        out = render_npm(_npm_record())
        parsed = json.loads(out["package.json"])
        assert parsed.get("private") is True

    def test_package_json_has_license(self):
        out = render_npm(_npm_record(license_="MIT"))
        parsed = json.loads(out["package.json"])
        assert parsed["license"] == "MIT"

    def test_package_json_has_homepage(self):
        out = render_npm(_npm_record(homepage="https://lodash.com"))
        parsed = json.loads(out["package.json"])
        assert parsed.get("homepage") == "https://lodash.com"

    def test_no_version_uses_wildcard(self):
        out = render_npm(_npm_record(version=""))
        parsed = json.loads(out["package.json"])
        dep_version = list(parsed["dependencies"].values())[0]
        assert dep_version == "*"

    def test_npmrc_has_registry(self):
        out = render_npm(_npm_record())
        assert "registry.npmjs.org" in out[".npmrc"]

    def test_npmrc_disables_audit(self):
        out = render_npm(_npm_record())
        assert "audit=false" in out[".npmrc"]

    def test_no_license_uses_unlicensed(self):
        out = render_npm(_npm_record(license_=""))
        parsed = json.loads(out["package.json"])
        assert parsed["license"] == "UNLICENSED"

    def test_safe_name_for_scoped_packages(self):
        out = render_npm(_npm_record(name="@scope/my-pkg"))
        parsed = json.loads(out["package.json"])
        # install wrapper name should not contain @
        assert not parsed["name"].startswith("@")
