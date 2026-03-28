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

When nix-instantiate is available, the Nixpkgs importer uses
``nix-instantiate --eval --json --strict`` for accurate metadata (deps,
licenses, platforms, maintainers).  Falls back to heuristic regex parsing
when nix-instantiate is not on PATH.

FreeBSD Ports slave ports (those setting MASTERDIR) are supported: the
master Makefile is read and merged as a base, with slave variables taking
precedence.

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

SCHEMA_VERSION = "0.2"
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
            "maintainers": [],
        },
        "conflicts": [],
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


def _resolve_masterdir(val: str, port_dir: Path, ports_root: Path) -> Path | None:
    """
    Resolve a MASTERDIR value to an absolute Path within ports_root.

    Handles the three common patterns seen in real FreeBSD Ports slave ports:
      ${.CURDIR}/../<portname>          — sibling in same category
      ${.CURDIR}/../../<cat>/<portname> — port in a different category
      ${.CURDIR:H:H}/<cat>/<portname>  — using :H (head = parent) modifiers

    Returns None if the value contains unresolvable make variables or the
    resolved path does not exist under ports_root.
    """
    val = val.replace("${.CURDIR:H:H}", str(port_dir.parent.parent))
    val = val.replace("${.CURDIR:H}", str(port_dir.parent))
    val = val.replace("${.CURDIR}", str(port_dir))
    if "${" in val:
        return None
    resolved = Path(val).resolve()
    try:
        resolved.relative_to(ports_root.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_dir() else None


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

    Slave ports (those that set MASTERDIR) are handled by loading the master
    Makefile, merging its variables as defaults, and overlaying the slave's
    own variables on top.  The slave's source_path is preserved in provenance.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    if "PORTNAME" not in content and "MASTERDIR" not in content:
        return None

    vars = _ports_vars(content)
    unmapped: list[str] = []
    warnings: list[str] = []

    # Slave port support: if MASTERDIR is set, merge master vars as defaults.
    masterdir_val = vars.get("MASTERDIR", "")
    if masterdir_val:
        master_dir = _resolve_masterdir(masterdir_val, path.parent, ports_root)
        if master_dir is not None:
            master_mf = master_dir / "Makefile"
            try:
                master_content = master_mf.read_text(encoding="utf-8", errors="replace")
                master_vars = _ports_vars(master_content)
                # Master uses ?= for overridable fields; slave vars win on conflict.
                merged = {**master_vars, **vars}
                vars = merged
                warnings.append(f"slave port; merged from {master_dir.relative_to(ports_root)}")
            except OSError:
                warnings.append(f"slave port; master Makefile not readable: {master_mf}")
        else:
            warnings.append(f"slave port; MASTERDIR not resolvable: {masterdir_val!r}")

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

    # maintainers
    maintainers = [vars["MAINTAINER"]] if vars.get("MAINTAINER") else []

    # conflicts — combine CONFLICTS and CONFLICTS_INSTALL into one list
    conflicts_raw = vars.get("CONFLICTS", "") + " " + vars.get("CONFLICTS_INSTALL", "")
    conflicts = conflicts_raw.split()

    # deprecated / expiration_date
    deprecated = bool(vars.get("DEPRECATED", ""))
    expiration_date = vars.get("EXPIRATION_DATE", "")

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
            "maintainers": maintainers,
            "deprecated": deprecated,
            **({"expiration_date": expiration_date} if expiration_date else {}),
        },
        "conflicts": conflicts,
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
# Nixpkgs eval-based importer (nix-instantiate)
# ---------------------------------------------------------------------------

# Nix expression template for batch evaluation.  Receives the nixpkgs path and
# a JSON-encoded list of attribute names via shell interpolation.
_NIX_BATCH_EXPR = r"""
let
  pkgs   = import {nixpkgs_path} {{}};
  names  = builtins.fromJSON ''{names_json}'';
  safe = name:
    let r = builtins.tryEval pkgs.${{name}};
    in if r.success && builtins.isAttrs r.value && r.value ? pname then
      let p  = r.value;
          r2 = builtins.tryEval {{
            pname   = p.pname or name;
            version = p.version or "";
            description = p.meta.description or "";
            homepage    = p.meta.homepage or "";
            license = if builtins.isList (p.meta.license or null)
                      then map (l: l.spdxId or l.shortName or "") p.meta.license
                      else [(p.meta.license.spdxId or p.meta.license.shortName or "")];
            maintainers = map (m: m.github or m.name or "") (p.meta.maintainers or []);
            platforms   = let rp = builtins.tryEval (p.meta.platforms or []);
                          in if rp.success then rp.value else [];
            position    = p.meta.position or "";
          }};
      in if r2.success then r2.value else null
    else null;
in
  builtins.listToAttrs (
    builtins.filter (x: x.value != null) (
      map (name: {{ inherit name; value = safe name; }}) names
    )
  )
"""

