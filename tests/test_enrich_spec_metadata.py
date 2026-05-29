from __future__ import annotations

import importlib.util
from pathlib import Path


_TOOL = Path(__file__).resolve().parent.parent / "tools" / "enrich_spec_metadata.py"
_SPEC = importlib.util.spec_from_file_location("enrich_spec_metadata", _TOOL)
esm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(esm)


def test_extract_html_summary_prefers_og_description():
    html = (
        '<html><head>'
        '<meta property="og:description" content="Structured data serialization.">'
        '<title>Ignored title</title>'
        '</head></html>'
    )
    assert esm._extract_html_summary(html) == "Structured data serialization."


def test_github_raw_to_repo_url_converts_tree_path():
    url = "https://github.com/torvalds/linux/raw/v5.8/include/uapi/linux/"
    assert esm._github_raw_to_repo_url(url) == "https://github.com/torvalds/linux/tree/v5.8/include/uapi/linux"


def test_freebsd_include_paths_resolve_parent_reference():
    text = '.include "${.CURDIR:H}/boost-all/common.mk"\n.include <bsd.port.mk>\n'
    assert esm._freebsd_include_paths(text, "devel/boost-libs") == ["devel/boost-all/common.mk"]


def test_nixpkgs_resolve_relative_uses_source_path_directory():
    assert (
        esm._nixpkgs_resolve_relative("pkgs/top-level/all-packages.nix", "../build-support/setup-hooks/foo.sh")
        == "pkgs/build-support/setup-hooks/foo.sh"
    )


def test_extract_nix_relative_source_finds_hook_path():
    block = 'makeSetupHook { name = "foo"; } ../build-support/setup-hooks/foo.sh;'
    assert esm._extract_nix_relative_source(block) == "../build-support/setup-hooks/foo.sh"


def test_extract_nix_relative_source_uses_last_match():
    block = 'src = ./tests/sample-project;\n} ./wrap-gapps-hook.sh\n'
    assert esm._extract_nix_relative_source(block) == "./wrap-gapps-hook.sh"


def test_extract_nix_attr_block_stops_at_next_top_level_attr():
    text = (
        'copyDesktopItems = makeSetupHook { meta.license = lib.licenses.mit; } ../foo.sh;\n\n'
        '  makeDesktopItem = callPackage ../bar { };\n'
    )
    assert "makeDesktopItem" not in esm._extract_nix_attr_block(text, "copyDesktopItems")


def test_nixpkgs_categories_from_path_uses_meaningful_segments():
    assert esm._nixpkgs_categories_from_path("pkgs/tools/compression/xz/default.nix") == ["tools", "compression"]
    assert esm._nixpkgs_categories_from_path("pkgs/build-support/setup-hooks/wrap-gapps-hook/default.nix") == [
        "build-support",
        "setup-hooks",
    ]
    assert esm._nixpkgs_categories_from_path("pkgs/by-name/li/libx11/package.nix") == []


def test_nixpkgs_hook_categories_cover_hook_packages():
    record = {"identity": {"canonical_name": "make-shell-wrapper-hook"}}
    assert esm._nixpkgs_hook_categories(record) == ["build-support", "setup-hooks"]


def test_nixpkgs_category_overrides_cover_by_name_records():
    assert esm._NIXPKGS_CATEGORY_OVERRIDES["libx11"] == ["development", "libraries"]
    assert esm._NIXPKGS_CATEGORY_OVERRIDES["unzip"] == ["tools", "compression"]


def test_enrich_nixpkgs_uses_curl_homepage_fallback():
    record = {
        "identity": {"canonical_name": "curl"},
        "provenance": {"source_path": "curl"},
        "descriptive": {"homepage": "", "categories": [], "maintainers": ["alice"]},
        "sources": [{"type": "archive", "url": "https://example.com/curl.tar.gz"}],
    }

    changed = esm.enrich_nixpkgs(record, timeout=1)

    assert changed is True
    assert record["descriptive"]["homepage"] == "https://curl.se/"
    assert record["descriptive"]["categories"] == ["tools", "networking"]


def test_enrich_pypi_fills_source_repository_when_description_complete(monkeypatch):
    record = {
        "identity": {"ecosystem_id": "aiohttp"},
        "descriptive": {
            "homepage": "https://docs.aiohttp.org/",
            "summary": "Async HTTP client/server framework.",
            "maintainers": ["maintainer@example.com"],
        },
        "sources": [{"type": "sdist", "url": "https://files.example/aiohttp.tar.gz", "sha256": "old"}],
        "extensions": {"pypi": {"requires_python": ">=3.9", "classifiers": ["Framework :: AsyncIO"]}},
    }
    data = {
        "info": {
            "project_urls": {"Homepage": "https://github.com/aio-libs/aiohttp"},
            "requires_python": ">=3.9",
            "classifiers": ["Framework :: AsyncIO"],
        },
        "urls": [],
    }
    monkeypatch.setattr(esm, "_fetch_pypi_record", lambda name, timeout: data)

    changed = esm.enrich_pypi(record, timeout=1)

    assert changed is True
    assert record["extensions"]["pypi"]["source_repository"] == "https://github.com/aio-libs/aiohttp"


def test_enrich_pypi_fills_empty_extension_and_source_fields(monkeypatch):
    record = {
        "identity": {"ecosystem_id": "sample"},
        "descriptive": {
            "homepage": "https://example.com",
            "summary": "Sample package.",
            "maintainers": ["maintainer@example.com"],
        },
        "sources": [{"type": "none", "url": ""}],
        "extensions": {"pypi": {"source_repository": "", "requires_python": "", "classifiers": []}},
    }
    data = {
        "info": {
            "project_urls": {"Source": "https://github.com/example/sample.git"},
            "requires_python": ">=3.10",
            "classifiers": ["Programming Language :: Python :: 3"],
        },
        "urls": [
            {
                "packagetype": "sdist",
                "url": "https://files.pythonhosted.org/packages/sample-1.0.tar.gz",
                "digests": {"sha256": "abc123"},
            }
        ],
    }
    monkeypatch.setattr(esm, "_fetch_pypi_record", lambda name, timeout: data)

    changed = esm.enrich_pypi(record, timeout=1)

    assert changed is True
    assert record["extensions"]["pypi"]["source_repository"] == "https://github.com/example/sample"
    assert record["extensions"]["pypi"]["requires_python"] == ">=3.10"
    assert record["extensions"]["pypi"]["classifiers"] == ["Programming Language :: Python :: 3"]
    assert record["sources"] == [
        {
            "type": "sdist",
            "url": "https://files.pythonhosted.org/packages/sample-1.0.tar.gz",
            "sha256": "abc123",
        }
    ]
