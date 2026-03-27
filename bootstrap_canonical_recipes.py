#!/usr/bin/env python3
"""
bootstrap_canonical_recipes.py

Walk Nixpkgs and/or FreeBSD Ports source trees and produce canonical package
recipe records conforming to schema/package-recipe.schema.json.

Usage:
    python3 bootstrap_canonical_recipes.py \
        [--nixpkgs /path/to/nixpkgs] \
        [--ports /path/to/freebsd-ports] \
        --out ./snapshots/YYYY-MM-DD

At least one of --nixpkgs or --ports must be provided.

Parsing is heuristic (regex-based, not a full Nix or Make interpreter).
Confidence scores and warnings in each record reflect parse quality.

Output layout:
    <out>/nixpkgs/<name>.json
    <out>/freebsd_ports/<category>__<portname>.json
    <out>/manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "0.1"
GENERATED_BY = "bootstrap_canonical_recipes.py"
IMPORTED_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _get_git_commit(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=repo_path, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _str_match(text: str, pattern: str, flags: int = 0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Nixpkgs parser
# ---------------------------------------------------------------------------

# Common nixpkgs license attrs → SPDX-ish strings
_NIX_LICENSES: dict[str, str] = {
    "mit": "MIT",
    "gpl2": "GPL-2.0",
    "gpl2Only": "GPL-2.0-only",
    "gpl3": "GPL-3.0",
    "gpl3Only": "GPL-3.0-only",
    "lgpl2": "LGPL-2.0",
    "lgpl21": "LGPL-2.1",
    "lgpl3": "LGPL-3.0",
    "bsd2": "BSD-2-Clause",
    "bsd3": "BSD-3-Clause",
    "isc": "ISC",
    "mpl20": "MPL-2.0",
    "asl20": "Apache-2.0",
    "zlib": "Zlib",
    "publicDomain": "Unlicense",
    "openssl": "OpenSSL",
    "curl": "curl",
    "unlicense": "Unlicense",
}

# nativeBuildInputs token OR builder keyword → build system name.
# Order matters: more-specific entries first.
_NIX_BUILD_SYSTEMS: dict[str, str] = {
    "cmake": "cmake",
    "meson": "meson",
    "waf": "waf",
    "buildPerlPackage": "perl",
    "buildPerlModule": "perl",
    "perl": "perl",
    "buildPythonPackage": "python",
    "buildPythonApplication": "python",
    "python3": "python",
    "buildGoModule": "go",
    "buildGoPackage": "go",
    "go": "go",
    "buildRustPackage": "cargo",
    "buildNpmPackage": "npm",
    "buildNpmApplication": "npm",
    "mkYarnPackage": "yarn",
    "buildDunePackage": "dune",
    "buildOcamlPackage": "ocaml",
    "buildHaskellPackage": "cabal",
    "buildRubyGem": "gem",
    "buildPhpPackage": "php",
}


def _nix_build_system(content: str) -> str:
    for token, name in _NIX_BUILD_SYSTEMS.items():
        if re.search(r'\b' + re.escape(token) + r'\b', content):
            return name
    return "autotools"


def _nix_list_contents(content: str, var: str) -> list[str]:
    """Extract items from a Nix list binding: var = [ a b.c ... ];"""
    m = re.search(rf'\b{re.escape(var)}\s*=\s*\[([^\]]*)\]', content, re.DOTALL)
    if not m:
        return []
    tokens = m.group(1).split()
    result = []
    for t in tokens:
        t = t.strip().rstrip(';')
        if not t or t.startswith('#'):
            continue
        if t.startswith('"'):
            result.append(t.strip('"'))
        else:
            # take the last segment of an attribute path (e.g. pkgs.cmake → cmake)
            result.append(t.split('.')[-1])
    return result


def parse_nix_file(path: Path, nixpkgs_root: Path) -> dict | None:
    """
    Parse a nixpkgs default.nix and return a canonical record, or None if the
    file does not look like a package derivation.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Must resemble a derivation. This list covers the most common Nixpkgs
    # builders. Domain-specific builders not listed here are detected via the
    # generic "Platform" / "mkDerivation" fallthrough below.
    if not any(kw in content for kw in (
        "mkDerivation",
        "buildPythonPackage", "buildPythonApplication",
        "buildGoModule", "buildGoPackage",
        "buildRustPackage",
        "buildNpmPackage", "mkYarnPackage", "buildNpmApplication",
        "buildPerlPackage", "buildPerlModule",
        "buildDunePackage", "buildOcamlPackage",
        "buildHaskellPackage",
        "buildRubyGem",
        "buildPhpPackage",
        "stdenv.mkDerivation",
    )):
        return None

    rel = path.parent.relative_to(nixpkgs_root)
    source_path = str(rel)
    unmapped: list[str] = []
    warnings: list[str] = []

    # identity
    pname = _str_match(content, r'\bpname\s*=\s*"([^"]+)"')
    raw_name = _str_match(content, r'\bname\s*=\s*"([^"]+)"')
    canonical_name = pname
    version = _str_match(content, r'\bversion\s*=\s*"([^"]+)"')

    if not canonical_name:
        if raw_name:
            m = re.match(r'^(.+?)-(\d[\d.].*)$', raw_name)
            if m:
                canonical_name, version = m.group(1), m.group(2)
            else:
                canonical_name = raw_name
        else:
            return None

    if not version:
        version = "unknown"
        warnings.append("version not found; set to 'unknown'")

    # descriptive
    summary = _str_match(content, r'\bdescription\s*=\s*"([^"]+)"')
    if not summary:
        unmapped.append("description")

    homepage = _str_match(content, r'\bhomepage\s*=\s*"([^"]+)"')
    if not homepage:
        unmapped.append("homepage")

    raw_lic_blocks = re.findall(r'\blicenses?\s*=\s*(?:with\s+\S+;\s*)?\[?([^\];]+)\]?', content)
    license_tokens = []
    for block in raw_lic_blocks:
        license_tokens.extend(re.findall(r'licenses\.(\w+)', block))
    licenses = [_NIX_LICENSES.get(t, t) for t in license_tokens]
    if not licenses:
        unmapped.append("license")

    # sources
    sources: list[dict] = []
    if homepage:
        sources.append({"type": "homepage", "url": homepage})
    for url in re.findall(r'\burl\s*=\s*"([^"]+)"', content):
        sources.append({"type": "archive", "url": url})
    if not sources:
        unmapped.append("src.url")

    # dependencies
    build_deps = _nix_list_contents(content, "nativeBuildInputs")
    host_deps = _nix_list_contents(content, "buildInputs")
    runtime_deps = _nix_list_contents(content, "propagatedBuildInputs")
    check_deps = (
        _nix_list_contents(content, "checkInputs")
        + _nix_list_contents(content, "nativeCheckInputs")
    )

    # build
    build_system = _nix_build_system(content)
    configure_flags = _nix_list_contents(content, "configureFlags")
    make_flags = _nix_list_contents(content, "makeFlags")
    phases_m = re.search(r'\bphases\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
    phases = phases_m.group(1).split() if phases_m else ["configure", "build", "check", "install"]

    # tests
    tests: dict = {}
    do_check = bool(re.search(r'\bdoCheck\s*=\s*true', content))
    no_check = bool(re.search(r'\bdoCheck\s*=\s*false', content))
    if do_check or (not no_check and "checkPhase" in content):
        tests["has_check_phase"] = True

    # patches
    patches: list[dict] = []
    pm = re.search(r'\bpatches\s*=\s*\[([^\]]*)\]', content, re.DOTALL)
    if pm:
        for p in re.findall(r'([\w./]+\.patch)', pm.group(1)):
            patches.append({"path": p, "reason": "nixpkgs patch"})
        if patches:
            warnings.append("patch reasons not parsed from source")

    # platforms
    platforms_include = _nix_list_contents(content, "platforms")
    platforms_exclude = _nix_list_contents(content, "badPlatforms")

    # confidence: proportion of key fields found
    found = sum(bool(x) for x in [
        canonical_name, version != "unknown", summary, homepage, licenses, sources,
    ])
    confidence = round(0.5 + (found / 6) * 0.45, 2)
    if warnings:
        confidence = round(confidence * 0.95, 2)

    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "canonical_name": canonical_name,
            "canonical_id": f"pkg:{canonical_name}",
            "version": version,
            "ecosystem": "nixpkgs",
            "ecosystem_id": source_path,
        },
        "descriptive": {
            "summary": summary or "",
            "homepage": homepage or "",
            "license": licenses,
            "categories": [],
        },
        "sources": sources,
        "dependencies": {
            "build": build_deps,
            "host": host_deps,
            "runtime": runtime_deps,
            "test": check_deps,
        },
        "build": {
            "system_kind": build_system,
            "configure_flags": configure_flags,
            "make_flags": make_flags,
            "phases": phases,
        },
        "features": {},
        "platforms": {
            "include": platforms_include,
            "exclude": platforms_exclude,
        },
        "patches": patches,
        "tests": tests,
        "provenance": {
            "generated_by": GENERATED_BY,
            "imported_at": IMPORTED_AT,
            "source_path": source_path,
            "source_repo_commit": None,
            "confidence": confidence,
            "unmapped": unmapped,
            "warnings": warnings,
        },
        "extensions": {
            "nixpkgs": {"recipe_file": path.name},
        },
    }


