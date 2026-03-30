"""
Tests for theseus/importer.py.
"""
import json
from pathlib import Path

import theseus.importer as bc

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

PORTS_WITH_MAINTAINER_CONFLICTS = """\
PORTNAME=\toldssl
PORTVERSION=\t1.0.0
CATEGORIES=\tsecurity
COMMENT=\tLegacy SSL library
WWW=\thttps://example.com/
LICENSE=\tOpenSSL
MAINTAINER=\tsecurity@FreeBSD.org
CONFLICTS=\topenssl-3* libressl-*
CONFLICTS_INSTALL=\topenssl30
DEPRECATED=\tUse security/openssl instead
EXPIRATION_DATE=\t2026-12-31
"""

# Master port that slave ports inherit from
PORTS_MASTER = """\
PORTNAME?=\tsvxlink
PORTVERSION=\t19.09.2
CATEGORIES=\tcomms hamradio
COMMENT?=\tGeneral purpose ham radio voice services
WWW=\thttps://www.svxlink.org/
LICENSE?=\tGPLv2
LIB_DEPENDS?=\tlibcurl.so:ftp/curl libgsm.so:audio/gsm
USES+=\tcmake gnome pkgconfig
"""

# Slave port that overrides PORTNAME and COMMENT from the master
PORTS_SLAVE_SIBLING = """\
PORTNAME=\tqtel
COMMENT=\tQtel Echolink client
LICENSE=\tGPLv2
LIB_DEPENDS=\tlibecholib.so:comms/svxlink libgsm.so:audio/gsm
MASTERDIR=\t${.CURDIR}/../svxlink
USES=\tqt:5 gnome
"""

# Slave port with no PORTNAME of its own (inherits entirely from master)
PORTS_SLAVE_NO_PORTNAME = """\
CATEGORIES=\tportugese
MASTERDIR=\t${.CURDIR}/../../www/webalizer
WEBALIZER_LANG=\tportugese
"""

# Slave port with unresolvable MASTERDIR (e.g. uses unknown make variable)
PORTS_SLAVE_BAD_MASTERDIR = """\
MASTERDIR=\t${PORTSDIR}/comms/svxlink
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


def test_parse_ports_makefile_maintainer(tmp_path):
    """MAINTAINER variable is extracted into descriptive.maintainers."""
    (tmp_path / "security" / "oldssl").mkdir(parents=True)
    mf = tmp_path / "security" / "oldssl" / "Makefile"
    mf.write_text(PORTS_WITH_MAINTAINER_CONFLICTS, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["descriptive"]["maintainers"] == ["security@FreeBSD.org"]


def test_parse_ports_makefile_conflicts(tmp_path):
    """CONFLICTS and CONFLICTS_INSTALL are merged into top-level conflicts list."""
    (tmp_path / "security" / "oldssl").mkdir(parents=True)
    mf = tmp_path / "security" / "oldssl" / "Makefile"
    mf.write_text(PORTS_WITH_MAINTAINER_CONFLICTS, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert isinstance(rec["conflicts"], list)
    assert "openssl30" in rec["conflicts"]


def test_parse_ports_makefile_deprecated(tmp_path):
    """DEPRECATED variable sets descriptive.deprecated = True."""
    (tmp_path / "security" / "oldssl").mkdir(parents=True)
    mf = tmp_path / "security" / "oldssl" / "Makefile"
    mf.write_text(PORTS_WITH_MAINTAINER_CONFLICTS, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["descriptive"]["deprecated"] is True


def test_parse_ports_makefile_expiration_date(tmp_path):
    """EXPIRATION_DATE is stored in descriptive.expiration_date."""
    (tmp_path / "security" / "oldssl").mkdir(parents=True)
    mf = tmp_path / "security" / "oldssl" / "Makefile"
    mf.write_text(PORTS_WITH_MAINTAINER_CONFLICTS, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["descriptive"]["expiration_date"] == "2026-12-31"


def test_parse_ports_makefile_no_maintainer_defaults_empty(tmp_path):
    """When MAINTAINER is absent, maintainers is an empty list."""
    (tmp_path / "ftp" / "curl").mkdir(parents=True)
    mf = tmp_path / "ftp" / "curl" / "Makefile"
    mf.write_text(PORTS_BASIC, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["descriptive"]["maintainers"] == []


def test_parse_ports_makefile_conflicts_field_always_present(tmp_path):
    """conflicts top-level field is always present, even when empty."""
    (tmp_path / "ftp" / "curl").mkdir(parents=True)
    mf = tmp_path / "ftp" / "curl" / "Makefile"
    mf.write_text(PORTS_BASIC, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert "conflicts" in rec
    assert isinstance(rec["conflicts"], list)


# ---------------------------------------------------------------------------
# parse_ports_makefile — slave port support
# ---------------------------------------------------------------------------

def _setup_master(tmp_path):
    """Create master port at comms/svxlink/Makefile."""
    master_dir = tmp_path / "comms" / "svxlink"
    master_dir.mkdir(parents=True)
    (master_dir / "Makefile").write_text(PORTS_MASTER, encoding="utf-8")
    return master_dir


def test_parse_ports_makefile_slave_inherits_portname(tmp_path):
    """Slave that sets PORTNAME overrides master's ?= PORTNAME."""
    _setup_master(tmp_path)
    slave_dir = tmp_path / "comms" / "qtel"
    slave_dir.mkdir(parents=True)
    mf = slave_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_SIBLING, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["identity"]["canonical_name"] == "qtel"