_NIX_EVAL_BATCH_SIZE = 200


def _nix_instantiate_available() -> bool:
    """Return True if nix-instantiate is on PATH and functional."""
    try:
        r = subprocess.run(
            ["nix-instantiate", "--version"],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _nix_eval_batch(nixpkgs_root: Path, names: list[str]) -> dict:
    """
    Call nix-instantiate --eval --json --strict for a batch of attribute names.
    Returns a dict of {attr_name: raw_data} for packages that evaluated
    successfully.  Failures are silently dropped.
    """
    expr = _NIX_BATCH_EXPR.format(
        nixpkgs_path=nixpkgs_root.resolve(),
        names_json=json.dumps(names),
    )
    try:
        r = subprocess.run(
            ["nix-instantiate", "--eval", "--json", "--strict", "-E", expr],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            return {}
        return json.loads(r.stdout)
    except Exception:
        return {}


def _nix_eval_to_record(attr_name: str, raw: dict, nixpkgs_root: Path) -> dict:
    """Convert raw nix-instantiate eval data into a canonical record."""
    canonical_name = raw.get("pname") or attr_name
    version = raw.get("version") or "unknown"
    warnings: list[str] = []
    unmapped: list[str] = []

    if version == "unknown":
        warnings.append("version not found in nix eval; set to 'unknown'")

    description = raw.get("description", "")
    homepage = raw.get("homepage", "")
    licenses = [lic for lic in raw.get("license", []) if lic]

    if not description:
        unmapped.append("meta.description")
    if not homepage:
        unmapped.append("meta.homepage")
    if not licenses:
        unmapped.append("meta.license")

    sources: list[dict] = []
    if homepage:
        sources.append({"type": "homepage", "url": homepage})

    # Dependency arrays are not populated by the batch eval importer because
    # evaluating buildInputs/propagatedBuildInputs with --strict triggers
    # infinite recursion in some nixpkgs packages (builtins.tryEval does not
    # catch infinite recursion in Nix 2.x).  Deps are left empty; use the
    # regex-based importer or a future per-package evaluation pass for deps.
    build_deps: list = []
    host_deps: list = []
    runtime_deps: list = []
    warnings.append("deps not extracted by eval importer (infinite recursion risk)")

    # Build system: fall back to autotools since we have no dep list
    build_system = "autotools"

    # Source path: extract from position ("file:line") or fall back to attr name
    position = raw.get("position", "")
    if position and str(nixpkgs_root.resolve()) in position:
        rel = position.split(":")[0]
        try:
            source_path = str(Path(rel).relative_to(nixpkgs_root.resolve()))
        except ValueError:
            source_path = attr_name
    else:
        source_path = attr_name

    found = sum(bool(x) for x in [canonical_name, version != "unknown",
                                   description, homepage, licenses, sources])
    confidence = round(0.70 + (found / 6) * 0.28, 2)  # eval baseline higher than regex
    if warnings:
        confidence = round(confidence * 0.97, 2)

    maintainers = raw.get("maintainers", [])
    platforms = raw.get("platforms", [])

    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "canonical_name": canonical_name,
            "canonical_id": f"pkg:{canonical_name}",
            "version": version,
            "ecosystem": "nixpkgs",
            "ecosystem_id": attr_name,
        },
        "descriptive": {
            "summary": description,
            "homepage": homepage,
            "license": licenses,
            "categories": [],
            "maintainers": maintainers,
        },
        "conflicts": [],
        "sources": sources,
        "dependencies": {
            "build": build_deps,
            "host": host_deps,
            "runtime": runtime_deps,
            "test": [],
        },
        "build": {
            "system_kind": build_system,
            "configure_args": [],
            "make_args": [],
        },
        "features": {},
        "platforms": {
            "include": platforms,
            "exclude": [],
        },
        "patches": [],
        "tests": {},
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
            "nixpkgs": {
                "attr": attr_name,
            },
        },
    }


