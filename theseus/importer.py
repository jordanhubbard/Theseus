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
# Per-package dep fill (post-import pass) — batched evaluation
# ---------------------------------------------------------------------------
#
# Key design: one nix-instantiate call evaluates a whole batch of packages,
# amortising the ~5s nixpkgs import cost across BATCH_SIZE attrs.  Each attr
# is protected by tryEval(toJSON(...)) so a single bad package cannot kill
# the batch.  No --strict needed: toJSON forces full evaluation per-package,
# and tryEval catches anything that blows up.

_NIX_DEP_BATCH_HEADER = r"""
let
  pkgs = import {nixpkgs_path} {{}};
  safeName = d:
    let r = builtins.tryEval (d.pname or d.name or "");
    in if r.success then r.value else "";
  names = drv: builtins.filter (s: s != "") (map safeName drv);
  evalOne = attr:
    let r = builtins.tryEval {{
              build   = names (pkgs.${{attr}}.nativeBuildInputs or []);
              host    = names (pkgs.${{attr}}.buildInputs or []);
              runtime = names (pkgs.${{attr}}.propagatedBuildInputs or []);
            }};
    in if r.success then r.value
       else {{ build = []; host = []; runtime = []; _failed = true; }};
in {{
"""

_NIX_DEP_BATCH_FOOTER = "\n}\n"

# Nix attr names safe for use as unquoted identifiers; fall back to quoted.
_NIX_IDENT_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_\-\']*$')


def _nix_attr_key(attr: str) -> str:
    """Return a Nix attribute key expression for the given attr name."""
    if _NIX_IDENT_RE.match(attr):
        return attr
    escaped = attr.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _nix_str(attr: str) -> str:
    """Return a Nix string literal for the given value (always quoted)."""
    escaped = attr.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