# ---------------------------------------------------------------------------
# FreeBSD Ports parser
# ---------------------------------------------------------------------------

_PORTS_BUILD_SYSTEMS: dict[str, str] = {
    "cmake": "cmake",
    "meson": "meson",
    "waf": "waf",
    "perl5": "perl",
    "python": "python",
    "go": "go",
    "cargo": "cargo",
}


def _ports_vars(content: str) -> dict[str, str]:
    """
    Parse Makefile variable assignments, handling continuation lines.
    Returns VAR → value (stripped).
    """
    lines: list[str] = []
    buf = ""
    for line in content.splitlines():
        if line.endswith("\\"):
            buf += line[:-1] + " "
        else:
            buf += line
            lines.append(buf)
            buf = ""
    if buf:
        lines.append(buf)

    result: dict[str, str] = {}
    for line in lines:
        m = re.match(r'^(\w+)\s*[?+:!]?=\s*(.*)', line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


def _ports_dep_names(dep_str: str) -> list[str]:
    """
    Extract portnames from a FreeBSD Ports dependency string.
    Each dep looks like: lib.so:category/portname or file:category/portname>=version
    """
    names = []
    for dep in dep_str.split():
        m = re.search(r':[\w-]+/([\w-]+)', dep)
        if m:
            names.append(m.group(1))
    return names


def parse_ports_makefile(path: Path, ports_root: Path) -> dict | None:
    """
    Parse a FreeBSD Ports Makefile and return a canonical record, or None if
    the file does not look like a port.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    if "PORTNAME" not in content:
        return None

    vars = _ports_vars(content)
    unmapped: list[str] = []
    warnings: list[str] = []

    canonical_name = vars.get("PORTNAME", "").strip()
    if not canonical_name:
        return None

    version = vars.get("PORTVERSION") or vars.get("DISTVERSION", "")
    if not version:
        version = "unknown"
        warnings.append("version not found; set to 'unknown'")

    rel = path.parent.relative_to(ports_root)
    source_path = str(rel)

    # descriptive
    summary = vars.get("COMMENT", "")
    if not summary:
        unmapped.append("COMMENT")

    homepage = vars.get("WWW", "")
    if not homepage:
        unmapped.append("WWW")

    raw_license = vars.get("LICENSE", "")
    licenses = raw_license.split() if raw_license else []
    if not licenses:
        unmapped.append("LICENSE")

    categories = vars.get("CATEGORIES", "").split()

    # sources
    sources: list[dict] = []
    if homepage:
        sources.append({"type": "homepage", "url": homepage})
    master_sites = vars.get("MASTER_SITES", "")
    if master_sites:
        first = master_sites.split()[0]
        sources.append({"type": "master_sites", "url": first})
    if not sources:
        unmapped.append("MASTER_SITES")

    # dependencies
    build_deps = _ports_dep_names(vars.get("BUILD_DEPENDS", ""))
    host_deps = _ports_dep_names(vars.get("LIB_DEPENDS", ""))
    runtime_deps = _ports_dep_names(vars.get("RUN_DEPENDS", ""))
    test_deps = _ports_dep_names(vars.get("TEST_DEPENDS", ""))

    # build system from USES
    uses_str = vars.get("USES", "")
    uses = [u.split(":")[0] for u in uses_str.split()]
    build_system = "freebsd_ports_make"
    for use_token, bname in _PORTS_BUILD_SYSTEMS.items():
        if use_token in uses:
            build_system = bname
            break

    configure_args = vars.get("CONFIGURE_ARGS", vars.get("CMAKE_ARGS", "")).split()
    make_args = vars.get("MAKE_ARGS", "").split()

    # features
    options = vars.get("OPTIONS_DEFINE", "").split()
    features = {"options_define": options} if options else {}

    # tests
    tests: dict = {}
    if vars.get("TEST_TARGET") or "test" in content.lower():
        tests["has_test_target"] = True

    # patches — enumerate files/patch-* if the directory exists
    patches: list[dict] = []
    files_dir = path.parent / "files"
    if files_dir.is_dir():
        for pf in sorted(files_dir.glob("patch-*")):
            patches.append({"path": f"files/{pf.name}", "reason": "freebsd ports patch"})
        if patches:
            warnings.append("patch reasons not parsed from source")

    # platforms
    only_for = vars.get("ONLY_FOR_ARCHS", "")
    not_for = vars.get("NOT_FOR_ARCHS", "")

    # confidence
    found = sum(bool(x) for x in [
        canonical_name, version != "unknown", summary, homepage, licenses, sources,
    ])
    confidence = round(0.55 + (found / 6) * 0.40, 2)
    if warnings:
        confidence = round(confidence * 0.95, 2)

    raw_vars_sample = {k: vars[k] for k in ("CATEGORIES", "PORTNAME") if k in vars}

    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "canonical_name": canonical_name,
            "canonical_id": f"pkg:{canonical_name}",
            "version": version,
            "ecosystem": "freebsd_ports",
            "ecosystem_id": source_path,
        },
        "descriptive": {
            "summary": summary,
            "homepage": homepage,
            "license": licenses,
            "categories": categories,
        },
        "sources": sources,
        "dependencies": {
            "build": build_deps,
            "host": host_deps,
            "runtime": runtime_deps,
            "test": test_deps,
        },
        "build": {
            "system_kind": build_system,
            "configure_args": configure_args,
            "make_args": make_args,
            "uses": uses,
        },
        "features": features,
        "platforms": {
            "include": only_for.split() if only_for else [],
            "exclude": not_for.split() if not_for else [],
        },
        "patches": patches,
        "tests": tests,
        "provenance": {
            "generated_by": GENERATED_BY,
            "imported_at": IMPORTED_AT,
            "source_path": source_path,
            "source_repo_commit": None,
            "confidence": confidence,
            "unmapped": unmapped,
            "warnings": warnings,
        },
        "extensions": {
            "freebsd_ports": {"raw_vars": raw_vars_sample},
        },
    }


# ---------------------------------------------------------------------------
# Import runners
# ---------------------------------------------------------------------------

# Top-level Nixpkgs infrastructure directories to skip (checked against
# the first path component only, to avoid false matches on names like "mylib").
_NIX_SKIP_TOP = {"lib", "nixos", "doc", "maintainers"}


def _nix_should_skip(nix_file: Path, nixpkgs_root: Path) -> bool:
    parts = nix_file.relative_to(nixpkgs_root).parts
    if not parts:
        return True
    if parts[0] in _NIX_SKIP_TOP:
        return True
    # Skip pkgs/top-level/
    if len(parts) >= 2 and parts[0] == "pkgs" and parts[1] == "top-level":
        return True
    return False


def import_nixpkgs(nixpkgs_root: Path, out_dir: Path, commit: str | None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0

    for nix_file in sorted(nixpkgs_root.rglob("default.nix")):
        if _nix_should_skip(nix_file, nixpkgs_root):
            continue

        rec = parse_nix_file(nix_file, nixpkgs_root)
        if rec is None:
            skipped += 1
            continue

        rec["provenance"]["source_repo_commit"] = commit
        name = rec["identity"]["canonical_name"]
        out_path = out_dir / f"{name}.json"
        idx = 1
        while out_path.exists():
            out_path = out_dir / f"{name}_{idx}.json"
            idx += 1

        out_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1

    print(f"nixpkgs: imported {count}, skipped {skipped}", file=sys.stderr)
    return count


def import_ports(ports_root: Path, out_dir: Path, commit: str | None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0

    # FreeBSD Ports: category/portname/Makefile
    for makefile in sorted(ports_root.glob("*/*/Makefile")):
        rec = parse_ports_makefile(makefile, ports_root)
        if rec is None:
            skipped += 1
            continue

        rec["provenance"]["source_repo_commit"] = commit
        parts = makefile.parent.relative_to(ports_root).parts
        file_stem = "__".join(parts)
        out_path = out_dir / f"{file_stem}.json"
        out_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1

    print(f"freebsd_ports: imported {count}, skipped {skipped}", file=sys.stderr)
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Bootstrap canonical package recipe records from Nixpkgs "
            "and/or FreeBSD Ports."
        )
    )
    ap.add_argument("--nixpkgs", type=Path, metavar="PATH",
                    help="Path to a Nixpkgs checkout")
    ap.add_argument("--ports", type=Path, metavar="PATH",
                    help="Path to a FreeBSD Ports checkout")
    ap.add_argument("--out", type=Path, required=True, metavar="DIR",
                    help="Output snapshot directory")
    args = ap.parse_args()

    if not args.nixpkgs and not args.ports:
        ap.error("At least one of --nixpkgs or --ports must be provided.")

    args.out.mkdir(parents=True, exist_ok=True)

    stats: dict = {
        "imported_at": IMPORTED_AT,
        "output_dir": str(args.out),
        "ecosystems": {},
    }

    if args.nixpkgs:
        if not args.nixpkgs.is_dir():
            print(f"Error: --nixpkgs path does not exist: {args.nixpkgs}", file=sys.stderr)
            sys.exit(1)
        commit = _get_git_commit(args.nixpkgs)
        count = import_nixpkgs(args.nixpkgs, args.out / "nixpkgs", commit)
        stats["ecosystems"]["nixpkgs"] = {"count": count, "commit": commit}

    if args.ports:
        if not args.ports.is_dir():
            print(f"Error: --ports path does not exist: {args.ports}", file=sys.stderr)
            sys.exit(1)
        commit = _get_git_commit(args.ports)
        count = import_ports(args.ports, args.out / "freebsd_ports", commit)
        stats["ecosystems"]["freebsd_ports"] = {"count": count, "commit": commit}

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
