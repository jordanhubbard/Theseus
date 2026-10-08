"""Tests for corpus-first recipe refresh (make refresh / make reingest)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import theseus.importer as imp
import theseus.refresh as refresh


def _pypi_response(name="requests", version="2.31.0"):
    return {
        "info": {
            "name": name,
            "version": version,
            "summary": "%s library" % name,
            "license": "Apache-2.0",
            "home_page": "https://%s.example.com" % name,
            "project_urls": {},
            "author_email": "author@example.com",
            "maintainer_email": "maintainer@example.com",
            "requires_dist": ["certifi>=2017.4.17"],
            "requires_python": ">=3.7",
            "classifiers": ["License :: OSI Approved :: Apache Software License"],
        },
        "urls": [{
            "packagetype": "sdist",
            "url": "https://files.pythonhosted.org/packages/%s-%s.tar.gz" % (name, version),
            "digests": {"sha256": "abc123"},
        }],
    }


REPO_ROOT = Path(__file__).resolve().parent.parent
NIX_PKG = """\
{ lib, stdenv, fetchurl }:
stdenv.mkDerivation rec {
  pname = "mylib";
  version = "9.9.9";
  src = fetchurl {
    url = "https://example.com/mylib-9.9.9.tar.gz";
    hash = "sha256-abc";
  };
  meta = with lib; {
    description = "A refreshed library";
    homepage = "https://example.com/mylib";
    license = licenses.mit;
  };
}
"""

PORTS_MAKEFILE = """\
PORTNAME=\tmylib
PORTVERSION=\t8.8.8
CATEGORIES=\tdevel
COMMENT=\tRefreshed port
WWW=\thttps://example.com/mylib
LICENSE=\tMIT
MAINTAINER=\ttest@example.com
"""


def _recipe(name, eco="pypi", version="1.0", **kwargs):
    rec = {
        "schema_version": "0.2",
        "identity": {
            "canonical_name": name,
            "canonical_id": "pkg:%s" % name,
            "version": version,
            "ecosystem": eco,
            "ecosystem_id": kwargs.pop("ecosystem_id", name),
        },
        "descriptive": {
            "summary": kwargs.pop("summary", "%s library" % name),
            "homepage": "https://example.invalid/%s" % name,
            "license": kwargs.pop("license", ["MIT"]),
            "maintainers": [],
        },
        "sources": kwargs.pop("sources", []),
        "dependencies": kwargs.pop(
            "dependencies",
            {"build": [], "host": [], "runtime": [], "test": []},
        ),
        "provenance": {
            "confidence": 0.9,
            "generated_by": "test",
            "imported_at": "2026-03-29T00:00:00+00:00",
            "source_path": kwargs.pop("source_path", "https://pypi.org/pypi/%s/json" % name),
            "source_repo_commit": None,
            "warnings": [],
            "unmapped": [],
        },
        "extensions": kwargs.pop("extensions", {"merged_from": [eco]}),
        "conflicts": [],
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "patches": [],
        "tests": {},
        "build": {"system_kind": eco, "configure_args": [], "make_args": []},
    }
    rec.update(kwargs)
    return rec


def _write(path: Path, rec: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


class TestClassify:
    def test_merged_from_wins(self):
        rec = _recipe("zlib", eco="freebsd_ports", extensions={"merged_from": ["freebsd_ports", "nixpkgs"]})
        assert refresh.recipe_ecosystems(rec) == ["freebsd_ports", "nixpkgs"]

    def test_identity_fallback(self):
        rec = _recipe("requests", eco="pypi", extensions={})
        assert refresh.recipe_ecosystems(rec) == ["pypi"]

    def test_ports_source_path_from_ecosystem_id(self):
        rec = _recipe(
            "zlib",
            eco="freebsd_ports",
            ecosystem_id="archivers/zlib",
            source_path="archivers/zlib",
        )
        assert refresh.ports_source_path(rec) == "archivers/zlib"

    def test_ports_ignores_nix_paths(self):
        rec = _recipe(
            "bzip2",
            eco="nixpkgs",
            ecosystem_id="bzip2",
            source_path="pkgs/tools/compression/bzip2/default.nix",
        )
        assert refresh.ports_source_path(rec) is None

    def test_nix_candidates_include_by_name(self):
        rec = _recipe("curl", eco="nixpkgs", ecosystem_id="curl", source_path="curl")
        cands = refresh.nixpkgs_source_candidates(rec)
        assert "pkgs/by-name/cu/curl/package.nix" in cands

    def test_masterdir_sibling(self):
        got = imp.masterdir_source_path("${.CURDIR}/../linux-c7-zlib", "devel/linux-c7-zlib-devel")
        assert got == "devel/linux-c7-zlib"


class TestRefreshPypi:
    def test_updates_version(self, tmp_path):
        specs = tmp_path / "specs"
        _write(specs / "requests.json", _recipe("requests", version="2.0.0"))
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(version="2.33.1")):
            report = refresh.refresh_recipes(
                specs, allow_remote=False, jobs=1, ecosystems=["pypi"]
            )
        rec = json.loads((specs / "requests.json").read_text())
        assert rec["identity"]["version"] == "2.33.1"
        assert rec["provenance"]["generated_by"] == "refresh_recipes.py"
        assert report["summary"]["refreshed"] == 1

    def test_keeps_license_when_new_parse_omits_it(self, tmp_path):
        specs = tmp_path / "specs"
        nix = tmp_path / "nixpkgs"
        dest = nix / "pkgs" / "by-name" / "my" / "mylib" / "package.nix"
        dest.parent.mkdir(parents=True)
        dest.write_text(
            '{ stdenv }:\nstdenv.mkDerivation rec {\n  pname = "mylib";\n  version = "9.9.9";\n}\n'
        )
        rec = _recipe(
            "mylib",
            eco="nixpkgs",
            version="1.0",
            license=["Zlib"],
            ecosystem_id="mylib",
            source_path="pkgs/by-name/my/mylib/package.nix",
            extensions={"merged_from": ["nixpkgs"]},
        )
        _write(specs / "mylib.json", rec)
        refresh.refresh_recipes(
            specs, nixpkgs_root=nix, allow_remote=False, jobs=1, ecosystems=["nixpkgs"]
        )
        out = json.loads((specs / "mylib.json").read_text())
        assert out["identity"]["version"] == "9.9.9"
        assert out["descriptive"]["license"] == ["Zlib"]

    def test_failed_fetch_leaves_original(self, tmp_path):
        specs = tmp_path / "specs"
        _write(specs / "requests.json", _recipe("requests", version="2.0.0"))
        with patch.object(imp, "pypi_record", return_value=None):
            report = refresh.refresh_recipes(
                specs, allow_remote=False, jobs=1, ecosystems=["pypi"]
            )
        rec = json.loads((specs / "requests.json").read_text())
        assert rec["identity"]["version"] == "2.0.0"
        assert rec["provenance"]["generated_by"] == "test"
        assert report["summary"]["failed"] == 1

    def test_dry_run_does_not_write(self, tmp_path):
        specs = tmp_path / "specs"
        _write(specs / "requests.json", _recipe("requests", version="2.0.0"))
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(version="9.9.9")):
            report = refresh.refresh_recipes(
                specs, allow_remote=False, jobs=1, ecosystems=["pypi"], dry_run=True
            )
        rec = json.loads((specs / "requests.json").read_text())
        assert rec["identity"]["version"] == "2.0.0"
        assert report["summary"]["dry_run"] == 1


class TestRefreshTrees:
    def test_local_nixpkgs(self, tmp_path):
        specs = tmp_path / "specs"
        nix = tmp_path / "nixpkgs"
        dest = nix / "pkgs" / "by-name" / "my" / "mylib" / "package.nix"
        dest.parent.mkdir(parents=True)
        dest.write_text(NIX_PKG)
        rec = _recipe(
            "mylib",
            eco="nixpkgs",
            version="1.0",
            ecosystem_id="mylib",
            source_path="pkgs/by-name/my/mylib/package.nix",
            extensions={"merged_from": ["nixpkgs"]},
        )
        _write(specs / "mylib.json", rec)
        report = refresh.refresh_recipes(
            specs, nixpkgs_root=nix, allow_remote=False, jobs=1, ecosystems=["nixpkgs"]
        )
        out = json.loads((specs / "mylib.json").read_text())
        assert out["identity"]["version"] == "9.9.9"
        assert out["identity"]["canonical_name"] == "mylib"
        assert report["summary"]["refreshed"] == 1

    def test_local_ports_preserves_canonical_name(self, tmp_path):
        specs = tmp_path / "specs"
        ports = tmp_path / "ports"
        makefile = ports / "devel" / "mylib-slave" / "Makefile"
        makefile.parent.mkdir(parents=True)
        makefile.write_text(PORTS_MAKEFILE)
        rec = _recipe(
            "mylib",
            eco="freebsd_ports",
            version="1.0",
            ecosystem_id="devel/mylib-slave",
            source_path="devel/mylib-slave",
            extensions={"merged_from": ["freebsd_ports"]},
        )
        _write(specs / "mylib.json", rec)
        refresh.refresh_recipes(
            specs, ports_root=ports, allow_remote=False, jobs=1, ecosystems=["freebsd_ports"]
        )
        out = json.loads((specs / "mylib.json").read_text())
        assert out["identity"]["canonical_name"] == "mylib"
        assert out["identity"]["version"] == "8.8.8"

    def test_follows_nix_override_alias(self, tmp_path):
        specs = tmp_path / "specs"
        rec = _recipe(
            "curl",
            eco="nixpkgs",
            version="1.0",
            ecosystem_id="curl",
            source_path="curl",
            extensions={"merged_from": ["nixpkgs"]},
        )
        _write(specs / "curl.json", rec)
        alias = "{\n  curlMinimal,\n  ...\n}:\ncurlMinimal.override { http3Support = true; }\n"
        files = {
            "pkgs/by-name/cu/curl/package.nix": alias,
            "pkgs/by-name/cu/curlMinimal/package.nix": NIX_PKG.replace("mylib", "curl"),
        }

        def fake_text(url, timeout=15):
            for path, body in files.items():
                if url.endswith(path):
                    return body
            return None

        with patch.object(refresh, "github_ref_sha", return_value="abc"):
            with patch.object(imp, "_fetch_text", side_effect=fake_text):
                refresh.refresh_recipes(
                    specs, allow_remote=True, jobs=1, ecosystems=["nixpkgs"]
                )
        out = json.loads((specs / "curl.json").read_text())
        assert out["identity"]["canonical_name"] == "curl"
        assert out["identity"]["version"] == "9.9.9"

    def test_setup_hook_parses(self, tmp_path):
        nix = tmp_path / "nixpkgs" / "pkgs" / "by-name" / "in" / "installShellFiles"
        nix.mkdir(parents=True)
        (nix / "package.nix").write_text(
            '{\n  makeSetupHook,\n  lib,\n}:\nmakeSetupHook {\n  name = "install-shell-files";\n'
            '  meta.license = lib.licenses.mit;\n} ./setup-hook.sh\n'
        )
        rec = imp.parse_nix_file(nix / "package.nix", tmp_path / "nixpkgs")
        assert rec is not None
        assert rec["identity"]["canonical_name"] == "install-shell-files"

    def test_remote_nixpkgs_fallback(self, tmp_path):
        specs = tmp_path / "specs"
        rec = _recipe(
            "mylib",
            eco="nixpkgs",
            version="1.0",
            ecosystem_id="mylib",
            source_path="curl",
            extensions={"merged_from": ["nixpkgs"]},
        )
        _write(specs / "mylib.json", rec)

        def fake_text(url, timeout=15):
            if url.endswith("pkgs/by-name/my/mylib/package.nix"):
                return NIX_PKG
            return None

        with patch.object(refresh, "github_ref_sha", return_value="abc123"):
            with patch.object(imp, "_fetch_text", side_effect=fake_text):
                report = refresh.refresh_recipes(
                    specs, allow_remote=True, jobs=1, ecosystems=["nixpkgs"]
                )
        out = json.loads((specs / "mylib.json").read_text())
        assert out["identity"]["version"] == "9.9.9"
        assert out["provenance"]["source_repo_commit"] == "abc123"
        assert report["summary"]["refreshed"] == 1

    def test_remote_ports_fallback(self, tmp_path):
        specs = tmp_path / "specs"
        rec = _recipe(
            "mylib",
            eco="freebsd_ports",
            version="1.0",
            ecosystem_id="devel/mylib",
            source_path="devel/mylib",
            extensions={"merged_from": ["freebsd_ports"]},
        )
        _write(specs / "mylib.json", rec)

        def fake_text(url, timeout=15):
            if url.endswith("devel/mylib/Makefile"):
                return PORTS_MAKEFILE
            return None

        with patch.object(refresh, "github_ref_sha", return_value="def456"):
            with patch.object(imp, "_fetch_text", side_effect=fake_text):
                refresh.refresh_recipes(
                    specs, allow_remote=True, jobs=1, ecosystems=["freebsd_ports"]
                )
        out = json.loads((specs / "mylib.json").read_text())
        assert out["identity"]["version"] == "8.8.8"
        assert out["provenance"]["source_repo_commit"] == "def456"

    def test_partial_keeps_failed_ecosystem_data(self, tmp_path):
        specs = tmp_path / "specs"
        rec = _recipe(
            "zlib",
            eco="freebsd_ports",
            version="1.2.7",
            ecosystem_id="archivers/zlib",
            source_path="archivers/zlib",
            extensions={"merged_from": ["freebsd_ports", "nixpkgs"]},
            dependencies={"build": [], "host": [], "runtime": ["old-nix-dep"], "test": []},
        )
        _write(specs / "zlib.json", rec)
        ports = tmp_path / "ports"
        makefile = ports / "archivers" / "zlib" / "Makefile"
        makefile.parent.mkdir(parents=True)
        makefile.write_text(PORTS_MAKEFILE.replace("mylib", "zlib"))
        report = refresh.refresh_recipes(
            specs,
            ports_root=ports,
            allow_remote=False,
            jobs=1,
            ecosystems=["freebsd_ports", "nixpkgs"],
        )
        out = json.loads((specs / "zlib.json").read_text())
        assert out["identity"]["version"] == "8.8.8"
        assert "old-nix-dep" in out["dependencies"]["runtime"]
        assert report["summary"]["partial"] == 1


def _load_cli():
    path = REPO_ROOT / "tools" / "refresh_recipes.py"
    spec = importlib.util.spec_from_file_location("refresh_recipes_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCli:
    def test_help(self):
        cli = _load_cli()
        with pytest.raises(SystemExit) as exc:
            cli.main(["--help"])
        assert exc.value.code == 0

    def test_dry_run_json(self, tmp_path):
        cli = _load_cli()
        specs = tmp_path / "specs"
        _write(specs / "requests.json", _recipe("requests", version="2.0.0"))
        with patch.object(imp, "_fetch_json", return_value=_pypi_response(version="3.0.0")):
            code = cli.main([
                "--specs", str(specs),
                "--no-remote",
                "--jobs", "1",
                "--ecosystems", "pypi",
                "--dry-run",
                "--json",
            ])
        assert code == 0
        rec = json.loads((specs / "requests.json").read_text())
        assert rec["identity"]["version"] == "2.0.0"


class TestMakefileContract:
    def test_refresh_targets_exist(self):
        text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        assert "refresh-recipes:" in text
        assert "refresh:" in text
        assert "reingest:" in text