def test_parse_ports_makefile_slave_inherits_version_from_master(tmp_path):
    """Slave without PORTVERSION gets it from master."""
    _setup_master(tmp_path)
    slave_dir = tmp_path / "comms" / "qtel"
    slave_dir.mkdir(parents=True)
    mf = slave_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_SIBLING, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["identity"]["version"] == "19.09.2"


def test_parse_ports_makefile_slave_overrides_comment(tmp_path):
    """Slave COMMENT takes precedence over master's COMMENT?=."""
    _setup_master(tmp_path)
    slave_dir = tmp_path / "comms" / "qtel"
    slave_dir.mkdir(parents=True)
    mf = slave_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_SIBLING, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["descriptive"]["summary"] == "Qtel Echolink client"


def test_parse_ports_makefile_slave_no_portname_uses_master(tmp_path):
    """Slave with no PORTNAME at all inherits it from the master."""
    (tmp_path / "www" / "webalizer").mkdir(parents=True)
    (tmp_path / "www" / "webalizer" / "Makefile").write_text(PORTS_MASTER, encoding="utf-8")
    slave_dir = tmp_path / "portuguese" / "webalizer-pt"
    slave_dir.mkdir(parents=True)
    mf = slave_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_NO_PORTNAME, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert rec["identity"]["canonical_name"] == "svxlink"


def test_parse_ports_makefile_slave_source_path_is_slave(tmp_path):
    """provenance.source_path must point to the slave port, not the master."""
    _setup_master(tmp_path)
    slave_dir = tmp_path / "comms" / "qtel"
    slave_dir.mkdir(parents=True)
    mf = slave_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_SIBLING, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert "qtel" in rec["provenance"]["source_path"]
    assert "svxlink" not in rec["provenance"]["source_path"]


def test_parse_ports_makefile_slave_warns_about_merge(tmp_path):
    """A slave port record must carry a warning about the merge."""
    _setup_master(tmp_path)
    slave_dir = tmp_path / "comms" / "qtel"
    slave_dir.mkdir(parents=True)
    mf = slave_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_SIBLING, encoding="utf-8")
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is not None
    assert any("slave port" in w for w in rec["provenance"]["warnings"])


def test_parse_ports_makefile_slave_unresolvable_masterdir(tmp_path):
    """Slave with unresolvable MASTERDIR (unknown make var) returns None."""
    mf_dir = tmp_path / "comms" / "badport"
    mf_dir.mkdir(parents=True)
    mf = mf_dir / "Makefile"
    mf.write_text(PORTS_SLAVE_BAD_MASTERDIR, encoding="utf-8")
    # No PORTNAME and MASTERDIR can't be resolved — should return None
    rec = bc.parse_ports_makefile(mf, tmp_path)
    assert rec is None


def test_import_ports_includes_slave_ports(tmp_path):
    """import_ports must count slave ports, not skip them."""
    fake_ports = tmp_path / "ports"
    master_dir = fake_ports / "comms" / "svxlink"
    master_dir.mkdir(parents=True)
    (master_dir / "Makefile").write_text(PORTS_MASTER, encoding="utf-8")
    slave_dir = fake_ports / "comms" / "qtel"
    slave_dir.mkdir(parents=True)
    (slave_dir / "Makefile").write_text(PORTS_SLAVE_SIBLING, encoding="utf-8")
    out = tmp_path / "out"
    count = bc.import_ports(fake_ports, out, commit=None)
    # Both master and slave should be imported
    assert count == 2


