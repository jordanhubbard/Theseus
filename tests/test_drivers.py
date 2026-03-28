"""
Tests for theseus/drivers/freebsd_ports.py and theseus/drivers/nixpkgs.py
"""
import pytest

from theseus.drivers.freebsd_ports import render as render_freebsd
from theseus.drivers.nixpkgs import render as render_nix
from theseus.drivers import DRIVERS


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

def _make_record(**overrides) -> dict:
    """Build a minimal canonical record for testing."""
    rec = {
        "schema_version": "0.2",
        "stub": False,
        "identity": {
            "canonical_name": "mypackage",
            "canonical_id": "mypackage-1.0.0",
            "version": "1.0.0",
            "ecosystem": "nixpkgs",
            "ecosystem_id": "mypackage",
        },
        "descriptive": {
            "summary": "A test package",
            "homepage": "https://example.com",
            "categories": ["devel"],
            "maintainers": ["alice@example.com"],
            "license": ["MIT"],
        },
        "sources": [
            {
                "type": "archive",
                "url": "https://example.com/releases/mypackage-1.0.0.tar.gz",
                "sha256": "abc123",
            }
        ],
        "dependencies": {
            "build": [],
            "host": [],
            "runtime": [],
            "test": [],
        },
        "build": {"system_kind": "autotools"},
        "features": {},
        "platforms": {"include": [], "exclude": []},
        "conflicts": [],
        "patches": [],
        "tests": {},
        "provenance": {"confidence": 0.9, "warnings": []},
        "extensions": {},
    }
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(rec.get(k), dict):
            rec[k].update(v)
        else:
            rec[k] = v
    return rec


# ---------------------------------------------------------------------------
# FreeBSD Ports driver — basic structure
# ---------------------------------------------------------------------------

