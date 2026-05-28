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