# ---------------------------------------------------------------------------
# _nix_eval_to_record
# ---------------------------------------------------------------------------

_EVAL_RAW_FULL = {
    "pname": "curl",
    "version": "8.7.1",
    "description": "Command line tool for transferring data with URLs",
    "homepage": "https://curl.se/",
    "license": ["curl"],
    "maintainers": ["Scrumplex"],
    "platforms": ["x86_64-linux"],
    "position": "",
}

_EVAL_RAW_MINIMAL = {
    "pname": "mypkg",
    "version": "1.0",
    "description": "",
    "homepage": "",
    "license": [],
    "nativeBuildInputs": [],
    "buildInputs": [],
    "propagatedBuildInputs": [],
    "maintainers": [],
    "platforms": [],
    "position": "",
}


def test_nix_eval_to_record_identity(tmp_path):
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    assert rec["identity"]["canonical_name"] == "curl"
    assert rec["identity"]["version"] == "8.7.1"
    assert rec["identity"]["ecosystem"] == "nixpkgs"
    assert rec["identity"]["ecosystem_id"] == "curl"


def test_nix_eval_to_record_descriptive(tmp_path):
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    assert rec["descriptive"]["summary"] == "Command line tool for transferring data with URLs"
    assert rec["descriptive"]["homepage"] == "https://curl.se/"
    assert "curl" in rec["descriptive"]["license"]


def test_nix_eval_to_record_deps_empty(tmp_path):
    """Eval importer leaves dep arrays empty (infinite recursion risk with --strict)."""
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    assert rec["dependencies"]["build"] == []
    assert rec["dependencies"]["host"] == []
    assert rec["dependencies"]["runtime"] == []
    # A warning must be present about deps not being extracted
    assert any("deps not extracted" in w for w in rec["provenance"]["warnings"])


def test_nix_eval_to_record_confidence_range(tmp_path):
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    conf = rec["provenance"]["confidence"]
    assert 0.0 <= conf <= 1.0


def test_nix_eval_to_record_confidence_higher_than_regex_baseline(tmp_path):
    """Eval-based records should have a higher base confidence than regex records."""
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    # regex baseline is 0.55; eval baseline is 0.70
    assert rec["provenance"]["confidence"] >= 0.70


def test_nix_eval_to_record_maintainers_in_descriptive(tmp_path):
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    assert "Scrumplex" in rec["descriptive"]["maintainers"]
    assert rec["extensions"]["nixpkgs"]["attr"] == "curl"
    assert "maintainers" not in rec["extensions"]["nixpkgs"]


def test_nix_eval_to_record_conflicts_is_empty_list(tmp_path):
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    assert rec["conflicts"] == []


def test_nix_eval_to_record_minimal_warns_missing_fields(tmp_path):
    rec = bc._nix_eval_to_record("mypkg", _EVAL_RAW_MINIMAL, tmp_path)
    unmapped = rec["provenance"]["unmapped"]
    assert "meta.description" in unmapped
    assert "meta.homepage" in unmapped
    assert "meta.license" in unmapped


def test_nix_eval_to_record_source_path_from_position(tmp_path):
    raw = dict(_EVAL_RAW_FULL)
    raw["position"] = f"{tmp_path}/pkgs/development/curl/default.nix:1"
    rec = bc._nix_eval_to_record("curl", raw, tmp_path)
    assert rec["provenance"]["source_path"] == "pkgs/development/curl/default.nix"


def test_nix_eval_to_record_source_path_falls_back_to_attr(tmp_path):
    rec = bc._nix_eval_to_record("curl", _EVAL_RAW_FULL, tmp_path)
    # No position set → attr name used
    assert rec["provenance"]["source_path"] == "curl"


def test_nix_eval_batch_returns_dict_on_bad_input(tmp_path):
    """_nix_eval_batch with an empty list should return an empty dict."""
    result = bc._nix_eval_batch(tmp_path, [])
    assert isinstance(result, dict)


def test_nix_instantiate_available_returns_bool():
    result = bc._nix_instantiate_available()
    assert isinstance(result, bool)


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