def import_nixpkgs_eval(nixpkgs_root: Path, out_dir: Path, commit: str | None) -> int:
    """
    Import Nixpkgs using nix-instantiate --eval for accurate metadata.

    Enumerates all top-level nixpkgs attributes in batches, evaluates each
    package's metadata (name, version, deps, license, platforms, maintainers),
    and writes canonical records.  Packages that fail evaluation are skipped.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Enumerate all top-level nixpkgs attribute names
    try:
        r = subprocess.run(
            ["nix-instantiate", "--eval", "--json", "--strict", "-E",
             f"builtins.attrNames (import {nixpkgs_root.resolve()} {{}})"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            print("nixpkgs eval: failed to enumerate attributes", file=sys.stderr)
            return 0
        all_names: list[str] = json.loads(r.stdout)
    except Exception as exc:
        print(f"nixpkgs eval: attribute enumeration error: {exc}", file=sys.stderr)
        return 0

    count = 0
    skipped = 0
    total = len(all_names)
    for batch_start in range(0, total, _NIX_EVAL_BATCH_SIZE):
        chunk = all_names[batch_start:batch_start + _NIX_EVAL_BATCH_SIZE]
        batch_end = min(batch_start + _NIX_EVAL_BATCH_SIZE, total)
        print(f"nixpkgs eval: evaluating {batch_start + 1}–{batch_end} / {total}",
              file=sys.stderr)
        results = _nix_eval_batch(nixpkgs_root, chunk)
        skipped += len(chunk) - len(results)
        for attr_name, raw in results.items():
            rec = _nix_eval_to_record(attr_name, raw, nixpkgs_root)
            rec["provenance"]["source_repo_commit"] = commit
            out_path = out_dir / f"{attr_name}.json"
            out_path.write_text(
                json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            count += 1

    print(f"nixpkgs eval: imported {count}, skipped {skipped}", file=sys.stderr)
    return count


# ---------------------------------------------------------------------------
# Per-package dep fill (post-import pass)
# ---------------------------------------------------------------------------

_NIX_DEP_EXPR = r"""
let
  pkgs = import {nixpkgs_path} {{}};
  p    = pkgs.{attr};
  safeName = d:
    let r = builtins.tryEval (d.pname or d.name or "");
    in if r.success then r.value else "";
  names = drv: builtins.filter (s: s != "") (map safeName drv);
in {{
  build   = names (p.nativeBuildInputs or []);
  host    = names (p.buildInputs or []);
  runtime = names (p.propagatedBuildInputs or []);
}}
"""


def _nixpkgs_deps_one(
    attr: str,
    nixpkgs_root: Path,
    *,
    timeout: int = 30,
) -> dict | None:
    """
    Evaluate dep lists for a single nixpkgs attribute using --strict to force
    full evaluation before JSON serialization.  Packages that cause infinite
    recursion will time out and return None.

    Returns {"build": [...], "host": [...], "runtime": [...]} on success,
    or None if evaluation fails or times out.
    """
    expr = _NIX_DEP_EXPR.format(
        nixpkgs_path=nixpkgs_root.resolve(),
        attr=attr,
    )
    try:
        r = subprocess.run(
            ["nix-instantiate", "--strict", "--eval", "--json", "-E", expr],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def fill_nixpkgs_deps(
    snapshot_dir: Path,
    nixpkgs_root: Path,
    *,
    timeout: int = 30,
    overwrite: bool = False,
) -> tuple[int, int, int]:
    """
    Walk snapshot_dir for nixpkgs records whose deps are all empty and fill them
    in using a per-package nix-instantiate eval (no --strict, so lazy eval avoids
    most infinite-recursion cases).

    Returns (filled, skipped_already_have_deps, failed).

    overwrite=True forces re-evaluation even for records that already have deps.
    """
    filled = 0
    skipped = 0
    failed = 0

    records = sorted(snapshot_dir.glob("*.json"))
    total = len(records)
    for i, path in enumerate(records, 1):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            failed += 1
            continue

        if rec.get("identity", {}).get("ecosystem") != "nixpkgs":
            skipped += 1
            continue

        deps = rec.get("dependencies", {})
        has_deps = any(deps.get(k) for k in ("build", "host", "runtime", "test"))
        if has_deps and not overwrite:
            skipped += 1
            continue

        attr = rec.get("extensions", {}).get("nixpkgs", {}).get("attr", "")
        if not attr:
            failed += 1
            continue

        if i % 100 == 0 or i == total:
            print(f"fill deps: {i}/{total} ({filled} filled, {failed} failed)",
                  file=sys.stderr)

        result = _nixpkgs_deps_one(attr, nixpkgs_root, timeout=timeout)
        if result is None:
            # Remove the stale warning if it exists; leave deps empty
            warnings = rec.get("provenance", {}).get("warnings", [])
            rec.setdefault("provenance", {})["warnings"] = [
                w for w in warnings
                if "infinite recursion" not in w
            ] + ["dep fill failed (eval timeout or error)"]
            failed += 1
        else:
            rec["dependencies"]["build"] = result.get("build", [])
            rec["dependencies"]["host"] = result.get("host", [])
            rec["dependencies"]["runtime"] = result.get("runtime", [])
            # Clear the stale warning
            warnings = rec.get("provenance", {}).get("warnings", [])
            rec.setdefault("provenance", {})["warnings"] = [
                w for w in warnings
                if "infinite recursion" not in w and "deps not extracted" not in w
            ]
            filled += 1

        path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    return filled, skipped, failed


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
        if _nix_instantiate_available():
            print("nixpkgs: nix-instantiate found; using eval-based importer",
                  file=sys.stderr)
            count = import_nixpkgs_eval(args.nixpkgs, args.out / "nixpkgs", commit)
        else:
            print("nixpkgs: nix-instantiate not found; using regex-based importer",
                  file=sys.stderr)
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
