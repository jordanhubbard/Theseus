"""
theseus/fabric.py — git-backed OSS knowledge fabric.

The working tree under fabric/packages/ is the database. Each committed JSON
file is one package fingerprint (identity, repository, license, outbound
dependencies). Reverse dependencies are derived by scanning that graph.
Historical queries use `git show <rev>:path` and `git log`; there is no
SQL store.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Iterable, Iterator, Optional
from urllib.parse import urlparse


SCHEMA_VERSION = "1.1"
SUPPORTED_SCHEMA_VERSIONS = ("1.0", "1.1")
FINGERPRINT_KIND = "oss_fingerprint"
PACKAGES_RELDIR = "fabric/packages"
GENERATED_BY = "theseus.fabric"
PRIORITY = {
    "primary": ["provenance", "tracking", "dependencies"],
    "secondary": ["recreation"],
}

_SCOPES = ("runtime", "build", "host", "test")
_REPO_HOSTS = (
    "github.com",
    "gitlab.com",
    "gitlab.freedesktop.org",
    "gitlab.gnome.org",
    "gitlab.kitware.com",
    "salsa.debian.org",
    "invent.kde.org",
    "code.videolan.org",
    "gitlab.xiph.org",
    "bitbucket.org",
    "codeberg.org",
    "git.savannah.gnu.org",
    "savannah.gnu.org",
    "cgit.freedesktop.org",
    "git.sr.ht",
    "sr.ht",
    "pagure.io",
)
_FORGE_TWO_PART = {
    "github.com",
    "bitbucket.org",
    "codeberg.org",
}
_FORGE_GITLAB = {
    "gitlab.com",
    "gitlab.freedesktop.org",
    "gitlab.gnome.org",
    "gitlab.kitware.com",
    "salsa.debian.org",
    "invent.kde.org",
    "code.videolan.org",
    "gitlab.xiph.org",
}
# gitlab.com itself is too noisy (language forks). Named unique promotion
# is restricted to these hosted forges plus github.com/<pkg>/<pkg>.
_TRUSTED_NAMED_GITLAB = {
    "gitlab.freedesktop.org",
    "gitlab.gnome.org",
    "gitlab.kitware.com",
    "salsa.debian.org",
    "invent.kde.org",
    "code.videolan.org",
    "gitlab.xiph.org",
}
_UNEXPANDED_URL = re.compile(r"\$\{|\$\(")
_GNU_SOFTWARE = re.compile(
    r"^https?://(?:www\.)?gnu\.org/software/([A-Za-z0-9+._-]+)/?",
    re.IGNORECASE,
)
_SKIP_HOMEPAGE_HOSTS = {
    "cran.r-project.org",
    "rforge.net",
    "bioconductor.org",
}
_PATH_JUNK = (
    "/-/",
    "/commit/",
    "/commits/",
    "/blob/",
    "/tree/",
    "/releases/",
    "/archive/",
    "/compare/",
    "/pull/",
    "/issues/",
    "/wiki/",
)
_LICENSE_ALIASES = {
    "zlib": "Zlib",
    "ZLIB": "Zlib",
    "Zlib": "Zlib",
    "mit": "MIT",
    "MIT": "MIT",
    "isc": "ISC",
    "ISC": "ISC",
    "apache-2.0": "Apache-2.0",
    "Apache-2.0": "Apache-2.0",
    "Apache 2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "bsd-2-clause": "BSD-2-Clause",
    "BSD-2-Clause": "BSD-2-Clause",
    "BSD2CLAUSE": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "BSD-3-Clause": "BSD-3-Clause",
    "BSD3CLAUSE": "BSD-3-Clause",
    "bsd": "BSD-3-Clause",
    "openssl": "OpenSSL",
    "OpenSSL": "OpenSSL",
    "psfl": "PSF-2.0",
    "PSF": "PSF-2.0",
    "python-2.0": "Python-2.0",
    "GPLv2+": "GPL-2.0-or-later",
    "GPLv2": "GPL-2.0-only",
    "GPLv3+": "GPL-3.0-or-later",
    "GPLv3": "GPL-3.0-only",
    "GPL-2.0-or-later": "GPL-2.0-or-later",
    "GPL-3.0-or-later": "GPL-3.0-or-later",
    "LGPL21+": "LGPL-2.1-or-later",
    "LGPL20+": "LGPL-2.0-or-later",
    "LGPL-2.1-or-later": "LGPL-2.1-or-later",
    "MPL-2.0": "MPL-2.0",
}

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._+-]+")
_GITHUBISH = re.compile(
    r"^https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org|codeberg\.org)"
    r"/([^/#?\s]+)/([^/#?\s]+)",
    re.IGNORECASE,
)
_DEP_NOISE = re.compile(r"^(\$\{|#|@\{)")


# ---------------------------------------------------------------------------
# Paths and names
# ---------------------------------------------------------------------------

def repo_root_from(start: Optional[Path] = None) -> Path:
    here = Path(start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "schema" / "package-recipe.schema.json").is_file():
            return candidate
    return here


def packages_dir(root: Path) -> Path:
    return root / PACKAGES_RELDIR


def package_slug(name: str) -> str:
    slug = _UNSAFE_NAME.sub("_", (name or "").strip())
    if not slug or slug in (".", ".."):
        raise ValueError("invalid package name: %r" % name)
    return slug


def package_filename(name: str) -> str:
    return package_slug(name) + ".json"


def fingerprint_relpath(name: str) -> str:
    return PACKAGES_RELDIR + "/" + package_filename(name)


def fingerprint_path(root: Path, name: str) -> Path:
    return packages_dir(root) / package_filename(name)


def normalize_name(name: str) -> str:
    return (name or "").strip().lower().replace("_", "-")


def dump_fingerprint(record: dict) -> str:
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def write_fingerprint(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_fingerprint(record), encoding="utf-8")


# ---------------------------------------------------------------------------
# Repository / license extraction
# ---------------------------------------------------------------------------

def normalize_license_token(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    return _LICENSE_ALIASES.get(text, _LICENSE_ALIASES.get(text.lower(), text))


def _strip_git_suffix(path_part: str) -> str:
    part = path_part.strip().rstrip("/")
    if part.endswith(".git"):
        part = part[:-4]
    return part


def _recipe_portname(recipe: dict) -> str:
    ports = (recipe.get("extensions") or {}).get("freebsd_ports") or {}
    raw = ports.get("raw_vars") if isinstance(ports, dict) else None
    if isinstance(raw, dict):
        name = (raw.get("PORTNAME") or "").strip()
        if name and "${" not in name:
            return name
    return ((recipe.get("identity") or {}).get("canonical_name") or "").strip()


def _expand_recipe_url(url: str, recipe: Optional[dict] = None) -> str:
    text = url.strip()
    if not recipe:
        return text
    portname = _recipe_portname(recipe)
    if not portname:
        return text
    text = text.replace("${PORTNAME}", portname)
    text = text.replace("${PORTNAME:tl}", portname.lower())
    text = text.replace("${PORTNAME:S/2//}", portname.replace("2", "", 1))
    return text


def _pkg_tokens(name: str) -> set:
    pkg = (name or "").lower().replace("+", "")
    tokens = {pkg}
    if pkg.startswith("lib") and len(pkg) > 4:
        tokens.add(pkg[3:])
    return tokens


def _url_owner_repo(url: str) -> tuple:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    parts = [p for p in (parsed.path or "").strip("/").split("/") if p]
    last = parts[-1].lower() if parts else ""
    if last.endswith(".git"):
        last = last[:-4]
    owner = parts[0].lower() if parts else ""
    return host, owner, last


def _name_matches_repo(package_name: str, last: str) -> bool:
    pkg = (package_name or "").lower().replace("+", "")
    last = (last or "").lower()
    if last in _pkg_tokens(package_name) or pkg == last:
        return True
    if last.startswith("lib") and last[3:] == pkg:
        return True
    return False


def normalize_repo_url(url: str, recipe: Optional[dict] = None) -> Optional[str]:
    if not url:
        return None
    text = _expand_recipe_url(url, recipe)
    leftover = _UNEXPANDED_URL.search(text)
    if leftover:
        prefix = text[: leftover.start()].rstrip("/-_")
        if prefix.count("/") >= 4:
            text = prefix
        else:
            return None
    if _UNEXPANDED_URL.search(text):
        return None
    if text.startswith("git+"):
        text = text[4:]
    if text.startswith("git://"):
        text = "https://" + text[6:]
    text = text.split("#", 1)[0].strip()
    if not re.match(r"^https?://", text, re.IGNORECASE):
        match = _GITHUBISH.match(text)
        if match:
            host, owner, repo = match.group(1), match.group(2), match.group(3)
            repo = _strip_git_suffix(repo)
            return "https://%s/%s/%s" % (host.lower(), owner, repo)
        return None
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or ""
    for marker in _PATH_JUNK:
        if marker in path:
            path = path.split(marker, 1)[0]
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if host == "cgit.freedesktop.org" and len(parts) >= 2:
        return "https://gitlab.freedesktop.org/%s/%s" % (parts[0], parts[1])
    if "savannah.gnu.org" in host:
        if len(parts) >= 2 and parts[0] in ("projects", "git", "cgit"):
            return "https://git.savannah.gnu.org/git/%s.git" % _strip_git_suffix(parts[1])
        return None
    if host in _FORGE_TWO_PART:
        if len(parts) < 2:
            return None
        return "https://%s/%s/%s" % (host, parts[0], _strip_git_suffix(parts[1]))
    if host in _FORGE_GITLAB:
        if len(parts) < 2:
            return None
        kept = parts[:4]
        kept[-1] = _strip_git_suffix(kept[-1])
        return "https://%s/%s" % (host, "/".join(kept))
    for known in _REPO_HOSTS:
        if known == host or host.endswith("." + known):
            cleaned = text.rstrip("/")
            if cleaned.endswith(".git"):
                cleaned = cleaned[:-4]
            return cleaned
    return None


def _explicit_repository(recipe: dict) -> Optional[tuple]:
    """Return (url, source_field) from ecosystem-specific metadata."""
    extensions = recipe.get("extensions") or {}
    for eco_key, field in (
        ("pypi", "source_repository"),
        ("npm", "source_repository"),
        ("npm", "repository"),
        ("nixpkgs", "source_repository"),
        ("freebsd_ports", "source_repository"),
        ("cargo", "repository"),
        ("crates", "repository"),
    ):
        block = extensions.get(eco_key) or {}
        if not isinstance(block, dict):
            continue
        value = block.get(field)
        if isinstance(value, dict):
            value = value.get("url") or value.get("git")
        if isinstance(value, str) and value.strip():
            url = normalize_repo_url(value, recipe) or (
                None if _UNEXPANDED_URL.search(value) else value.strip()
            )
            if url:
                return url, "%s.%s" % (eco_key, field)
    return None


def _homepage_tokens(homepage: str) -> list:
    if not homepage or not isinstance(homepage, str):
        return []
    return [tok for tok in re.split(r"[\s,]+", homepage.strip()) if tok]


def _github_pages_repo(homepage: str, package_name: str) -> Optional[str]:
    parsed = urlparse(homepage.strip())
    host = (parsed.hostname or "").lower()
    match = re.match(r"^([a-z0-9-]+)\.github\.io$", host)
    if not match:
        return None
    user = match.group(1)
    path = (parsed.path or "").strip("/")
    repo = path.split("/")[0] if path else user
    pkg = (package_name or "").lower().replace("+", "")
    if user == pkg or repo.lower() == pkg:
        return "https://github.com/%s/%s" % (user, repo)
    return None


def _gnu_savannah_repo(homepage: str, package_name: str) -> Optional[str]:
    token = homepage.strip()
    match = _GNU_SOFTWARE.match(token)
    if not match:
        return None
    gnu = match.group(1).lower()
    pkg = (package_name or "").lower()
    if gnu == pkg or pkg.startswith(gnu + "-") or gnu.startswith(pkg.split("-")[0]):
        return "https://git.savannah.gnu.org/git/%s.git" % gnu
    return None


def _freedesktop_project_homepage(homepage: str, package_name: str) -> Optional[str]:
    parsed = urlparse(homepage.strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    match = re.match(r"^([a-z0-9-]+)\.freedesktop\.org$", host)
    if not match:
        return None
    project = match.group(1)
    pkg = (package_name or "").lower().replace("+", "")
    if project == pkg:
        return "https://gitlab.freedesktop.org/%s/%s" % (project, project)
    return None


def _homepage_corroborates(homepage: str, package_name: str) -> bool:
    if not homepage:
        return False
    parsed = urlparse(homepage.strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in _SKIP_HOMEPAGE_HOSTS:
        return False
    pkg = (package_name or "").lower().replace("+", "")
    first = host.split(".")[0]
    return first == pkg or first == pkg + "build"


def _unique_list(urls: list) -> Optional[str]:
    ordered = []
    seen = set()
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            ordered.append(url)
    if len(ordered) == 1:
        return ordered[0]
    return None


def _github_name_owners(candidates: list, package_name: str) -> set:
    """GitHub owners whose repo name is or contains the package name."""
    pkg = (package_name or "").lower().replace("+", "")
    tokens = _pkg_tokens(package_name)
    owners = set()
    for url in candidates:
        host, owner, last = _url_owner_repo(url)
        if host != "github.com" or not owner:
            continue
        if last in tokens or pkg in last:
            owners.add(owner)
    return owners


def _ambiguous_github_name(candidates: list, package_name: str) -> bool:
    return len(_github_name_owners(candidates, package_name)) > 1


def _savannah_among_candidates(candidates: list, package_name: str) -> Optional[str]:
    hits = []
    tokens = _pkg_tokens(package_name)
    for url in candidates:
        host, _owner, last = _url_owner_repo(url)
        if "savannah.gnu.org" in host and last in tokens:
            hits.append("https://git.savannah.gnu.org/git/%s.git" % last)
    return _unique_list(hits)


def _unique_trusted_named(candidates: list, package_name: str) -> Optional[str]:
    hits = []
    tokens = _pkg_tokens(package_name)
    ambiguous = _ambiguous_github_name(candidates, package_name)
    for url in candidates:
        host, owner, last = _url_owner_repo(url)
        if not _name_matches_repo(package_name, last):
            continue
        if host in _TRUSTED_NAMED_GITLAB or "savannah.gnu.org" in host:
            hits.append(url)
        elif (
            host in _FORGE_TWO_PART
            and not ambiguous
            and (owner in tokens or owner == last)
        ):
            hits.append(url)
    return _unique_list(hits)


def _unique_github_owned_by_pkg(candidates: list, package_name: str) -> Optional[str]:
    if _ambiguous_github_name(candidates, package_name):
        return None
    tokens = _pkg_tokens(package_name)
    owned = []
    for url in candidates:
        host, owner, _last = _url_owner_repo(url)
        if host == "github.com" and owner in tokens:
            owned.append(url)
    return _unique_list(owned)


def _homepage_corroborated_github(
    candidates: list, homepage: str, package_name: str
) -> Optional[str]:
    if not _homepage_corroborates(homepage, package_name):
        return None
    if _ambiguous_github_name(candidates, package_name):
        return None
    hits = []
    for url in candidates:
        host, _owner, last = _url_owner_repo(url)
        if host == "github.com" and _name_matches_repo(package_name, last):
            hits.append(url)
    return _unique_list(hits)


def _candidate_urls(recipe: dict) -> list:
    found = []
    seen = set()

    def add(url):
        for token in _homepage_tokens(url) if url else []:
            norm = normalize_repo_url(token, recipe)
            if norm and norm not in seen:
                seen.add(norm)
                found.append(norm)

    homepage = (recipe.get("descriptive") or {}).get("homepage")
    if isinstance(homepage, str):
        add(homepage)
    for source in recipe.get("sources") or []:
        if isinstance(source, dict):
            url = source.get("url")
            if isinstance(url, str):
                add(url)
    return found


def _unique_git_clone_url(recipe: dict) -> Optional[str]:
    found = []
    seen = set()
    for source in recipe.get("sources") or []:
        if not isinstance(source, dict):
            continue
        raw = source.get("url") or ""
        if ".patch" in raw or "/commit/" in raw:
            continue
        if source.get("type") not in ("git", "git-clone") and not raw.rstrip("/").endswith(".git"):
            continue
        norm = normalize_repo_url(raw, recipe)
        if norm and norm not in seen:
            seen.add(norm)
            found.append(norm)
    if len(found) == 1:
        return found[0]
    return None


def extract_repository(recipe: dict) -> dict:
    explicit = _explicit_repository(recipe)
    candidates = _candidate_urls(recipe)
    ident = (recipe.get("identity") or {}).get("canonical_name") or ""
    homepage = (recipe.get("descriptive") or {}).get("homepage") or ""

    def result(url, source, confidence):
        kind = "git" if url and any(h in url.lower() for h in _REPO_HOSTS) else None
        extra = [c for c in candidates if c != url]
        return {
            "url": url,
            "kind": kind,
            "web": url,
            "confidence": confidence,
            "source": source,
            "candidates": extra,
        }

    if explicit:
        url, source = explicit
        return result(url, source, 0.95)
    for token in _homepage_tokens(homepage):
        from_home = normalize_repo_url(token, recipe)
        if from_home:
            return result(from_home, "homepage", 0.8)
        pages = _github_pages_repo(token, ident)
        if pages:
            return result(pages, "github_pages", 0.75)
        gnu = _gnu_savannah_repo(token, ident)
        if gnu:
            return result(gnu, "gnu_savannah_convention", 0.75)
        fdo = _freedesktop_project_homepage(token, ident)
        if fdo:
            return result(fdo, "freedesktop_gitlab_convention", 0.75)
    clone = _unique_git_clone_url(recipe)
    if clone:
        return result(clone, "sources.git", 0.85)
    savannah = _savannah_among_candidates(candidates, ident)
    if savannah:
        return result(savannah, "savannah_among_candidates", 0.8)
    trusted = _unique_trusted_named(candidates, ident)
    if trusted:
        return result(trusted, "unique_named_forge", 0.75)
    owned = _unique_github_owned_by_pkg(candidates, ident)
    if owned:
        return result(owned, "github_owner_matches_package", 0.7)
    corroborated = _homepage_corroborated_github(candidates, homepage, ident)
    if corroborated:
        return result(corroborated, "homepage_corroborated_github", 0.7)
    return {
        "url": None,
        "kind": None,
        "web": None,
        "confidence": 0.0,
        "source": None,
        "candidates": candidates,
    }


def extract_license(recipe: dict) -> dict:
    raw = []
    for item in (recipe.get("descriptive") or {}).get("license") or []:
        if isinstance(item, str) and item.strip():
            raw.append(item.strip())
    spdx = []
    seen = set()
    for token in raw:
        mapped = normalize_license_token(token)
        if mapped and mapped not in seen:
            seen.add(mapped)
            spdx.append(mapped)
    confidence = 0.9 if spdx else 0.0
    return {"spdx": spdx, "raw": raw, "confidence": confidence}


def _is_noisy_dep(name: str) -> bool:
    if not name or not name.strip():
        return True
    text = name.strip()
    if _DEP_NOISE.match(text):
        return True
    if text in ("#", "-"):
        return True
    if "/" in text or text.endswith(".so"):
        return True
    return False


def extract_depends_on(recipe: dict) -> list:
    deps = recipe.get("dependencies") or {}
    ecosystem = (recipe.get("identity") or {}).get("ecosystem")
    out = []
    seen = set()
    for scope in _SCOPES:
        for item in deps.get(scope) or []:
            if not isinstance(item, str):
                continue
            name = item.strip()
            if _is_noisy_dep(name):
                continue
            key = (normalize_name(name), scope, ecosystem or "")
            if key in seen:
                continue
            seen.add(key)
            entry = {"name": name, "scope": scope}
            if ecosystem:
                entry["ecosystem"] = ecosystem
            out.append(entry)
    return out


def extract_dropped_dependencies(recipe: dict) -> list:
    deps = recipe.get("dependencies") or {}
    dropped = []
    seen = set()
    for scope in _SCOPES:
        for item in deps.get(scope) or []:
            if not isinstance(item, str):
                continue
            name = item.strip()
            if not _is_noisy_dep(name):
                continue
            key = (name, scope)
            if key in seen:
                continue
            seen.add(key)
            dropped.append({
                "name": name,
                "scope": scope,
                "reason": "unresolved_token",
            })
    return dropped


def extract_distributions(recipe: dict) -> list:
    out = []
    seen = set()
    for source in recipe.get("sources") or []:
        if not isinstance(source, dict):
            continue
        item = {}
        for key in ("type", "url", "sha256", "filename", "size"):
            if source.get(key) is not None:
                item[key] = source[key]
        if not item:
            continue
        marker = (item.get("type"), item.get("url"), item.get("sha256"))
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out


def _uniq_str(values) -> list:
    out = []
    seen = set()
    for value in values or []:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _zsdl_for(root: Path, canonical_name: str) -> Optional[str]:
    rel = "zspecs/%s.zspec.zsdl" % canonical_name
    if (root / rel).is_file():
        return rel
    slug = package_slug(canonical_name)
    alt = "zspecs/%s.zspec.zsdl" % slug
    if alt != rel and (root / alt).is_file():
        return alt
    return None


# ---------------------------------------------------------------------------
# Recipe → fingerprint
# ---------------------------------------------------------------------------

def recipe_to_fingerprint(recipe: dict, source_path: str, root: Optional[Path] = None) -> dict:
    identity = recipe.get("identity") or {}
    descriptive = recipe.get("descriptive") or {}
    name = identity.get("canonical_name")
    if not name:
        raise ValueError("recipe missing identity.canonical_name (%s)" % source_path)
    canonical_id = identity.get("canonical_id") or ("pkg:%s" % name)
    aliases = []
    if canonical_id != ("pkg:%s" % name):
        aliases.append("pkg:%s" % name)
    orig_id = identity.get("ecosystem_id")
    if orig_id and orig_id != name and orig_id not in aliases:
        aliases.append(orig_id)

    repo = extract_repository(recipe)
    license_info = extract_license(recipe)
    eco = {
        "ecosystem": identity.get("ecosystem") or "unknown",
        "ecosystem_id": identity.get("ecosystem_id"),
        "version": identity.get("version"),
        "canonical_id": canonical_id,
    }
    evidence = {
        "recipes": [source_path],
        "behavioral_spec": None,
        "recreation": "secondary",
    }
    if root is not None:
        evidence["behavioral_spec"] = _zsdl_for(root, name)

    src_prov = recipe.get("provenance") or {}
    confidence = src_prov.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    imported_at = src_prov.get("imported_at") or _now_iso()
    source_path_orig = src_prov.get("source_path")
    source_commit = src_prov.get("source_repo_commit")
    build_kind = (recipe.get("build") or {}).get("system_kind")

    tracking = {
        "ingested_at": _now_iso(),
        "recipe_count": 1,
        "maintainers": _uniq_str(descriptive.get("maintainers") or []),
        "categories": _uniq_str(descriptive.get("categories") or []),
        "source_paths": _uniq_str([source_path_orig] if source_path_orig else []),
        "source_repo_commits": _uniq_str([source_commit] if source_commit else []),
        "build_systems": _uniq_str([build_kind] if build_kind else []),
        "distributions": extract_distributions(recipe),
        "dropped_dependencies": extract_dropped_dependencies(recipe),
        "dep_edges": 0,
        "dep_resolved": 0,
        "dep_dangling": 0,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": FINGERPRINT_KIND,
        "identity": {
            "canonical_name": name,
            "canonical_id": canonical_id,
            "aliases": aliases,
        },
        "repository": repo,
        "license": license_info,
        "homepage": descriptive.get("homepage"),
        "summary": descriptive.get("summary"),
        "ecosystems": [eco],
        "depends_on": extract_depends_on(recipe),
        "evidence": evidence,
        "priority": {
            "primary": list(PRIORITY["primary"]),
            "secondary": list(PRIORITY["secondary"]),
        },
        "tracking": tracking,
        "provenance": {
            "generated_by": GENERATED_BY,
            "imported_at": imported_at,
            "confidence": float(confidence),
            "sources": [
                {
                    "path": source_path,
                    "kind": "package_recipe",
                    "imported_at": src_prov.get("imported_at"),
                    "generated_by": src_prov.get("generated_by"),
                    "source_path": source_path_orig,
                    "source_repo_commit": source_commit,
                    "confidence": src_prov.get("confidence"),
                    "unmapped": list(src_prov.get("unmapped") or []),
                }
            ],
            "warnings": list(src_prov.get("warnings") or []),
        },
    }


def _text_quality(text: Optional[str]) -> float:
    if not text:
        return -1.0
    score = min(len(text), 120) / 120.0
    if "${" in text:
        score -= 5.0
    if "Linux CentOS" in text:
        score -= 3.0
    if text.startswith("https://"):
        score += 0.2
    return score


def _pick_better_text(current: Optional[str], incoming: Optional[str]) -> Optional[str]:
    if _text_quality(incoming) > _text_quality(current):
        return incoming
    return current


def _pick_better_repo(current: dict, incoming: dict) -> dict:
    cur_c = float(current.get("confidence") or 0)
    inc_c = float(incoming.get("confidence") or 0)
    winner = incoming if inc_c > cur_c else current
    loser = current if winner is incoming else incoming
    candidates = []
    seen = set()
    urls = [winner.get("url"), loser.get("url")]
    urls.extend(winner.get("candidates") or [])
    urls.extend(loser.get("candidates") or [])
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            candidates.append(url)
    merged = dict(winner)
    if merged.get("url") in candidates:
        candidates = [c for c in candidates if c != merged.get("url")]
    merged["candidates"] = candidates
    return merged


def merge_fingerprints(parts: list) -> dict:
    if not parts:
        raise ValueError("merge_fingerprints requires at least one record")
    base = json.loads(json.dumps(parts[0]))
    aliases = list(base.get("identity", {}).get("aliases") or [])
    ecosystems = list(base.get("ecosystems") or [])
    eco_keys = {(e.get("ecosystem"), e.get("ecosystem_id"), e.get("version")) for e in ecosystems}
    depends = list(base.get("depends_on") or [])
    dep_keys = {
        (normalize_name(d.get("name", "")), d.get("scope"), d.get("ecosystem") or "")
        for d in depends
    }
    recipes = list((base.get("evidence") or {}).get("recipes") or [])
    sources = list((base.get("provenance") or {}).get("sources") or [])
    warnings = list((base.get("provenance") or {}).get("warnings") or [])
    spdx = list((base.get("license") or {}).get("spdx") or [])
    raw = list((base.get("license") or {}).get("raw") or [])
    confidences = [float((base.get("provenance") or {}).get("confidence") or 0)]
    repo = dict(base.get("repository") or {})
    homepage = base.get("homepage")
    summary = base.get("summary")
    spec = (base.get("evidence") or {}).get("behavioral_spec")
    imported_at = (base.get("provenance") or {}).get("imported_at") or _now_iso()
    track = dict(base.get("tracking") or {})
    maintainers = list(track.get("maintainers") or [])
    categories = list(track.get("categories") or [])
    source_paths = list(track.get("source_paths") or [])
    source_commits = list(track.get("source_repo_commits") or [])
    build_systems = list(track.get("build_systems") or [])
    distributions = list(track.get("distributions") or [])
    dropped = list(track.get("dropped_dependencies") or [])
    dist_keys = {
        (d.get("type"), d.get("url"), d.get("sha256")) for d in distributions if isinstance(d, dict)
    }
    drop_keys = {(d.get("name"), d.get("scope")) for d in dropped if isinstance(d, dict)}

    for extra in parts[1:]:
        ident = extra.get("identity") or {}
        for alias in ident.get("aliases") or []:
            if alias not in aliases:
                aliases.append(alias)
        cid = ident.get("canonical_id")
        if cid and cid not in aliases and cid != base["identity"]["canonical_id"]:
            aliases.append(cid)
        for eco in extra.get("ecosystems") or []:
            key = (eco.get("ecosystem"), eco.get("ecosystem_id"), eco.get("version"))
            if key not in eco_keys:
                eco_keys.add(key)
                ecosystems.append(eco)
        for dep in extra.get("depends_on") or []:
            key = (normalize_name(dep.get("name", "")), dep.get("scope"), dep.get("ecosystem") or "")
            if key not in dep_keys:
                dep_keys.add(key)
                depends.append(dep)
        for rec_path in (extra.get("evidence") or {}).get("recipes") or []:
            if rec_path not in recipes:
                recipes.append(rec_path)
        extra_spec = (extra.get("evidence") or {}).get("behavioral_spec")
        if extra_spec and not spec:
            spec = extra_spec
        extra_track = extra.get("tracking") or {}
        maintainers = _uniq_str(maintainers + list(extra_track.get("maintainers") or []))
        categories = _uniq_str(categories + list(extra_track.get("categories") or []))
        source_paths = _uniq_str(source_paths + list(extra_track.get("source_paths") or []))
        source_commits = _uniq_str(source_commits + list(extra_track.get("source_repo_commits") or []))
        build_systems = _uniq_str(build_systems + list(extra_track.get("build_systems") or []))
        for dist in extra_track.get("distributions") or []:
            if not isinstance(dist, dict):
                continue
            marker = (dist.get("type"), dist.get("url"), dist.get("sha256"))
            if marker in dist_keys:
                continue
            dist_keys.add(marker)
            distributions.append(dist)
        for drop in extra_track.get("dropped_dependencies") or []:
            if not isinstance(drop, dict):
                continue
            marker = (drop.get("name"), drop.get("scope"))
            if marker in drop_keys:
                continue
            drop_keys.add(marker)
            dropped.append(drop)
        for src in (extra.get("provenance") or {}).get("sources") or []:
            sources.append(src)
        for warn in (extra.get("provenance") or {}).get("warnings") or []:
            if warn not in warnings:
                warnings.append(warn)
        lic = extra.get("license") or {}
        for token in lic.get("spdx") or []:
            if token not in spdx:
                spdx.append(token)
        for token in lic.get("raw") or []:
            if token not in raw:
                raw.append(token)
        confidences.append(float((extra.get("provenance") or {}).get("confidence") or 0))
        repo = _pick_better_repo(repo, extra.get("repository") or {})
        homepage = _pick_better_text(homepage, extra.get("homepage"))
        summary = _pick_better_text(summary, extra.get("summary"))
        extra_imported = (extra.get("provenance") or {}).get("imported_at")
        if extra_imported and extra_imported > imported_at:
            imported_at = extra_imported

    base["identity"]["aliases"] = aliases
    base["ecosystems"] = ecosystems
    base["depends_on"] = depends
    base["repository"] = repo
    base["homepage"] = homepage
    base["summary"] = summary
    base["license"] = {
        "spdx": spdx,
        "raw": raw,
        "confidence": 0.9 if spdx else 0.0,
    }
    base["evidence"] = {
        "recipes": recipes,
        "behavioral_spec": spec,
        "recreation": "secondary",
    }
    base["priority"] = {
        "primary": list(PRIORITY["primary"]),
        "secondary": list(PRIORITY["secondary"]),
    }
    base["tracking"] = {
        "ingested_at": _now_iso(),
        "recipe_count": len(recipes),
        "maintainers": maintainers,
        "categories": categories,
        "source_paths": source_paths,
        "source_repo_commits": source_commits,
        "build_systems": build_systems,
        "distributions": distributions,
        "dropped_dependencies": dropped,
        "dep_edges": 0,
        "dep_resolved": 0,
        "dep_dangling": 0,
    }
    base["schema_version"] = SCHEMA_VERSION
    base["provenance"] = {
        "generated_by": GENERATED_BY,
        "imported_at": imported_at,
        "confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        "sources": sources,
        "warnings": warnings,
    }
    return base


def iter_recipe_files(paths: Iterable[Path]) -> Iterator[Path]:
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix == ".json":
            if path.name != "manifest.json":
                yield path
            continue
        if not path.is_dir():
            continue
        for found in sorted(path.rglob("*.json")):
            if found.name == "manifest.json":
                continue
            yield found


def load_recipe(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if "identity" not in data:
        return None
    if (data.get("kind") == FINGERPRINT_KIND) or (data.get("schema_version") == SCHEMA_VERSION and "depends_on" in data):
        return None
    return data


def _recipe_relpath(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def convert_recipe_path(root: Path, path: Path):
    """Load one recipe file and convert it. None means skip."""
    recipe = load_recipe(path)
    if recipe is None:
        return None
    name = (recipe.get("identity") or {}).get("canonical_name")
    if not name:
        return None
    return name, recipe_to_fingerprint(recipe, _recipe_relpath(root, path), root=root)


def worker_count(jobs: int, nfiles: int) -> int:
    if nfiles <= 1:
        return 1
    if jobs is not None and jobs > 0:
        return max(1, int(jobs))
    cpus = os.cpu_count() or 2
    return max(2, min(8, cpus, nfiles))


def build_name_index(records: list) -> dict:
    index = {}
    for rec in records:
        ident = rec.get("identity") or {}
        cname = ident.get("canonical_name")
        if not cname:
            continue
        index[normalize_name(cname)] = cname
        for alias in ident.get("aliases") or []:
            key = normalize_name(alias)
            if key and key not in index:
                index[key] = cname
        for eco in rec.get("ecosystems") or []:
            eid = eco.get("ecosystem_id")
            if not eid:
                continue
            key = normalize_name(eid)
            if key and key not in index:
                index[key] = cname
    return index


def resolve_dependencies(records: list) -> None:
    """Annotate outbound deps with resolved/dangling against the fabric index."""
    index = build_name_index(records)
    for rec in records:
        resolved = 0
        dangling = 0
        for dep in rec.get("depends_on") or []:
            target = index.get(normalize_name(dep.get("name") or ""))
            if target:
                dep["resolved"] = True
                dep["resolved_to"] = target
                resolved += 1
            else:
                dep["resolved"] = False
                if "resolved_to" in dep:
                    del dep["resolved_to"]
                dangling += 1
        tracking = rec.setdefault("tracking", {})
        tracking["dep_edges"] = resolved + dangling
        tracking["dep_resolved"] = resolved
        tracking["dep_dangling"] = dangling


def ingest(
    root: Path,
    recipe_dirs: Iterable[Path],
    out_dir: Optional[Path] = None,
    jobs: int = 0,
) -> dict:
    """Convert package-recipe records into committed fingerprints in parallel."""
    root = Path(root).resolve()
    dest = Path(out_dir) if out_dir is not None else packages_dir(root)
    dest.mkdir(parents=True, exist_ok=True)
    files = list(iter_recipe_files(recipe_dirs))
    workers = worker_count(jobs, len(files))
    if workers <= 1:
        converted = [convert_recipe_path(root, path) for path in files]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            converted = list(pool.map(partial(convert_recipe_path, root), files))
    grouped = defaultdict(list)
    skipped = 0
    for item in converted:
        if item is None:
            skipped += 1
            continue
        name, fingerprint = item
        grouped[name].append(fingerprint)
    records = []
    for name in sorted(grouped, key=lambda n: n.lower()):
        records.append(merge_fingerprints(grouped[name]))
    resolve_dependencies(records)
    written = []
    for record in records:
        name = record["identity"]["canonical_name"]
        write_fingerprint(dest / package_filename(name), record)
        written.append(name)
    return {
        "written": len(written),
        "packages": written,
        "skipped": skipped,
        "out_dir": str(dest),
        "jobs": workers,
        "recipes": len(files),
    }


# ---------------------------------------------------------------------------
# Git-backed store
# ---------------------------------------------------------------------------

def _git(root: Path, args: list, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def git_show(root: Path, rev: str, relpath: str) -> str:
    result = _git(root, ["show", "%s:%s" % (rev, relpath)])
    if result.returncode != 0:
        raise FileNotFoundError(result.stderr.strip() or "git show failed for %s:%s" % (rev, relpath))
    return result.stdout


def git_list_packages(root: Path, rev: str) -> list:
    result = _git(root, ["ls-tree", "-r", "--name-only", rev, "--", PACKAGES_RELDIR])
    if result.returncode != 0:
        raise FileNotFoundError(result.stderr.strip() or "git ls-tree failed for %s" % rev)
    names = []
    prefix = PACKAGES_RELDIR + "/"
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith(prefix) and line.endswith(".json"):
            names.append(Path(line).stem)
    return sorted(names, key=lambda n: n.lower())


def git_history(root: Path, name: str) -> list:
    rel = fingerprint_relpath(name)
    result = _git(
        root,
        ["log", "--follow", "--pretty=format:%H\t%cI\t%s", "--", rel],
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git log failed")
    entries = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        entries.append({"commit": parts[0], "date": parts[1], "subject": parts[2]})
    return entries


class FabricStore:
    """Query fingerprints from the working tree or a git revision."""

    def __init__(self, root: Path, rev: Optional[str] = None):
        self.root = Path(root).resolve()
        self.rev = rev
        self._cache = None

    def _load_all(self) -> dict:
        if self._cache is not None:
            return self._cache
        records = {}
        if self.rev:
            for name in git_list_packages(self.root, self.rev):
                try:
                    text = git_show(self.root, self.rev, fingerprint_relpath(name))
                    rec = json.loads(text)
                except (FileNotFoundError, ValueError):
                    continue
                records[normalize_name(name)] = rec
        else:
            directory = packages_dir(self.root)
            if directory.is_dir():
                for path in sorted(directory.glob("*.json")):
                    try:
                        rec = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        continue
                    if not isinstance(rec, dict):
                        continue
                    name = (rec.get("identity") or {}).get("canonical_name") or path.stem
                    records[normalize_name(name)] = rec
        self._cache = records
        return records

    def __len__(self) -> int:
        return len(self._load_all())

    def names(self) -> list:
        recs = self._load_all()
        return sorted(
            ((r.get("identity") or {}).get("canonical_name") or k) for k, r in recs.items()
        )

    def get(self, name: str) -> Optional[dict]:
        return self._load_all().get(normalize_name(name))

    def all(self) -> list:
        recs = self._load_all()
        return [recs[k] for k in sorted(recs)]

    def deps(self, name: str, scope: Optional[str] = None) -> list:
        rec = self.get(name)
        if rec is None:
            raise KeyError(name)
        items = list(rec.get("depends_on") or [])
        if scope:
            items = [d for d in items if d.get("scope") == scope]
        return items

    def rdeps(self, name: str, scope: Optional[str] = None) -> list:
        target = normalize_name(name)
        found = []
        for rec in self.all():
            pkg = (rec.get("identity") or {}).get("canonical_name")
            for dep in rec.get("depends_on") or []:
                if normalize_name(dep.get("name") or "") != target:
                    continue
                if scope and dep.get("scope") != scope:
                    continue
                found.append({
                    "name": pkg,
                    "scope": dep.get("scope"),
                    "ecosystem": dep.get("ecosystem"),
                })
        return found

    def query(
        self,
        name: Optional[str] = None,
        license: Optional[str] = None,
        repo: Optional[str] = None,
        ecosystem: Optional[str] = None,
        has_repo: Optional[bool] = None,
        missing_license: bool = False,
    ) -> list:
        name_q = normalize_name(name) if name else None
        lic_q = (license or "").strip().lower()
        repo_q = (repo or "").strip().lower()
        eco_q = (ecosystem or "").strip().lower()
        matches = []
        for rec in self.all():
            ident = rec.get("identity") or {}
            cname = ident.get("canonical_name") or ""
            if name_q and name_q not in normalize_name(cname) and name_q not in normalize_name(" ".join(ident.get("aliases") or [])):
                continue
            lic = rec.get("license") or {}
            tokens = [t.lower() for t in (lic.get("spdx") or []) + (lic.get("raw") or [])]
            if lic_q and not any(lic_q in t for t in tokens):
                continue
            if missing_license and (lic.get("spdx") or lic.get("raw")):
                continue
            repository = rec.get("repository") or {}
            url = repository.get("url") or ""
            cands = " ".join(repository.get("candidates") or [])
            if repo_q and repo_q not in (url + " " + cands).lower():
                continue
            if has_repo is True and not url:
                continue
            if has_repo is False and url:
                continue
            if eco_q:
                ecos = [e.get("ecosystem", "").lower() for e in rec.get("ecosystems") or []]
                if eco_q not in ecos:
                    continue
            matches.append(rec)
        return matches

    def stats(self) -> dict:
        recs = self.all()
        with_repo = 0
        with_license = 0
        with_deps = 0
        with_rdeps = 0
        with_spec = 0
        with_commit = 0
        with_maintainers = 0
        with_distributions = 0
        dep_resolved = 0
        dep_dangling = 0
        dep_edges = 0
        dropped_deps = 0
        ecosystems = defaultdict(int)
        licenses = defaultdict(int)
        rdep_names = set()
        for rec in recs:
            if (rec.get("repository") or {}).get("url"):
                with_repo += 1
            lic = rec.get("license") or {}
            if lic.get("spdx") or lic.get("raw"):
                with_license += 1
                for token in lic.get("spdx") or lic.get("raw") or []:
                    licenses[token] += 1
            if rec.get("depends_on"):
                with_deps += 1
            if (rec.get("evidence") or {}).get("behavioral_spec"):
                with_spec += 1
            tracking = rec.get("tracking") or {}
            if tracking.get("source_repo_commits"):
                with_commit += 1
            if tracking.get("maintainers"):
                with_maintainers += 1
            if tracking.get("distributions"):
                with_distributions += 1
            dep_resolved += int(tracking.get("dep_resolved") or 0)
            dep_dangling += int(tracking.get("dep_dangling") or 0)
            dep_edges += int(tracking.get("dep_edges") or 0)
            dropped_deps += len(tracking.get("dropped_dependencies") or [])
            for eco in rec.get("ecosystems") or []:
                ecosystems[eco.get("ecosystem") or "unknown"] += 1
            for dep in rec.get("depends_on") or []:
                rdep_names.add(normalize_name(dep.get("name") or ""))
        for rec in recs:
            cname = normalize_name((rec.get("identity") or {}).get("canonical_name") or "")
            if cname in rdep_names:
                with_rdeps += 1
        total = len(recs)
        return {
            "packages": total,
            "with_repository": with_repo,
            "with_license": with_license,
            "with_depends_on": with_deps,
            "with_dependents": with_rdeps,
            "with_behavioral_spec": with_spec,
            "with_source_commit": with_commit,
            "with_maintainers": with_maintainers,
            "with_distributions": with_distributions,
            "dep_edges": dep_edges,
            "dep_resolved": dep_resolved,
            "dep_dangling": dep_dangling,
            "dropped_dependencies": dropped_deps,
            "missing_repository": total - with_repo,
            "missing_license": total - with_license,
            "ecosystems": dict(sorted(ecosystems.items())),
            "licenses": dict(sorted(licenses.items(), key=lambda kv: (-kv[1], kv[0]))),
            "rev": self.rev,
        }

    def validate(self) -> list:
        errors = []
        for rec in self.all():
            name = (rec.get("identity") or {}).get("canonical_name") or "<unknown>"
            for err in validate_fingerprint(rec, filename=package_filename(name) if name != "<unknown>" else None):
                errors.append("%s: %s" % (name, err))
        return errors

    def history(self, name: str) -> list:
        return git_history(self.root, name)


def load_store(root: Optional[Path] = None, rev: Optional[str] = None) -> FabricStore:
    return FabricStore(repo_root_from(root), rev=rev)


def validate_fingerprint(record: dict, filename: Optional[str] = None) -> list:
    errors = []
    if not isinstance(record, dict):
        return ["not an object"]
    if record.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            "schema_version must be one of %s" % (SUPPORTED_SCHEMA_VERSIONS,)
        )
    if record.get("schema_version") == SCHEMA_VERSION:
        if not isinstance(record.get("tracking"), dict):
            errors.append("tracking is required")
        if not isinstance(record.get("priority"), dict):
            errors.append("priority is required")
    if record.get("kind") != FINGERPRINT_KIND:
        errors.append("kind must be %s" % FINGERPRINT_KIND)
    identity = record.get("identity")
    if not isinstance(identity, dict):
        errors.append("identity is required")
        return errors
    name = identity.get("canonical_name")
    if not name:
        errors.append("identity.canonical_name is required")
    elif filename and filename != package_filename(name):
        errors.append("filename %s does not match canonical_name %s" % (filename, name))
    if not identity.get("canonical_id"):
        errors.append("identity.canonical_id is required")
    license_info = record.get("license")
    if not isinstance(license_info, dict):
        errors.append("license is required")
    else:
        if not isinstance(license_info.get("spdx"), list):
            errors.append("license.spdx must be a list")
        if not isinstance(license_info.get("raw"), list):
            errors.append("license.raw must be a list")
    deps = record.get("depends_on")
    if not isinstance(deps, list):
        errors.append("depends_on must be a list")
    else:
        for i, dep in enumerate(deps):
            if not isinstance(dep, dict) or not dep.get("name") or dep.get("scope") not in _SCOPES:
                errors.append("depends_on[%d] must have name and scope in %s" % (i, _SCOPES))
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance is required")
    else:
        if not provenance.get("generated_by"):
            errors.append("provenance.generated_by is required")
        if not provenance.get("imported_at"):
            errors.append("provenance.imported_at is required")
        if not isinstance(provenance.get("sources"), list):
            errors.append("provenance.sources must be a list")
    return errors


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