_NIX_DEP_SINGLE_EXPR = r"""
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


def _nixpkgs_deps_one_direct(
    attr: str,
    nixpkgs_root: Path,
    *,
    timeout: int = 15,
) -> dict | None:
    """
    Evaluate deps for a single attr via --strict.  Used as fallback when batch
    evaluation fails (e.g. one package in the batch causes infinite recursion).
    """
    expr = _NIX_DEP_SINGLE_EXPR.format(
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


def _nixpkgs_deps_batch(
    attrs: list[str],
    nixpkgs_root: Path,
    *,
    timeout: int = 60,
    fallback_timeout: int = 3,
) -> dict[str, dict | None]:
    """
    Evaluate dep lists for a batch of nixpkgs attrs in a single nix-instantiate
    call (amortising the ~5s nixpkgs import cost).

    If the batch fails (e.g. one package causes infinite recursion that tryEval
    cannot catch), falls back to per-package --strict evals so the rest of the
    batch is not lost.

    Returns {attr: {build,host,runtime}} for each attr, or {attr: None} on failure.
    """
    entries = "\n".join(
        f"  {_nix_attr_key(a)} = evalOne {_nix_str(a)};"
        for a in attrs
    )
    expr = (
        _NIX_DEP_BATCH_HEADER.format(nixpkgs_path=nixpkgs_root.resolve())
        + entries
        + _NIX_DEP_BATCH_FOOTER
    )
    try:
        r = subprocess.run(
            ["nix-instantiate", "--strict", "--eval", "--json", "-E", expr],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            result = {}
            for a in attrs:
                v = data.get(a)
                if v is None or v.get("_failed"):
                    result[a] = None
                else:
                    result[a] = {
                        "build":   v.get("build", []),
                        "host":    v.get("host", []),
                        "runtime": v.get("runtime", []),
                    }
            return result
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass

    # Batch failed — fall back to per-package evals to isolate the bad one.
    return {
        a: _nixpkgs_deps_one_direct(a, nixpkgs_root, timeout=fallback_timeout)
        for a in attrs
    }


# Public single-attr variant for ad-hoc use and tests.
def _nixpkgs_deps_one(
    attr: str,
    nixpkgs_root: Path,
    *,
    timeout: int = 30,
) -> dict | None:
    """Evaluate deps for a single attr.  Thin wrapper around _nixpkgs_deps_batch."""
    results = _nixpkgs_deps_batch([attr], nixpkgs_root, timeout=timeout)
    return results.get(attr)


def fill_nixpkgs_deps(
    snapshot_dir: Path,
    nixpkgs_root: Path,
    *,
    timeout: int = 60,
    batch_size: int = 50,
    overwrite: bool = False,
) -> tuple[int, int, int]:
    """
    Walk snapshot_dir for nixpkgs records whose deps are all empty and fill them
    in using batched nix-instantiate evaluation (one nixpkgs import per batch).

    Returns (filled, skipped_already_have_deps, failed).
    overwrite=True forces re-evaluation even for records that already have deps.
    """
    filled = 0
    skipped = 0
    failed = 0

    # Collect records that need evaluation.
    records = sorted(snapshot_dir.glob("*.json"))
    total = len(records)

    # Two-pass: first scan to split into skip/todo, then batch-evaluate todo.
    todo: list[tuple[Path, dict, str]] = []   # (path, rec, attr)
    for path in records:
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
        todo.append((path, rec, attr))

    n_todo = len(todo)
    print(f"fill deps: {skipped} skipped (already filled), {n_todo} to evaluate "
          f"in batches of {batch_size}", file=sys.stderr)

    for batch_start in range(0, n_todo, batch_size):
        batch = todo[batch_start: batch_start + batch_size]
        attrs = [a for _, _, a in batch]

        results = _nixpkgs_deps_batch(attrs, nixpkgs_root, timeout=timeout)

        for (path, rec, attr) in batch:
            result = results.get(attr)
            if result is None:
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
                warnings = rec.get("provenance", {}).get("warnings", [])
                rec.setdefault("provenance", {})["warnings"] = [
                    w for w in warnings
                    if "infinite recursion" not in w and "deps not extracted" not in w
                ]
                filled += 1
            path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")

        done = min(batch_start + batch_size, n_todo)
        print(f"fill deps: {done}/{n_todo} evaluated "
              f"({filled} filled, {failed} failed)", file=sys.stderr, flush=True)

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
# HTTP utilities (stdlib only — no third-party deps)
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 15) -> dict | None:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    try:
        req = Request(url, headers={"User-Agent": "theseus/0.1 package-recipe-importer"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, json.JSONDecodeError, Exception):
        return None


# ---------------------------------------------------------------------------
# PEP 508 parser (minimal — name extraction only)
# ---------------------------------------------------------------------------

def _parse_pep508(req_str: str) -> str | None:
    """Extract the package name from a PEP 508 requirement string.

    Handles: ``requests>=2.0``, ``requests[security]>=2.0``,
    ``requests (>=2.0)``, ``requests; python_version>="3.6"``.
    Returns None for malformed strings.
    """
    s = req_str.split(";")[0].strip()
    m = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)", s)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Source repository helpers
# ---------------------------------------------------------------------------

_PERMISSIVE_LICENSE_PREFIXES = (
    "MIT", "BSD", "Apache", "ISC", "0BSD", "Unlicense", "Zlib",
    "OpenSSL", "curl", "PSF", "Python-",
)

_GPL_LICENSE_SUBSTRINGS = (
    "GPL", "AGPL", "LGPL", "copyleft",
)


def _license_is_permissive(license_str: str):
    """Return True if license is permissive, False if GPL-family, None if unknown."""
    if not license_str:
        return None
    upper = license_str.upper()
    if any(s.upper() in upper for s in _GPL_LICENSE_SUBSTRINGS):
        return False
    if any(license_str.startswith(p) for p in _PERMISSIVE_LICENSE_PREFIXES):
        return True
    return None


def _normalize_github_url(raw: str) -> str:
    """Normalize various GitHub URL forms to https://github.com/owner/repo."""
    url = raw.strip()
    # Strip git+ prefix
    if url.startswith("git+"):
        url = url[4:]
    # git://github.com/ → https://github.com/
    if url.startswith("git://github.com/"):
        url = "https://github.com/" + url[len("git://github.com/"):]
    # github:owner/repo shorthand
    if url.startswith("github:"):
        url = "https://github.com/" + url[7:]
    # Strip .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    # Bare owner/repo (no scheme, single slash, no dots in owner)
    if url and "/" in url and not url.startswith("http") and url.count("/") == 1:
        url = "https://github.com/" + url
    return url.strip()


def _pypi_source_repo(info: dict) -> str:
    """Extract source repository URL from PyPI package info.

    Priority: project_urls["Source"] > project_urls["Repository"] >
    project_urls["Code"] > project_urls["Source Code"] >
    home_page (if github.com).
    """
    project_urls = info.get("project_urls") or {}
    for key in ("Source", "Repository", "Code", "Source Code"):
        val = (project_urls.get(key) or "").strip()
        if val and "github.com" in val:
            return val
    # Non-GitHub explicit source URLs
    for key in ("Source", "Repository", "Code", "Source Code"):
        val = (project_urls.get(key) or "").strip()
        if val:
            return val
    # home_page if it looks like GitHub
    hp = (info.get("home_page") or "").strip()
    if hp and "github.com" in hp:
        return hp
    return ""


# ---------------------------------------------------------------------------
# PyPI importer
# ---------------------------------------------------------------------------

_PYPI_API = "https://pypi.org/pypi/{name}/json"


