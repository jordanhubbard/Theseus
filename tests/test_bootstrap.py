"""
Tests for bootstrap_canonical_recipes.py.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import bootstrap_canonical_recipes as bc

# ---------------------------------------------------------------------------
# Fixtures: minimal synthetic source content
# ---------------------------------------------------------------------------

NIX_BASIC = """\
{ lib, stdenv, fetchurl, cmake }:
stdenv.mkDerivation rec {
  pname = "mylib";
  version = "2.1.0";
  src = fetchurl {
    url = "https://example.com/mylib-2.1.0.tar.gz";
    hash = "sha256-abc";
  };
  nativeBuildInputs = [ cmake ];
  buildInputs = [ zlib ];
  meta = with lib; {
    description = "A test library";
    homepage = "https://example.com/";
    license = licenses.mit;
  };
}
"""

NIX_WITH_PATCHES = """\
{ lib, stdenv, fetchurl }:
stdenv.mkDerivation rec {
  pname = "patchedpkg";
  version = "1.0";
  src = fetchurl { url = "https://example.com/pkg.tar.gz"; hash = "sha256-x"; };
  patches = [ ./fix-build.patch ./fix-test.patch ];
  meta = with lib; {
    description = "Patched package";
    homepage = "https://example.com/";
    license = licenses.bsd2;
  };
}
"""

NIX_NO_DERIVATION = """\
# This is just a utility file
{ lib }:
lib.makeOverridable (args: args.value + 1)
"""

NIX_NAME_VERSION_IN_NAME = """\
{ lib, stdenv }:
stdenv.mkDerivation {
  name = "oldstyle-1.2.3";
  src = ./src;
  meta = with lib; {
    description = "Old-style name";
    homepage = "https://old.example.com/";
    license = licenses.gpl3;
  };
}
"""

PORTS_BASIC = """\
PORTNAME=\tcurl
PORTVERSION=\t8.7.1
CATEGORIES=\tftp
COMMENT=\tCommand line tool for transferring data with URLs
WWW=\thttps://curl.se/
LICENSE=\tcurl
LIB_DEPENDS=\tlibssl.so:security/openssl libz.so:archivers/zlib
BUILD_DEPENDS=\tpkgconf:devel/pkgconf
USES=\tssl tar:xz
OPTIONS_DEFINE=\tIDN LDAP
"""

PORTS_CMAKE = """\
PORTNAME=\tmycmakepkg
PORTVERSION=\t3.0.0
CATEGORIES=\tdevel
COMMENT=\tA CMake-based package
WWW=\thttps://cmake-example.com/
LICENSE=\tMIT
USES=\tcmake
"""

PORTS_NO_PORTNAME = """\
# This is not a port Makefile
SOMEVAR=\tvalue
"""

PORTS_CONTINUATION = """\
PORTNAME=\tcontinuedpkg
PORTVERSION=\t1.0
CATEGORIES=\tdevel
COMMENT=\tPackage with continuation lines
WWW=\thttps://example.com/
LICENSE=\tMIT
BUILD_DEPENDS=\t\\
\t\tpkgconf:devel/pkgconf \\
\t\tgmake:devel/gmake
"""


def _make_fake_nixpkgs(root: Path, packages: dict[str, str]) -> None:
    """Create a minimal fake Nixpkgs tree under root."""
    for rel_path, content in packages.items():
        p = root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _make_fake_ports(root: Path, packages: dict[str, str]) -> None:
    """Create a minimal fake FreeBSD Ports tree under root."""
    for rel_path, content in packages.items():
        p = root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# _str_match
# ---------------------------------------------------------------------------

def test_str_match_found():
    assert bc._str_match('pname = "hello"', r'\bpname\s*=\s*"([^"]+)"') == "hello"


def test_str_match_not_found():
    assert bc._str_match("nothing here", r'\bpname\s*=\s*"([^"]+)"') is None


# ---------------------------------------------------------------------------
# _nix_list_contents
# ---------------------------------------------------------------------------

def test_nix_list_contents_basic():
    content = 'nativeBuildInputs = [ cmake pkg-config ];\n'
    result = bc._nix_list_contents(content, "nativeBuildInputs")
    assert "cmake" in result
    assert "pkg-config" in result


def test_nix_list_contents_attribute_path():
    content = 'buildInputs = [ pkgs.zlib pkgs.openssl ];\n'
    result = bc._nix_list_contents(content, "buildInputs")
    assert "zlib" in result
    assert "openssl" in result


def test_nix_list_contents_missing():
    result = bc._nix_list_contents("no lists here", "buildInputs")
    assert result == []


def test_nix_list_contents_multiline():
    content = 'nativeBuildInputs = [\n  cmake\n  meson\n];\n'
    result = bc._nix_list_contents(content, "nativeBuildInputs")
    assert "cmake" in result
    assert "meson" in result


# ---------------------------------------------------------------------------
# _nix_build_system
# ---------------------------------------------------------------------------

def test_nix_build_system_cmake():
    assert bc._nix_build_system("nativeBuildInputs = [ cmake ];") == "cmake"


def test_nix_build_system_meson():
    assert bc._nix_build_system("nativeBuildInputs = [ meson ninja ];") == "meson"


def test_nix_build_system_default_autotools():
    assert bc._nix_build_system("stdenv.mkDerivation {}") == "autotools"


# ---------------------------------------------------------------------------
# _ports_vars
# ---------------------------------------------------------------------------

def test_ports_vars_basic():
    content = "PORTNAME=\tcurl\nPORTVERSION=\t8.7.1\n"
    v = bc._ports_vars(content)
    assert v["PORTNAME"] == "curl"
    assert v["PORTVERSION"] == "8.7.1"


def test_ports_vars_continuation():
    content = "BUILD_DEPENDS=\t\\\n\tpkgconf:devel/pkgconf \\\n\tgmake:devel/gmake\n"
    v = bc._ports_vars(content)
    assert "pkgconf" in v["BUILD_DEPENDS"]
    assert "gmake" in v["BUILD_DEPENDS"]


def test_ports_vars_optional_assign():
    content = "USES?=\tcmake\n"
    v = bc._ports_vars(content)
    assert v["USES"] == "cmake"


def test_ports_vars_append_assign():
    content = "USES+=\tssl\n"
    v = bc._ports_vars(content)
    assert v["USES"] == "ssl"


def test_ports_vars_ignores_comments():
    content = "# PORTNAME=\tshould-be-ignored\nPORTNAME=\treal\n"
    v = bc._ports_vars(content)
    assert v["PORTNAME"] == "real"


# ---------------------------------------------------------------------------
# _ports_dep_names
# ---------------------------------------------------------------------------

def test_ports_dep_names_basic():
    dep_str = "libssl.so:security/openssl libz.so:archivers/zlib"
    result = bc._ports_dep_names(dep_str)
    assert "openssl" in result
    assert "zlib" in result


def test_ports_dep_names_empty():
    assert bc._ports_dep_names("") == []


def test_ports_dep_names_build_style():
    dep_str = "pkgconf:devel/pkgconf"
    result = bc._ports_dep_names(dep_str)
    assert result == ["pkgconf"]


# ---------------------------------------------------------------------------
# parse_nix_file
# ---------------------------------------------------------------------------

def test_parse_nix_file_basic(tmp_path):
    (tmp_path / "pkgs" / "mylib").mkdir(parents=True)
    nix_file = tmp_path / "pkgs" / "mylib" / "default.nix"
    nix_file.write_text(NIX_BASIC, encoding="utf-8")
    rec = bc.parse_nix_file(nix_file, tmp_path)
    assert rec is not None
    assert rec["identity"]["canonical_name"] == "mylib"
    assert rec["identity"]["version"] == "2.1.0"
    assert rec["identity"]["ecosystem"] == "nixpkgs"
    assert rec["descriptive"]["summary"] == "A test library"
    assert rec["descriptive"]["homepage"] == "https://example.com/"
    assert "MIT" in rec["descriptive"]["license"]
    assert rec["build"]["system_kind"] == "cmake"
    assert "cmake" in rec["dependencies"]["build"]
    assert "zlib" in rec["dependencies"]["host"]


def test_parse_nix_file_returns_none_for_non_derivation(tmp_path):
    (tmp_path / "lib").mkdir()
    nix_file = tmp_path / "lib" / "default.nix"
    nix_file.write_text(NIX_NO_DERIVATION, encoding="utf-8")
    assert bc.parse_nix_file(nix_file, tmp_path) is None


def test_parse_nix_file_patches(tmp_path):
    (tmp_path / "pkgs" / "patchedpkg").mkdir(parents=True)
    nix_file = tmp_path / "pkgs" / "patchedpkg" / "default.nix"
    nix_file.write_text(NIX_WITH_PATCHES, encoding="utf-8")
    rec = bc.parse_nix_file(nix_file, tmp_path)
    assert rec is not None
    assert len(rec["patches"]) == 2


def test_parse_nix_file_name_version_split(tmp_path):
    (tmp_path / "pkgs" / "old").mkdir(parents=True)
    nix_file = tmp_path / "pkgs" / "old" / "default.nix"
    nix_file.write_text(NIX_NAME_VERSION_IN_NAME, encoding="utf-8")
    rec = bc.parse_nix_file(nix_file, tmp_path)
    assert rec is not None
    assert rec["identity"]["canonical_name"] == "oldstyle"
    assert rec["identity"]["version"] == "1.2.3"


def test_parse_nix_file_confidence_range(tmp_path):
    (tmp_path / "pkgs" / "mylib").mkdir(parents=True)
    nix_file = tmp_path / "pkgs" / "mylib" / "default.nix"
    nix_file.write_text(NIX_BASIC, encoding="utf-8")
    rec = bc.parse_nix_file(nix_file, tmp_path)
    conf = rec["provenance"]["confidence"]
    assert 0.0 <= conf <= 1.0


def test_parse_nix_file_provenance_fields(tmp_path):
    (tmp_path / "pkgs" / "mylib").mkdir(parents=True)
    nix_file = tmp_path / "pkgs" / "mylib" / "default.nix"
    nix_file.write_text(NIX_BASIC, encoding="utf-8")
    rec = bc.parse_nix_file(nix_file, tmp_path)
    prov = rec["provenance"]
    assert prov["generated_by"] == bc.GENERATED_BY
    assert isinstance(prov["unmapped"], list)
    assert isinstance(prov["warnings"], list)


# ---------------------------------------------------------------------------
# parse_ports_makefile
# ---------------------------------------------------------------------------

def test_parse_ports_makefile_basic(tmp_path):
    (tmp_path / "ftp" / "curl").mkdir(parents=True)
    mf = tmp_path / "ftp" / "curl" / "Makefile"
    mf.write_text(PORTS_BASIC, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["identity"]["canonical_name"] == "curl"
    assert rec["identity"]["version"] == "8.7.1"
    assert rec["identity"]["ecosystem"] == "freebsd_ports"
    assert rec["descriptive"]["summary"] == "Command line tool for transferring data with URLs"
    assert rec["descriptive"]["homepage"] == "https://curl.se/"
    assert "curl" in rec["descriptive"]["license"]
    assert "openssl" in rec["dependencies"]["host"]
    assert "zlib" in rec["dependencies"]["host"]
    assert "pkgconf" in rec["dependencies"]["build"]
    assert "IDN" in rec["features"]["options_define"]


def test_parse_ports_makefile_cmake(tmp_path):
    (tmp_path / "devel" / "mycmakepkg").mkdir(parents=True)
    mf = tmp_path / "devel" / "mycmakepkg" / "Makefile"
    mf.write_text(PORTS_CMAKE, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["build"]["system_kind"] == "cmake"


def test_parse_ports_makefile_returns_none_for_non_port(tmp_path):
    mf = tmp_path / "Makefile"
    mf.write_text(PORTS_NO_PORTNAME, encoding="utf-8")
    assert bc.parse_ports_makefile(mf, tmp_path) is None


def test_parse_ports_makefile_continuation_lines(tmp_path):
    (tmp_path / "devel" / "continuedpkg").mkdir(parents=True)
    mf = tmp_path / "devel" / "continuedpkg" / "Makefile"
    mf.write_text(PORTS_CONTINUATION, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert "pkgconf" in rec["dependencies"]["build"]
    assert "gmake" in rec["dependencies"]["build"]


def test_parse_ports_makefile_patch_files(tmp_path):
    (tmp_path / "devel" / "patched").mkdir(parents=True)
    mf = tmp_path / "devel" / "patched" / "Makefile"
    mf.write_text(PORTS_BASIC, encoding="utf-8")
    files_dir = tmp_path / "devel" / "patched" / "files"
    files_dir.mkdir()
    (files_dir / "patch-configure").write_text("--- a\n+++ b\n", encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert len(rec["patches"]) == 1
    assert rec["patches"][0]["path"] == "files/patch-configure"


def test_parse_ports_makefile_confidence_range(tmp_path):
    (tmp_path / "ftp" / "curl").mkdir(parents=True)
    mf = tmp_path / "ftp" / "curl" / "Makefile"
    mf.write_text(PORTS_BASIC, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    conf = rec["provenance"]["confidence"]
    assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# import_nixpkgs / import_ports
# ---------------------------------------------------------------------------

def test_import_nixpkgs_end_to_end(tmp_path):
    fake_nix = tmp_path / "nixpkgs"
    _make_fake_nixpkgs(fake_nix, {
        "pkgs/mylib/default.nix": NIX_BASIC,
        "pkgs/patchedpkg/default.nix": NIX_WITH_PATCHES,
    })
    out = tmp_path / "out" / "nixpkgs"
    count = bc.import_nixpkgs(fake_nix, out, commit="abc123")
    assert count == 2
    records = list(out.glob("*.json"))
    assert len(records) == 2
    for r in records:
        rec = json.loads(r.read_text())
        assert rec["provenance"]["source_repo_commit"] == "abc123"
        assert rec["identity"]["ecosystem"] == "nixpkgs"


def test_import_nixpkgs_skips_non_derivations(tmp_path):
    fake_nix = tmp_path / "nixpkgs"
    _make_fake_nixpkgs(fake_nix, {
        "pkgs/real/default.nix": NIX_BASIC,
        "lib/utils/default.nix": NIX_NO_DERIVATION,
    })
    out = tmp_path / "out" / "nixpkgs"
    count = bc.import_nixpkgs(fake_nix, out, commit=None)
    assert count == 1


def test_import_ports_end_to_end(tmp_path):
    fake_ports = tmp_path / "ports"
    _make_fake_ports(fake_ports, {
        "ftp/curl/Makefile": PORTS_BASIC,
        "devel/mycmakepkg/Makefile": PORTS_CMAKE,
    })
    out = tmp_path / "out" / "freebsd_ports"
    count = bc.import_ports(fake_ports, out, commit="def456")
    assert count == 2
    records = list(out.glob("*.json"))
    assert len(records) == 2
    for r in records:
        rec = json.loads(r.read_text())
        assert rec["provenance"]["source_repo_commit"] == "def456"
        assert rec["identity"]["ecosystem"] == "freebsd_ports"


def test_import_ports_skips_non_ports(tmp_path):
    fake_ports = tmp_path / "ports"
    _make_fake_ports(fake_ports, {
        "ftp/curl/Makefile": PORTS_BASIC,
        "ftp/notaport/Makefile": PORTS_NO_PORTNAME,
    })
    out = tmp_path / "out" / "freebsd_ports"
    count = bc.import_ports(fake_ports, out, commit=None)
    assert count == 1


# ---------------------------------------------------------------------------
# _get_git_commit
# ---------------------------------------------------------------------------

def test_get_git_commit_returns_none_for_non_git(tmp_path):
    result = bc._get_git_commit(tmp_path)
    assert result is None
