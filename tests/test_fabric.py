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

    def test_npm_source_repository_field(self):
        rec = _recipe(
            "lodash",
            eco="npm",
            homepage="https://lodash.com/",
            extensions={"npm": {"source_repository": "https://github.com/lodash/lodash"}},
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/lodash/lodash"
        assert repo["source"] == "npm.source_repository"

    def test_nixpkgs_source_repository_field(self):
        rec = _recipe(
            "ninja",
            eco="nixpkgs",
            homepage="https://ninja-build.org/",
            extensions={"nixpkgs": {"source_repository": "https://github.com/ninja-build/ninja"}},
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/ninja-build/ninja"
        assert repo["source"] == "nixpkgs.source_repository"

    def test_freedesktop_gitlab_homepage(self):
        rec = _recipe(
            "libxrandr",
            homepage="https://gitlab.freedesktop.org/xorg/lib/libxrandr",
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://gitlab.freedesktop.org/xorg/lib/libxrandr"
        assert repo["source"] == "homepage"

    def test_cgit_maps_to_gitlab_freedesktop(self):
        rec = _recipe("glu", homepage="https://cgit.freedesktop.org/mesa/glu/")
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://gitlab.freedesktop.org/mesa/glu"

    def test_gnu_savannah_from_software_homepage(self):
        rec = _recipe("bash", homepage="https://www.gnu.org/software/bash/")
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://git.savannah.gnu.org/git/bash.git"
        assert repo["source"] == "gnu_savannah_convention"

    def test_github_pages_homepage(self):
        rec = _recipe("harfbuzz", homepage="https://harfbuzz.github.io/")
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/harfbuzz/harfbuzz"

    def test_unique_git_clone_source(self):
        rec = _recipe(
            "cmake",
            homepage="https://www.cmake.org",
            sources=[{"type": "git", "url": "https://gitlab.kitware.com/cmake/cmake.git"}],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://gitlab.kitware.com/cmake/cmake"
        assert repo["source"] == "sources.git"

    def test_unexpanded_unknown_vars_are_not_repos(self):
        rec = _recipe(
            "libzip",
            homepage="https://libzip.org/",
            sources=[{
                "type": "master_sites",
                "url": "https://github.com/${GH_ACCOUNT}/${GH_PROJECT}/releases/",
            }],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] is None

    def test_portname_github_corroborated_by_homepage(self):
        rec = _recipe(
            "libzip",
            homepage="https://libzip.org/",
            sources=[{
                "type": "master_sites",
                "url": "https://github.com/nih-at/${PORTNAME}/releases/download/v${DISTVERSION}/",
            }],
            extensions={"freebsd_ports": {"raw_vars": {"PORTNAME": "libzip"}}},
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/nih-at/libzip"
        assert repo["source"] == "homepage_corroborated_github"

    def test_unique_owner_named_github(self):
        rec = _recipe(
            "itstool",
            homepage="https://itstool.org/",
            sources=[{"type": "homepage", "url": "https://github.com/itstool/itstool"}],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/itstool/itstool"
        assert repo["source"] == "unique_named_forge"

    def test_unique_gnome_gitlab(self):
        rec = _recipe(
            "json-glib",
            homepage="https://live.gnome.org/JsonGlib",
            sources=[{"type": "homepage", "url": "https://gitlab.gnome.org/GNOME/json-glib"}],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://gitlab.gnome.org/GNOME/json-glib"
        assert repo["source"] == "unique_named_forge"

    def test_savannah_preferred_over_language_binding(self):
        rec = _recipe(
            "readline",
            homepage="https://tiswww.case.edu/php/chet/readline/rltop.html",
            sources=[
                {"type": "homepage", "url": "https://github.com/ruby/readline"},
                {"type": "homepage", "url": "https://savannah.gnu.org/projects/readline/"},
            ],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://git.savannah.gnu.org/git/readline.git"
        assert "https://github.com/ruby/readline" in repo["candidates"]

    def test_openssl_ambiguous_github_not_promoted(self):
        rec = _recipe(
            "openssl",
            homepage="https://cran.r-project.org/package=openssl",
            sources=[
                {"type": "homepage", "url": "https://github.com/ruby/openssl"},
                {"type": "master_sites", "url": "https://github.com/openssl/openssl/releases/download/${DISTNAME}/"},
                {"type": "homepage", "url": "https://www.github.com/quictls/quictls"},
            ],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] is None
        assert "https://github.com/ruby/openssl" in repo["candidates"]
        assert "https://github.com/openssl/openssl" in repo["candidates"]

    def test_federico_bzip2_gitlab_not_promoted(self):
        rec = _recipe(
            "bzip2",
            homepage="https://www.sourceware.org/bzip2",
            sources=[{"type": "homepage", "url": "https://gitlab.com/federicomenaquintero/bzip2/"}],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] is None
        assert "https://gitlab.com/federicomenaquintero/bzip2" in repo["candidates"]

    def test_madler_unzip_not_promoted(self):
        rec = _recipe(
            "unzip",
            homepage="http://www.info-zip.org",
            sources=[{
                "type": "archive",
                "url": "https://github.com/madler/unzip/commit/41beb477c5744bc396fa1162ee0c14218ec12213.patch",
            }],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] is None

    def test_wayland_freedesktop_subdomain(self):
        rec = _recipe("wayland", homepage="https://wayland.freedesktop.org/")
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://gitlab.freedesktop.org/wayland/wayland"
        assert repo["source"] == "freedesktop_gitlab_convention"

    def test_wayland_protocols_from_gitlab_portname(self):
        rec = _recipe(
            "wayland-protocols",
            homepage="https://wayland.freedesktop.org/",
            sources=[{
                "type": "master_sites",
                "url": "https://gitlab.freedesktop.org/wayland/${PORTNAME}/-/releases/${DISTVERSION}/downloads/",
            }],
            extensions={"freebsd_ports": {"raw_vars": {"PORTNAME": "wayland-protocols"}}},
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://gitlab.freedesktop.org/wayland/wayland-protocols"

    def test_llvm_owner_matches_with_version_var(self):
        rec = _recipe(
            "llvm",
            homepage="https://llvm.org/",
            sources=[{
                "type": "master_sites",
                "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-${DISTVERSION}/",
            }],
        )
        repo = fab.extract_repository(rec)
        assert repo["url"] == "https://github.com/llvm/llvm-project"
        assert repo["source"] == "github_owner_matches_package"

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
        dropped = fab.extract_dropped_dependencies(rec)
        dropped_names = {d["name"] for d in dropped}
        assert "${LUA_PKGNAMEPREFIX}lzlib" in dropped_names
        assert "lib/lua/5.*/zlib.so" in dropped_names


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
        assert fp["schema_version"] == "1.1"
        assert fp["priority"]["primary"] == ["provenance", "tracking", "dependencies"]
        assert fp["evidence"]["recreation"] == "secondary"
        assert "maintainers" in fp["tracking"]

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
        assert merged["tracking"]["recipe_count"] == 2
        assert merged["evidence"]["recreation"] == "secondary"

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
        runtime = store.deps("requests", scope="runtime")
        by_name = {d["name"]: d for d in runtime}
        assert by_name["urllib3"]["resolved"] is True
        assert by_name["urllib3"]["resolved_to"] == "urllib3"

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
        dep = store.deps("flask", scope="runtime")[0]
        assert dep["name"] == "blinker"
        assert dep["resolved"] is False

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

    def test_tracking_provenance_and_distributions(self, tmp_path):
        recipes = tmp_path / "recipes"
        _write_recipe(
            recipes / "flask.json",
            name="flask",
            summary="A simple framework",
            homepage="https://github.com/pallets/flask",
            license=["BSD-3-Clause"],
            extensions={"pypi": {"source_repository": "https://github.com/pallets/flask"}},
            sources=[{
                "type": "sdist",
                "url": "https://files.pythonhosted.org/flask.tgz",
                "sha256": "abc",
            }],
            provenance={
                "confidence": 0.9,
                "generated_by": "bootstrap_canonical_recipes.py",
                "imported_at": "2026-03-29T19:55:18+00:00",
                "source_path": "https://pypi.org/pypi/flask/json",
                "source_repo_commit": "deadbeef",
                "warnings": [],
            },
            dependencies={
                "build": ["${NOT_A_DEP}"],
                "host": [],
                "runtime": ["werkzeug"],
                "test": [],
            },
        )
        (tmp_path / "zspecs").mkdir()
        (tmp_path / "zspecs" / "flask.zspec.zsdl").write_text("spec: flask\n", encoding="utf-8")
        fab.ingest(tmp_path, [recipes], out_dir=tmp_path / "fabric" / "packages", jobs=1)
        rec = fab.FabricStore(tmp_path).get("flask")
        src = rec["provenance"]["sources"][0]
        assert src["source_path"] == "https://pypi.org/pypi/flask/json"
        assert src["source_repo_commit"] == "deadbeef"
        assert rec["tracking"]["source_paths"] == ["https://pypi.org/pypi/flask/json"]
        assert rec["tracking"]["source_repo_commits"] == ["deadbeef"]
        assert rec["tracking"]["distributions"][0]["sha256"] == "abc"
        assert rec["tracking"]["dropped_dependencies"][0]["name"] == "${NOT_A_DEP}"
        assert rec["evidence"]["behavioral_spec"] == "zspecs/flask.zspec.zsdl"
        assert rec["evidence"]["recreation"] == "secondary"
        assert rec["priority"]["primary"][0] == "provenance"

    def test_parallel_ingest_matches_serial(self, tmp_path):
        recipes = tmp_path / "recipes"
        for name in ("alpha", "beta", "gamma", "delta"):
            _write_recipe(
                recipes / ("%s.json" % name),
                name=name,
                dependencies={
                    "build": [],
                    "host": [],
                    "runtime": ["alpha"] if name != "alpha" else [],
                    "test": [],
                },
            )
        serial_dir = tmp_path / "serial"
        parallel_dir = tmp_path / "parallel"
        a = fab.ingest(tmp_path, [recipes], out_dir=serial_dir, jobs=1)
        b = fab.ingest(tmp_path, [recipes], out_dir=parallel_dir, jobs=4)
        assert a["written"] == b["written"] == 4
        assert b["jobs"] == 4
        for name in ("alpha", "beta", "gamma", "delta"):
            left = json.loads((serial_dir / ("%s.json" % name)).read_text(encoding="utf-8"))
            right = json.loads((parallel_dir / ("%s.json" % name)).read_text(encoding="utf-8"))
            left["tracking"]["ingested_at"] = "ts"
            right["tracking"]["ingested_at"] = "ts"
            assert left == right
        beta = json.loads((parallel_dir / "beta.json").read_text(encoding="utf-8"))
        dep = [d for d in beta["depends_on"] if d["name"] == "alpha"][0]
        assert dep["resolved"] is True
        assert dep["resolved_to"] == "alpha"


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
        url = (rec.get("repository") or {}).get("url") or ""
        assert "ruby/zlib" not in url
        assert "lua-zlib" not in url

    def test_ambiguous_c_library_forks_not_promoted(self, store):
        bzip = ((store.get("bzip2") or {}).get("repository") or {}).get("url") or ""
        assert "federicomenaquintero" not in bzip
        ossl = ((store.get("openssl") or {}).get("repository") or {}).get("url") or ""
        assert "ruby/openssl" not in ossl
        unzip = ((store.get("unzip") or {}).get("repository") or {}).get("url") or ""
        assert "madler/unzip" not in unzip

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
        assert stats["dep_edges"] >= stats["dep_resolved"]
        assert "dep_dangling" in stats

    def test_priority_tracking_and_recreation_kept(self, store):
        flask = store.get("flask")
        assert flask["schema_version"] == "1.1"
        assert flask["priority"]["primary"] == ["provenance", "tracking", "dependencies"]
        assert flask["priority"]["secondary"] == ["recreation"]
        assert flask["evidence"]["recreation"] == "secondary"
        assert flask["tracking"]["source_paths"]
        assert flask["tracking"]["maintainers"]
        werk = [d for d in flask["depends_on"] if d["name"] == "werkzeug"][0]
        assert werk["resolved"] is True
        assert werk["resolved_to"] == "werkzeug"
        blinker = [d for d in flask["depends_on"] if d["name"] == "blinker"][0]
        assert blinker["resolved"] is False
        requests = store.get("requests")
        assert requests["evidence"]["behavioral_spec"] == "zspecs/requests.zspec.zsdl"
        assert requests["evidence"]["recreation"] == "secondary"
        zlib = store.get("zlib")
        assert zlib["evidence"]["behavioral_spec"] == "zspecs/zlib.zspec.zsdl"
        assert zlib["tracking"]["recipe_count"] == 3
        assert zlib["tracking"]["source_repo_commits"]