def import_pypi(packages: list[str], out_dir: Path, *, timeout: int = 15) -> int:
    """Fetch metadata for each package name from PyPI and write canonical records.

    Returns the count of successfully imported packages.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for pkg_name in packages:
        url = _PYPI_API.format(name=pkg_name)
        data = _fetch_json(url, timeout=timeout)
        if not data:
            print(f"  pypi: SKIP {pkg_name} (fetch failed)", file=sys.stderr)
            continue

        info = data.get("info", {})
        name = info.get("name", pkg_name)
        version = info.get("version", "")
        canonical_name = name.lower().replace("_", "-")

        # Source URL: prefer sdist tarball
        source_url = ""
        source_sha256 = ""
        for u in data.get("urls", []):
            if u.get("packagetype") == "sdist":
                source_url = u.get("url", "")
                source_sha256 = u.get("digests", {}).get("sha256", "")
                break
        if not source_url and data.get("urls"):
            u = data["urls"][0]
            source_url = u.get("url", "")
            source_sha256 = u.get("digests", {}).get("sha256", "")

        # Runtime deps from requires_dist (skip optional/extra deps)
        runtime_deps: list[str] = []
        seen: set[str] = set()
        for req in info.get("requires_dist") or []:
            if "extra ==" in req or "extra==" in req:
                continue
            dep = _parse_pep508(req)
            if dep:
                norm = dep.lower().replace("_", "-")
                if norm not in seen:
                    seen.add(norm)
                    runtime_deps.append(norm)

        # License
        license_str = (info.get("license") or "").strip()
        licenses = [license_str] if license_str else []

        # Homepage
        homepage = (info.get("home_page") or "").strip()
        if not homepage:
            for key in ("Homepage", "home_page", "Source", "Repository"):
                hp = ((info.get("project_urls") or {}).get(key) or "").strip()
                if hp:
                    homepage = hp
                    break

        source_repository = _pypi_source_repo(info)

        rec = {
            "schema_version": SCHEMA_VERSION,
            "identity": {
                "canonical_name": canonical_name,
                "canonical_id": f"pkg:{canonical_name}",
                "version": version,
                "ecosystem": "pypi",
                "ecosystem_id": name,
            },
            "descriptive": {
                "summary": (info.get("summary") or "").strip(),
                "homepage": homepage,
                "license": licenses,
                "categories": ["python"],
                "maintainers": [],
            },
            "conflicts": [],
            "sources": ([{
                "type": "sdist",
                "url": source_url,
                "sha256": source_sha256,
            }] if source_url else []),
            "dependencies": {
                "build": ["setuptools", "wheel"],
                "host": [],
                "runtime": runtime_deps,
                "test": [],
            },
            "build": {
                "system_kind": "pypi",
                "configure_args": [],
                "make_args": [],
            },
            "features": {},
            "platforms": {"include": [], "exclude": []},
            "patches": [],
            "tests": {},
            "provenance": {
                "generated_by": GENERATED_BY,
                "imported_at": IMPORTED_AT,
                "source_path": url,
                "source_repo_commit": None,
                "confidence": 0.9,
                "unmapped": [],
                "warnings": [],
            },
            "extensions": {
                "pypi": {
                    "requires_python": (info.get("requires_python") or "").strip(),
                    "classifiers": (info.get("classifiers") or [])[:10],
                    "source_repository": source_repository,
                }
            },
        }

        out_path = out_dir / f"{canonical_name}.json"
        out_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1

    print(f"pypi: imported {count}/{len(packages)}", file=sys.stderr)
    return count


# ---------------------------------------------------------------------------
# npm importer
# ---------------------------------------------------------------------------

_NPM_API = "https://registry.npmjs.org/{name}"


def _npm_canonical_name(pkg_name: str) -> str:
    """Normalize an npm package name to a filesystem-safe canonical form.

    Scoped packages: ``@scope/name`` → ``scope__name``.
    """
    if pkg_name.startswith("@"):
        return pkg_name.lstrip("@").replace("/", "__")
    return pkg_name


def import_npm(packages: list[str], out_dir: Path, *, timeout: int = 15) -> int:
    """Fetch metadata for each package name from the npm registry and write canonical records.

    Returns the count of successfully imported packages.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for pkg_name in packages:
        url_name = pkg_name.replace("/", "%2F")
        url = _NPM_API.format(name=url_name)
        data = _fetch_json(url, timeout=timeout)
        if not data:
            print(f"  npm: SKIP {pkg_name} (fetch failed)", file=sys.stderr)
            continue

        latest_ver = (data.get("dist-tags") or {}).get("latest", "")
        versions = data.get("versions") or {}
        ver_data = versions.get(latest_ver, {})
        if not ver_data and versions:
            latest_ver = list(versions.keys())[-1]
            ver_data = versions[latest_ver]

        canonical_name = _npm_canonical_name(pkg_name)

        dist = ver_data.get("dist") or {}
        source_url = dist.get("tarball", "")
        source_integrity = dist.get("integrity", "")

        runtime_deps = list((ver_data.get("dependencies") or {}).keys())
        build_deps = list((ver_data.get("devDependencies") or {}).keys())
        host_deps = list((ver_data.get("peerDependencies") or {}).keys())

        license_val = ver_data.get("license") or data.get("license") or ""
        if isinstance(license_val, dict):
            license_val = license_val.get("type", "")
        licenses = [str(license_val)] if license_val else []

        homepage = (ver_data.get("homepage") or data.get("homepage") or "").strip()
        description = (ver_data.get("description") or data.get("description") or "").strip()

        repo = ver_data.get("repository") or data.get("repository") or {}
        if isinstance(repo, str):
            repo = {"url": repo}
        repo_url = (repo.get("url") or "").strip()
        source_repository = _normalize_github_url(repo_url) if repo_url else ""

        keywords = (ver_data.get("keywords") or data.get("keywords") or [])[:10]

        rec = {
            "schema_version": SCHEMA_VERSION,
            "identity": {
                "canonical_name": canonical_name,
                "canonical_id": f"pkg:{canonical_name}",
                "version": latest_ver,
                "ecosystem": "npm",
                "ecosystem_id": pkg_name,
            },
            "descriptive": {
                "summary": description,
                "homepage": homepage or repo_url,
                "license": licenses,
                "categories": ["javascript"],
                "maintainers": [],
            },
            "conflicts": [],
            "sources": ([{
                "type": "tarball",
                "url": source_url,
                "integrity": source_integrity,
            }] if source_url else []),
            "dependencies": {
                "build": build_deps,
                "host": host_deps,
                "runtime": runtime_deps,
                "test": [],
            },
            "build": {
                "system_kind": "npm",
                "configure_args": [],
                "make_args": [],
            },
            "features": {},
            "platforms": {"include": [], "exclude": []},
            "patches": [],
            "tests": {},
            "provenance": {
                "generated_by": GENERATED_BY,
                "imported_at": IMPORTED_AT,
                "source_path": url,
                "source_repo_commit": None,
                "confidence": 0.85,
                "unmapped": [],
                "warnings": [],
            },
            "extensions": {
                "npm": {
                    "engines": ver_data.get("engines") or {},
                    "keywords": keywords,
                    "source_repository": source_repository,
                }
            },
        }

        out_path = out_dir / f"{canonical_name}.json"
        out_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1

    print(f"npm: imported {count}/{len(packages)}", file=sys.stderr)
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _read_package_list(path: Path) -> list[str]:
    """Read a newline-delimited package list file, stripping comments and blanks."""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            lines.append(line)
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Bootstrap canonical package recipe records from Nixpkgs, "
            "FreeBSD Ports, PyPI, and/or npm."
        )
    )
    ap.add_argument("--nixpkgs", type=Path, metavar="PATH",
                    help="Path to a Nixpkgs checkout")
    ap.add_argument("--ports", type=Path, metavar="PATH",
                    help="Path to a FreeBSD Ports checkout")
    ap.add_argument("--pypi-list", type=Path, metavar="FILE",
                    help="File containing PyPI package names (one per line)")
    ap.add_argument("--npm-list", type=Path, metavar="FILE",
                    help="File containing npm package names (one per line)")
    ap.add_argument("--out", type=Path, required=True, metavar="DIR",
                    help="Output snapshot directory")
    ap.add_argument("--timeout", type=int, default=15, metavar="SECS",
                    help="HTTP timeout for PyPI/npm fetches (default: 15)")
    args = ap.parse_args()

    if not any([args.nixpkgs, args.ports, args.pypi_list, args.npm_list]):
        ap.error("At least one of --nixpkgs, --ports, --pypi-list, or --npm-list must be provided.")

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

    if args.pypi_list:
        if not args.pypi_list.is_file():
            print(f"Error: --pypi-list path does not exist: {args.pypi_list}", file=sys.stderr)
            sys.exit(1)
        packages = _read_package_list(args.pypi_list)
        print(f"pypi: fetching {len(packages)} packages...", file=sys.stderr)
        count = import_pypi(packages, args.out / "pypi", timeout=args.timeout)
        stats["ecosystems"]["pypi"] = {"count": count, "requested": len(packages)}

    if args.npm_list:
        if not args.npm_list.is_file():
            print(f"Error: --npm-list path does not exist: {args.npm_list}", file=sys.stderr)
            sys.exit(1)
        packages = _read_package_list(args.npm_list)
        print(f"npm: fetching {len(packages)} packages...", file=sys.stderr)
        count = import_npm(packages, args.out / "npm", timeout=args.timeout)
        stats["ecosystems"]["npm"] = {"count": count, "requested": len(packages)}

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
