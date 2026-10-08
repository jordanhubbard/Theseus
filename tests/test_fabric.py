"""Tests for the git-backed OSS knowledge fabric."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from theseus import fabric as fab


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "fingerprint.schema.json"


def _recipe(name, eco="pypi", version="1.0", **kwargs):
    descriptive = {
        "summary": kwargs.pop("summary", "%s library" % name),
        "homepage": kwargs.pop("homepage", "https://example.invalid/%s" % name),
        "license": kwargs.pop("license", ["MIT"]),
    }
    identity = {
        "canonical_name": name,
        "canonical_id": "pkg:%s" % name,
        "version": version,
        "ecosystem": eco,
        "ecosystem_id": name,
    }
    rec = {
        "schema_version": "0.2",
        "identity": identity,
        "descriptive": descriptive,
        "sources": kwargs.pop("sources", []),
        "dependencies": kwargs.pop(
            "dependencies",
            {"build": [], "host": [], "runtime": [], "test": []},
        ),
        "provenance": kwargs.pop(
            "provenance",
            {
                "confidence": 0.9,
                "generated_by": "test",
                "imported_at": "2026-10-07T00:00:00+00:00",
                "warnings": [],
            },
        ),
        "extensions": kwargs.pop("extensions", {}),
    }
    rec.update(kwargs)
    return rec


def _write_recipe(path: Path, **kwargs):
    rec = _recipe(**kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec), encoding="utf-8")
    return rec


class TestSchema:
    def test_schema_is_valid_json(self):
        data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert data["title"] == "OSS Package Fingerprint"
        assert data["properties"]["kind"]["const"] == "oss_fingerprint"

    def test_required_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        required = set(schema["required"])
        assert required >= {
            "schema_version",
            "kind",
            "identity",
            "license",
            "depends_on",
            "provenance",
        }


class TestNames:
    def test_slug_keeps_dots(self):
        assert fab.package_filename("zope.interface") == "zope.interface.json"

    def test_slug_rewrites_unsafe(self):
        assert fab.package_filename("foo/bar") == "foo_bar.json"

    def test_normalize_name_hyphenates(self):
        assert fab.normalize_name("Charset_Normalizer") == "charset-normalizer"


class TestExtractors:
    def test_pypi_source_repository_wins(self):
        rec = _recipe(
            "requests",
            homepage="https://requests.readthedocs.io",
            extensions={"pypi": {"source_repository": "https://github.com/psf/requests"}},
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/psf/requests"
        assert repo["confidence"] >= 0.9
        assert repo["source"] == "pypi.source_repository"

    def test_homepage_github_used_when_no_explicit_repo(self):
        rec = _recipe("semver", homepage="https://github.com/npm/node-semver#readme")
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/npm/node-semver"
        assert repo["source"] == "homepage"

    def test_noisy_github_sources_are_candidates_not_url(self):
        rec = _recipe(
            "zlib",
            homepage="https://zlib.net/",
            sources=[
                {"type": "homepage", "url": "https://github.com/brimworks/lua-zlib"},
                {"type": "homepage", "url": "https://github.com/ruby/zlib"},
            ],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] is None
        assert "https://github.com/brimworks/lua-zlib" in repo["candidates"]
        assert "https://github.com/ruby/zlib" in repo["candidates"]

    def test_license_alias_zlib(self):
        rec = _recipe("zlib", license=["ZLIB"])
        lic = fab.extract_license(rec)
        assert "Zlib" in lic["spdx"]
        assert lic["raw"] == ["ZLIB"]

    def test_license_alias_freebsd_tokens(self):
        rec = _recipe("foo", license=["BSD3CLAUSE", "GPLv2+"])
        lic = fab.extract_license(rec)
        assert "BSD-3-Clause" in lic["spdx"]
        assert "GPL-2.0-or-later" in lic["spdx"]

    def test_noisy_deps_dropped(self):
        rec = _recipe(
            "zlib",
            dependencies={
                "build": ["${LUA_PKGNAMEPREFIX}lzlib", "#"],
                "host": [],
                "runtime": ["openssl"],
                "test": ["lib/lua/5.*/zlib.so"],
            },
        )
        deps = fab.extract_depends_on(rec)
        names = [d["name"] for d in deps]
        assert names == ["openssl"]
        assert deps[0]["scope"] == "runtime"


class TestRecipeConversion:
    def test_round_trip_fields(self, tmp_path):
        rec = _recipe(
            "flask",
            dependencies={
                "build": ["setuptools"],
                "host": [],
                "runtime": ["click", "werkzeug"],
                "test": [],
            },
            extensions={"pypi": {"source_repository": "https://github.com/pallets/flask"}},
        )
        fp = fab.recipe_to_fingerprint(rec, "specs/flask.json", root=tmp_path)
        assert fp["kind"] == "oss_fingerprint"
        assert fp["identity"]["canonical_name"] == "flask"
        assert fp["repository"]["url"] == "https://github.com/pallets/flask"
        scopes = {(d["name"], d["scope"]) for d in fp["depends_on"]}
        assert ("click", "runtime") in scopes
        assert ("setuptools", "build") in scopes
        assert fp["provenance"]["sources"][0]["path"] == "specs/flask.json"

    def test_merge_unions_ecosystems_and_deps(self):
        a = fab.recipe_to_fingerprint(
            _recipe("zlib", eco="nixpkgs", license=["Zlib"], version="1.3.1"),
            "examples/nixpkgs/zlib.json",
        )
        b = fab.recipe_to_fingerprint(
            _recipe(
                "zlib",
                eco="freebsd_ports",
                license=["ZLIB"],
                version="1.2.7",
                dependencies={
                    "build": [],
                    "host": [],
                    "runtime": ["openssl"],
                    "test": [],
                },
            ),
            "examples/freebsd_ports/zlib.json",
        )
        merged = fab.merge_fingerprints([a, b])
        ecos = {e["ecosystem"] for e in merged["ecosystems"]}
        assert ecos == {"nixpkgs", "freebsd_ports"}
        assert any(d["name"] == "openssl" for d in merged["depends_on"])
        assert "Zlib" in merged["license"]["spdx"]

    def test_merge_prefers_clean_summary(self):
        a = fab.recipe_to_fingerprint(
            _recipe("zlib", summary="Zlib headers (Linux CentOS ${LINUX_DIST_VER})", homepage="http://zlib.net/"),
            "specs/zlib.json",
        )
        b = fab.recipe_to_fingerprint(
            _recipe(
                "zlib",
                eco="nixpkgs",
                summary="Compression library implementing the deflate algorithm",
                homepage="https://zlib.net/",
            ),
            "examples/nixpkgs/zlib.json",
        )
        merged = fab.merge_fingerprints([a, b])
        assert "${" not in (merged["summary"] or "")
        assert merged["homepage"].startswith("https://")


class TestIngestAndQuery:
    def test_ingest_and_bidirectional_deps(self, tmp_path):
        recipes = tmp_path / "recipes"
        _write_recipe(
            recipes / "requests.json",
            name="requests",
            license=["Apache-2.0"],
            extensions={"pypi": {"source_repository": "https://github.com/psf/requests"}},
            dependencies={
                "build": [],
                "host": [],
                "runtime": ["urllib3", "certifi"],
                "test": [],
            },
        )
        _write_recipe(
            recipes / "urllib3.json",
            name="urllib3",
            license=["MIT"],
            homepage="https://github.com/urllib3/urllib3",
        )
        _write_recipe(
            recipes / "certifi.json",
            name="certifi",
            license=["MPL-2.0"],
        )
        result = fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages")
        assert result["written"] == 3

        store = fab.FabricStore(tmp_path)
        req = store.get("requests")
        assert req["repository"]["url"] == "https://github.com/psf/requests"
        dep_names = {d["name"] for d in store.deps("requests", scope="runtime")}
        assert dep_names == {"urllib3", "certifi"}
        rdep_names = {d["name"] for d in store.rdeps("urllib3")}
        assert rdep_names == {"requests"}

        mit = store.query(license="MIT")
        assert { (r["identity"]["canonical_name"]) for r in mit } == {"urllib3"}

        stats = store.stats()
        assert stats["packages"] == 3
        assert stats["with_repository"] == 2
        assert stats["with_license"] == 3
        assert stats["missing_repository"] == 1

        errors = store.validate()
        assert errors == []

    def test_rdeps_for_name_not_in_store(self, tmp_path):
        recipes = tmp_path / "recipes"
        _write_recipe(
            recipes / "flask.json",
            name="flask",
            dependencies={
                "build": [],
                "host": [],
                "runtime": ["blinker"],
                "test": [],
            },
        )
        fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages")
        store = fab.FabricStore(tmp_path)
        assert store.get("blinker") is None
        assert [d["name"] for d in store.rdeps("blinker")] == ["flask"]

    def test_query_by_repo_and_ecosystem(self, tmp_path):
        recipes = tmp_path / "recipes"
        _write_recipe(
            recipes / "a.json",
            name="alpha",
            eco="pypi",
            extensions={"pypi": {"source_repository": "https://github.com/psf/alpha"}},
        )
        _write_recipe(
            recipes / "b.json",
            name="beta",
            eco="npm",
            homepage="https://github.com/npm/beta",
        )
        fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages")
        store = fab.FabricStore(tmp_path)
        assert len(store.query(repo="github.com/psf")) == 1
        assert len(store.query(ecosystem="npm")) == 1
        assert len(store.query(has_repo=True)) == 2
        assert len(store.query(missing_license=True)) == 0

    def test_validate_rejects_bad_kind(self):
        rec = fab.recipe_to_fingerprint(_recipe("x"), "specs/x.json")
        rec["kind"] = "nope"
        errors = fab.validate_fingerprint(rec, filename="x.json")
        assert any("kind" in e for e in errors)

    def test_ingest_skips_manifest_and_invalid(self, tmp_path):
        recipes = tmp_path / "recipes"
        recipes.mkdir()
        (recipes / "manifest.json").write_text('{"type":"manifest"}', encoding="utf-8")
        (recipes / "bad.json").write_text("not json", encoding="utf-8")
        _write_recipe(recipes / "ok.json", name="ok")
        result = fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages")
        assert result["written"] == 1
        assert result["skipped"] >= 1


class TestGitBackend:
    def _git(self, cwd: Path, *args):
        subprocess.run(
            ["git", "-C", str(cwd), "-c", "commit.gpgsign=false", *args],
            check=True,
            capture_output=True,
        )

    def test_query_at_revision(self, tmp_path):
        self._git(tmp_path, "init")
        self._git(tmp_path, "config", "user.email", "test@example.invalid")
        self._git(tmp_path, "config", "user.name", "Test")
        recipes = tmp_path / "recipes"
        _write_recipe(
            recipes / "alpha.json",
            name="alpha",
            license=["MIT"],
            homepage="https://github.com/ex/alpha",
        )
        fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages")
        self._git(tmp_path, "add", "fabric/packages/alpha.json")
        self._git(tmp_path, "commit", "-m", "fabric: add alpha")
        first = subprocess.check_output(
            ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
            text=True,
        ).strip()

        _write_recipe(
            recipes / "beta.json",
            name="beta",
            license=["Apache-2.0"],
        )
        fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages")
        self._git(tmp_path, "add", "fabric/packages")
        self._git(tmp_path, "commit", "-m", "fabric: add beta")

        at_first = fab.FabricStore(tmp_path, rev=first)
        assert at_first.get("alpha") is not None
        assert at_first.get("beta") is None
        assert len(at_first) == 1

        head = fab.FabricStore(tmp_path)
        assert head.get("beta") is not None
        assert len(head) == 2

        history = fab.git_history(tmp_path, "alpha")
        assert len(history) >= 1
        assert "add alpha" in history[0]["subject"] or any("alpha" in h["subject"] for h in history)


class TestCLI:
    def test_stats_json_after_subcommand(self):
        out = subprocess.check_output(
            [sys.executable, str(REPO_ROOT / "tools" / "fabric.py"), "stats", "--json"],
            cwd=str(REPO_ROOT),
            text=True,
        )
        stats = json.loads(out)
        assert stats["packages"] >= 200
        assert "with_repository" in stats

    def test_rdeps_json(self):
        out = subprocess.check_output(
            [sys.executable, str(REPO_ROOT / "tools" / "fabric.py"), "rdeps", "urllib3", "--json"],
            cwd=str(REPO_ROOT),
            text=True,
        )
        names = {row["name"] for row in json.loads(out)}
        assert "requests" in names


class TestCommittedFabric:
    @pytest.fixture(scope="class")
    def store(self):
        return fab.load_store(REPO_ROOT)

    def test_schema_file_committed(self):
        assert SCHEMA_PATH.is_file()

    def test_fabric_populated(self, store):
        assert len(store) >= 200

    def test_validate_committed(self, store):
        errors = store.validate()
        assert errors == []

    def test_zlib_fingerprint(self, store):
        rec = store.get("zlib")
        assert rec is not None
        assert rec["kind"] == "oss_fingerprint"
        assert rec["identity"]["canonical_name"] == "zlib"
        tokens = rec["license"]["spdx"] + rec["license"]["raw"]
        assert any("zlib" in t.lower() for t in tokens)

    def test_requests_depends_on_urllib3(self, store):
        names = {d["name"] for d in store.deps("requests", scope="runtime")}
        assert "urllib3" in names
        assert "certifi" in names

    def test_urllib3_has_requests_dependent(self, store):
        names = {d["name"] for d in store.rdeps("urllib3")}
        assert "requests" in names

    def test_flask_runtime_graph(self, store):
        names = {d["name"] for d in store.deps("flask", scope="runtime")}
        assert "werkzeug" in names
        assert "click" in names
        werk = {d["name"] for d in store.rdeps("werkzeug")}
        assert "flask" in werk

    def test_license_query_mit(self, store):
        matches = store.query(license="MIT")
        assert len(matches) >= 1
        assert all(
            any("mit" in t.lower() for t in (r.get("license") or {}).get("spdx", []))
            or any("mit" in t.lower() for t in (r.get("license") or {}).get("raw", []))
            for r in matches
        )

    def test_stats_cover_identity_fields(self, store):
        stats = store.stats()
        assert stats["packages"] == len(store)
        assert stats["with_license"] >= 1
        assert "pypi" in stats["ecosystems"] or stats["ecosystems"]