class TestFreeBSDPortsDriver:

    def test_render_returns_required_keys(self):
        rec = _make_record()
        out = render_freebsd(rec)
        assert "Makefile" in out
        assert "distinfo" in out
        assert "pkg-descr" in out

    def test_makefile_contains_portname(self):
        rec = _make_record()
        mk = render_freebsd(rec)["Makefile"]
        assert "PORTNAME=" in mk
        assert "mypackage" in mk

    def test_makefile_contains_distversion(self):
        rec = _make_record()
        mk = render_freebsd(rec)["Makefile"]
        assert "DISTVERSION=" in mk
        assert "1.0.0" in mk

    def test_makefile_contains_maintainer(self):
        rec = _make_record()
        mk = render_freebsd(rec)["Makefile"]
        assert "MAINTAINER=" in mk
        assert "alice@example.com" in mk

    def test_makefile_default_maintainer_when_empty(self):
        rec = _make_record()
        rec["descriptive"]["maintainers"] = []
        mk = render_freebsd(rec)["Makefile"]
        assert "ports@FreeBSD.org" in mk

    def test_makefile_contains_comment(self):
        rec = _make_record()
        mk = render_freebsd(rec)["Makefile"]
        assert "COMMENT=" in mk
        assert "A test package" in mk

    def test_makefile_ends_with_include(self):
        rec = _make_record()
        mk = render_freebsd(rec)["Makefile"]
        assert mk.rstrip().endswith(".include <bsd.port.mk>")

    def test_makefile_stub_comment(self):
        rec = _make_record()
        rec["stub"] = True
        mk = render_freebsd(rec)["Makefile"]
        assert "THESEUS STUB" in mk

    def test_makefile_no_stub_comment_when_not_stub(self):
        rec = _make_record()
        rec["stub"] = False
        mk = render_freebsd(rec)["Makefile"]
        assert "THESEUS STUB" not in mk

    def test_distinfo_real_sha256(self):
        rec = _make_record()
        di = render_freebsd(rec)["distinfo"]
        assert "abc123" in di
        assert "SHA256" in di

    def test_distinfo_placeholder_when_no_sha256(self):
        rec = _make_record()
        rec["sources"][0].pop("sha256")
        di = render_freebsd(rec)["distinfo"]
        assert "STUB" in di or "0000" in di

    def test_distinfo_no_source(self):
        rec = _make_record()
        rec["sources"] = []
        di = render_freebsd(rec)["distinfo"]
        assert "STUB" in di or "no source" in di.lower()

    def test_license_mit(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["MIT"]
        mk = render_freebsd(rec)["Makefile"]
        assert "MIT" in mk

    def test_license_apache(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["Apache-2.0"]
        mk = render_freebsd(rec)["Makefile"]
        assert "APACHE20" in mk

    def test_license_gpl3(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["GPL-3.0"]
        mk = render_freebsd(rec)["Makefile"]
        assert "GPLv3" in mk

    def test_license_bsd2(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["BSD-2-Clause"]
        mk = render_freebsd(rec)["Makefile"]
        assert "BSD2CLAUSE" in mk

    def test_license_unknown_spdx(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["LicenseRef-Custom"]
        mk = render_freebsd(rec)["Makefile"]
        assert "UNKNOWN" in mk

    def test_empty_categories_defaults_to_misc(self):
        rec = _make_record()
        rec["descriptive"]["categories"] = []
        mk = render_freebsd(rec)["Makefile"]
        assert "misc" in mk

    def test_conflicts_in_makefile(self):
        rec = _make_record()
        rec["conflicts"] = ["other-pkg", "old-pkg"]
        mk = render_freebsd(rec)["Makefile"]
        assert "CONFLICTS=" in mk
        assert "other-pkg" in mk
        assert "old-pkg" in mk

    def test_no_conflicts_section_when_empty(self):
        rec = _make_record()
        rec["conflicts"] = []
        mk = render_freebsd(rec)["Makefile"]
        assert "CONFLICTS=" not in mk

    def test_cmake_uses(self):
        rec = _make_record()
        rec["build"]["system_kind"] = "cmake"
        mk = render_freebsd(rec)["Makefile"]
        assert "cmake" in mk

    def test_meson_uses(self):
        rec = _make_record()
        rec["build"]["system_kind"] = "meson"
        mk = render_freebsd(rec)["Makefile"]
        assert "meson" in mk

    def test_pkg_descr_contains_summary(self):
        rec = _make_record()
        descr = render_freebsd(rec)["pkg-descr"]
        assert "A test package" in descr

    def test_pkg_descr_contains_www(self):
        rec = _make_record()
        descr = render_freebsd(rec)["pkg-descr"]
        assert "https://example.com" in descr

    def test_comment_truncated_to_70(self):
        rec = _make_record()
        rec["descriptive"]["summary"] = "x" * 80
        mk = render_freebsd(rec)["Makefile"]
        # Find COMMENT line and check it is at most 70 chars of actual content
        for line in mk.splitlines():
            if "COMMENT=" in line:
                val = line.split("COMMENT=")[-1].strip()
                assert len(val) <= 70
                break

    def test_build_deps_stub_comment(self):
        rec = _make_record()
        rec["dependencies"]["build"] = ["openssl", "zlib"]
        mk = render_freebsd(rec)["Makefile"]
        assert "openssl" in mk
        assert "zlib" in mk
        assert "STUB" in mk

    def test_drivers_dict_contains_freebsd_ports(self):
        assert "freebsd_ports" in DRIVERS
        assert callable(DRIVERS["freebsd_ports"])


# ---------------------------------------------------------------------------
# Nixpkgs driver
# ---------------------------------------------------------------------------

class TestNixpkgsDriver:

    def test_render_returns_default_nix(self):
        rec = _make_record()
        out = render_nix(rec)
        assert "default.nix" in out

    def test_default_nix_contains_pname(self):
        rec = _make_record()
        nix = render_nix(rec)["default.nix"]
        assert 'pname = "mypackage"' in nix

    def test_default_nix_contains_version(self):
        rec = _make_record()
        nix = render_nix(rec)["default.nix"]
        assert 'version = "1.0.0"' in nix

    def test_stub_uses_fake_sha256(self):
        rec = _make_record()
        rec["stub"] = True
        rec["sources"][0].pop("sha256", None)
        nix = render_nix(rec)["default.nix"]
        assert "fakeSha256" in nix

    def test_real_sha256_used_when_present(self):
        rec = _make_record()
        rec["stub"] = False
        nix = render_nix(rec)["default.nix"]
        assert "abc123" in nix
        assert "fakeSha256" not in nix

    def test_cmake_in_native_build_inputs(self):
        rec = _make_record()
        rec["build"]["system_kind"] = "cmake"
        nix = render_nix(rec)["default.nix"]
        assert "cmake" in nix
        assert "nativeBuildInputs" in nix

    def test_meson_in_native_build_inputs(self):
        rec = _make_record()
        rec["build"]["system_kind"] = "meson"
        nix = render_nix(rec)["default.nix"]
        assert "meson" in nix
        assert "ninja" in nix

    def test_meta_contains_description(self):
        rec = _make_record()
        nix = render_nix(rec)["default.nix"]
        assert "description" in nix
        assert "A test package" in nix

    def test_meta_contains_homepage(self):
        rec = _make_record()
        nix = render_nix(rec)["default.nix"]
        assert "homepage" in nix
        assert "https://example.com" in nix

    def test_balanced_braces(self):
        rec = _make_record()
        nix = render_nix(rec)["default.nix"]
        assert nix.count("{") == nix.count("}")

    def test_stub_header_comment(self):
        rec = _make_record()
        rec["stub"] = True
        nix = render_nix(rec)["default.nix"]
        assert "THESEUS STUB" in nix

    def test_no_stub_comment_when_not_stub(self):
        rec = _make_record()
        rec["stub"] = False
        nix = render_nix(rec)["default.nix"]
        assert "THESEUS STUB" not in nix

    def test_go_builder(self):
        rec = _make_record()
        rec["build"]["system_kind"] = "go"
        nix = render_nix(rec)["default.nix"]
        assert "buildGoModule" in nix

    def test_rust_builder(self):
        rec = _make_record()
        rec["build"]["system_kind"] = "cargo"
        nix = render_nix(rec)["default.nix"]
        assert "rustPlatform.buildRustPackage" in nix

    def test_license_mit_mapping(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["MIT"]
        nix = render_nix(rec)["default.nix"]
        assert "licenses.mit" in nix

    def test_license_apache_mapping(self):
        rec = _make_record()
        rec["descriptive"]["license"] = ["Apache-2.0"]
        nix = render_nix(rec)["default.nix"]
        assert "licenses.asl20" in nix

    def test_no_source_url(self):
        rec = _make_record()
        rec["sources"] = []
        nix = render_nix(rec)["default.nix"]
        # Should still render without crashing, with a TODO
        assert "pname" in nix

    def test_drivers_dict_contains_nixpkgs(self):
        assert "nixpkgs" in DRIVERS
        assert callable(DRIVERS["nixpkgs"])

    def test_runtime_deps_in_propagated_build_inputs(self):
        rec = _make_record()
        rec["dependencies"]["runtime"] = ["openssl", "zlib"]
        nix = render_nix(rec)["default.nix"]
        assert "propagatedBuildInputs" in nix
        assert "openssl" in nix

    def test_host_deps_in_build_inputs(self):
        rec = _make_record()
        rec["dependencies"]["host"] = ["libevent"]
        nix = render_nix(rec)["default.nix"]
        assert "buildInputs" in nix
        assert "libevent" in nix
