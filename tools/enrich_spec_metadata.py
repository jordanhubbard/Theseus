#!/usr/bin/env python3
"""
Backfill missing metadata in canonical package records from authoritative APIs.

Current enrichment targets:
  - PyPI: descriptive.homepage, descriptive.summary, descriptive.maintainers
  - npm: descriptive.maintainers
  - FreeBSD Ports: descriptive.homepage, descriptive.categories,
    descriptive.maintainers

The tool only fills empty fields. It does not overwrite non-empty values.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from theseus import importer


_FREEBSD_RAW = "https://raw.githubusercontent.com/freebsd/freebsd-ports/{commit}/{path}"
_NIXPKGS_RAW = "https://raw.githubusercontent.com/NixOS/nixpkgs/master/{path}"
_NIXPKGS_BLOB = "https://github.com/NixOS/nixpkgs/blob/master/{path}"
_NIXPKGS_HOOK_SUMMARIES = {
    "auto-patchelf-hook": "Nixpkgs setup hook for automatically patching ELF binaries",
    "autoreconf-hook": "Nixpkgs setup hook that runs autoreconf before configure",
    "copy-desktop-items-hook": "Nixpkgs setup hook for installing desktop item files",
    "install-shell-files": "Nixpkgs setup hook for installing man pages and shell completion files",
    "make-binary-wrapper-hook": "Nixpkgs setup hook for building binary executable wrappers",
    "make-shell-wrapper-hook": "Nixpkgs setup hook for creating wrapped shell executables",
    "wrap-gapps-hook": "Nixpkgs setup hook for wrapping graphical applications with GTK and GSettings environment",
    "writable-tmpdir-as-home-hook": "Nixpkgs setup hook that sets HOME to a writable temporary directory when needed",
}
_NIXPKGS_CATEGORY_OVERRIDES = {
    "curl": ["tools", "networking"],
    "doxygen": ["development", "tools"],
    "glu": ["development", "libraries"],
    "gnutls": ["development", "libraries"],
    "gtk+3": ["development", "libraries"],
    "itstool": ["development", "tools"],
    "libogg": ["development", "libraries"],
    "libpng-apng": ["development", "libraries"],
    "libusb": ["development", "libraries"],
    "libvorbis": ["development", "libraries"],
    "libx11": ["development", "libraries"],
    "libxext": ["development", "libraries"],
    "libxkbcommon": ["development", "libraries"],
    "libxrandr": ["development", "libraries"],
    "meson": ["development", "tools"],
    "openblas": ["development", "libraries"],
    "sdl2-compat": ["development", "libraries"],
    "unzip": ["tools", "compression"],
}


def _is_empty(value) -> bool:
    return value is None or value == "" or value == []


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _pypi_homepage(info: dict) -> str:
    homepage = (info.get("home_page") or "").strip()
    if homepage:
        return homepage
    project_urls = info.get("project_urls") or {}
    for key in (
        "Homepage", "homepage",
        "home_page",
        "Documentation", "documentation",
        "Source", "source",
        "Repository", "repository",
    ):
        value = (project_urls.get(key) or "").strip()
        if value:
            return value
    return (info.get("project_url") or info.get("package_url") or "").strip()


def _github_owner_handle(url: str) -> str:
    """Extract the repository owner from a GitHub URL."""
    normalized = importer._normalize_github_url(url)
    match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)$", normalized)
    if not match:
        return ""
    return match.group(1)


def _fetch_pypi_record(name: str, timeout: int) -> Optional[dict]:
    return importer._fetch_json(importer._PYPI_API.format(name=name), timeout=timeout)


def _fetch_npm_record(name: str, timeout: int) -> Optional[dict]:
    url_name = name.replace("/", "%2F")
    return importer._fetch_json(importer._NPM_API.format(name=url_name), timeout=timeout)


def _fetch_text(url: str, timeout: int) -> Optional[str]:
    data = importer._fetch_json(url, timeout=timeout)
    if isinstance(data, dict):
        return None
    try:
        from urllib.request import Request, urlopen

        req = Request(url, headers={"User-Agent": "theseus/0.1 metadata-enricher"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _extract_html_summary(text: str) -> str:
    """Extract a concise summary from HTML metadata."""
    patterns = (
        r'property=["\']og:description["\']\s+content=["\']([^"\']+)["\']',
        r'name=["\']description["\']\s+content=["\']([^"\']+)["\']',
        r'content=["\']([^"\']+)["\']\s+property=["\']og:description["\']',
        r'content=["\']([^"\']+)["\']\s+name=["\']description["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    title = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if title:
        return re.sub(r"\s+", " ", title.group(1)).strip()
    return ""


def _github_raw_to_repo_url(url: str) -> str:
    """Convert a GitHub raw/archive-like URL to a browsable repository URL."""
    match = re.match(
        r"^https://github\.com/([^/]+)/([^/]+)/raw/([^/]+)/(.+?)/?$",
        url,
    )
    if match:
        owner, repo, ref, path = match.groups()
        return "https://github.com/{}/{}/tree/{}/{}".format(owner, repo, ref, path.rstrip("/"))
    match = re.match(
        r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$",
        url,
    )
    if match:
        owner, repo, ref, path = match.groups()
        return "https://github.com/{}/{}/blob/{}/{}".format(owner, repo, ref, path)
    return ""


def _nixpkgs_resolve_relative(base_path: str, rel: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base_path), rel))


def _parse_freebsd_makefile(text: str) -> dict:
    result = {}
    patterns = {
        "homepage": r"^WWW\s*=\s*(.+)$",
        "maintainer": r"^MAINTAINER\s*=\s*(.+)$",
        "categories": r"^CATEGORIES\s*=\s*(.+)$",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            result[key] = match.group(1).strip()
    return result


def _freebsd_include_paths(text: str, source_path: str) -> list[str]:
    """Resolve quoted .include paths relative to a port directory."""
    current_dir = Path(source_path)
    parent_dir = current_dir.parent
    include_paths: list[str] = []
    for raw in re.findall(r'^\.include\s+"([^"]+)"', text, re.MULTILINE):
        path = raw.replace("${.CURDIR:H}", str(parent_dir)).replace("${.CURDIR}", str(current_dir))
        if path.startswith("../"):
            path = posixpath.normpath(posixpath.join(str(current_dir), path))
        if path.endswith(".mk"):
            include_paths.append(path.lstrip("./"))
    return include_paths


def _freebsd_fetch_path(commit: str, source_path: str, timeout: int) -> Optional[str]:
    raw_path = source_path if source_path.endswith(".mk") else source_path.rstrip("/") + "/Makefile"
    return _fetch_text(_FREEBSD_RAW.format(commit=commit, path=raw_path), timeout)


def _freebsd_meta(commit: str, source_path: str, timeout: int, seen: Optional[set[str]] = None) -> dict:
    """Collect metadata from a port Makefile and selected included .mk files."""
    if seen is None:
        seen = set()
    if source_path in seen:
        return {}
    seen.add(source_path)

    text = _freebsd_fetch_path(commit, source_path, timeout)
    if not text:
        return {}

    meta = _parse_freebsd_makefile(text)
    if meta.get("homepage") and meta.get("maintainer") and meta.get("categories"):
        return meta

    for include_path in _freebsd_include_paths(text, source_path):
        child = _freebsd_meta(commit, include_path, timeout, seen)
        for key, value in child.items():
            meta.setdefault(key, value)
    return meta


def _fetch_nixpkgs_text(path: str, timeout: int) -> Optional[str]:
    return _fetch_text(_NIXPKGS_RAW.format(path=path), timeout)


def _extract_nix_attr_block(text: str, attr: str) -> str:
    idx = text.find(attr)
    if idx == -1:
        return ""
    remainder = text[idx:]
    match = re.search(r"\n  [A-Za-z0-9_.+-]+\s*=", remainder[1:])
    if not match:
        return remainder
    end = 1 + match.start()
    return remainder[:end]


def _extract_nix_string(block: str, field: str) -> str:
    match = re.search(r"\b{}\s*=\s*\"([^\"]+)\"".format(re.escape(field)), block)
    return match.group(1).strip() if match else ""


def _extract_nix_maintainers(block: str) -> list[str]:
    match = re.search(r"maintainers\s*=\s*(?:with\s+lib\.maintainers;\s*)?\[\s*([^\]]*)\s*\]", block, re.DOTALL)
    if not match:
        return []
    tokens = re.findall(r"[A-Za-z0-9._+-]+", match.group(1))
    return [t for t in tokens if t]


def _extract_nix_relative_source(block: str) -> str:
    matches = re.findall(r"(\.\.?/[A-Za-z0-9._/+:-]+(?:\.[A-Za-z0-9._-]+)?)", block)
    return matches[-1] if matches else ""


def _nixpkgs_categories_from_path(path: str) -> list[str]:
    """Infer broad categories from a nixpkgs source path when the path is meaningful."""
    parts = [p for p in path.split("/") if p]
    if not parts or parts[0] != "pkgs":
        return []
    parts = parts[1:]
    if not parts:
        return []
    if parts[0] == "by-name":
        return []

    dirs = [p for p in parts[:-1] if p not in {"default.nix", "package.nix"}]
    if not dirs:
        return []
    if dirs[0] == "top-level":
        return []
    if dirs[0] == "build-support":
        return dirs[:2]
    if len(dirs) >= 2:
        return dirs[:2]
    return dirs[:1]


def _nixpkgs_path_from_source_url(url: str) -> str:
    prefix = "https://github.com/NixOS/nixpkgs/blob/master/"
    if url.startswith(prefix):
        return url[len(prefix):]
    return ""


def _nixpkgs_hook_categories(record: dict) -> list[str]:
    name = record.get("identity", {}).get("canonical_name", "")
    if name.endswith("-hook") or name == "install-shell-files":
        return ["build-support", "setup-hooks"]
    return []


def _is_nixpkgs_internal(record: dict) -> bool:
    source_path = record.get("provenance", {}).get("source_path", "")
    name = record.get("identity", {}).get("canonical_name", "")
    return source_path.startswith("pkgs/") and (
        "setup-hooks" in source_path
        or name.endswith("-hook")
        or name in {"install-shell-files"}
    )


def enrich_nixpkgs(record: dict, timeout: int) -> bool:
    changed = False
    desc = record.setdefault("descriptive", {})
    prov = record.get("provenance", {})
    source_path = prov.get("source_path", "")
    name = record.get("identity", {}).get("canonical_name", "")
    if _is_empty(desc.get("homepage")) and name == "curl":
        desc["homepage"] = "https://curl.se/"
        changed = True
    if _is_empty(desc.get("categories")):
        fallback_categories = _NIXPKGS_CATEGORY_OVERRIDES.get(name, [])
        categories = _nixpkgs_categories_from_path(source_path)
        if not categories:
            categories = fallback_categories
        if categories:
            desc["categories"] = categories
            changed = True
    if not source_path.startswith("pkgs/"):
        return changed

    text = _fetch_nixpkgs_text(source_path, timeout)
    if not text:
        return changed

    block = text
    attr = record.get("extensions", {}).get("nixpkgs", {}).get("attr", "")
    if source_path.endswith("all-packages.nix") and attr:
        block = _extract_nix_attr_block(text, attr)
    if not block:
        return False

    summary = _extract_nix_string(block, "description")
    homepage = _extract_nix_string(block, "homepage")
    maintainers = _extract_nix_maintainers(block)
    rel_source = _extract_nix_relative_source(block)
    resolved_source = ""
    if rel_source:
        resolved_source = _nixpkgs_resolve_relative(source_path, rel_source)

    if _is_empty(desc.get("summary")) and summary:
        desc["summary"] = summary
        changed = True
    if _is_empty(desc.get("summary")):
        fallback_summary = _NIXPKGS_HOOK_SUMMARIES.get(record.get("identity", {}).get("canonical_name", ""))
        if fallback_summary:
            desc["summary"] = fallback_summary
            changed = True
    if _is_empty(desc.get("maintainers")) and maintainers:
        desc["maintainers"] = maintainers
        changed = True
    if _is_empty(desc.get("homepage")):
        if homepage:
            desc["homepage"] = homepage
            changed = True
        elif _is_nixpkgs_internal(record):
            target = resolved_source or source_path
            desc["homepage"] = _NIXPKGS_BLOB.format(path=target)
            changed = True
        elif name == "curl":
            desc["homepage"] = "https://curl.se/"
            changed = True
    if not record.get("sources") and resolved_source:
        record["sources"] = [{"type": "repository", "url": _NIXPKGS_BLOB.format(path=resolved_source)}]
        changed = True
    if _is_empty(desc.get("categories")):
        category_path = source_path
        if not category_path and record.get("sources"):
            category_path = _nixpkgs_path_from_source_url(record["sources"][0].get("url", ""))
        categories = _nixpkgs_categories_from_path(category_path)
        if not categories and resolved_source:
            categories = _nixpkgs_categories_from_path(resolved_source)
        if not categories:
            categories = _nixpkgs_hook_categories(record)
        if not categories:
            categories = _NIXPKGS_CATEGORY_OVERRIDES.get(name, [])
        if categories:
            desc["categories"] = categories
            changed = True
    return changed


def enrich_pypi(record: dict, timeout: int) -> bool:
    changed = False
    desc = record.setdefault("descriptive", {})
    if not (_is_empty(desc.get("homepage")) or _is_empty(desc.get("summary")) or _is_empty(desc.get("maintainers"))):
        return False

    pkg_name = record["identity"]["ecosystem_id"]
    data = _fetch_pypi_record(pkg_name, timeout)
    if not data:
        return False
    info = data.get("info", {})

    if _is_empty(desc.get("homepage")):
        homepage = _pypi_homepage(info)
        if not homepage:
            homepage = (
                record.get("extensions", {})
                .get("pypi", {})
                .get("source_repository", "")
            )
        if homepage:
            desc["homepage"] = homepage
            changed = True
    if _is_empty(desc.get("summary")):
        summary = (info.get("summary") or "").strip()
        if not summary:
            homepage = _pypi_homepage(info)
            if homepage:
                html = _fetch_text(homepage, timeout)
                if html:
                    summary = _extract_html_summary(html)
        if summary:
            desc["summary"] = summary
            changed = True
    if _is_empty(desc.get("maintainers")):
        maintainers = importer._pypi_maintainers(info)
        if not maintainers:
            owner = _github_owner_handle(
                record.get("extensions", {})
                .get("pypi", {})
                .get("source_repository", "")
            )
            if owner:
                maintainers = [owner]
        if maintainers:
            desc["maintainers"] = maintainers
            changed = True
    return changed


def enrich_npm(record: dict, timeout: int) -> bool:
    desc = record.setdefault("descriptive", {})
    if not _is_empty(desc.get("maintainers")):
        return False

    pkg_name = record["identity"]["ecosystem_id"]
    data = _fetch_npm_record(pkg_name, timeout)
    if not data:
        return False

    latest_ver = (data.get("dist-tags") or {}).get("latest", "")
    versions = data.get("versions") or {}
    ver_data = versions.get(latest_ver, {})
    if not ver_data and versions:
        latest_ver = list(versions.keys())[-1]
        ver_data = versions[latest_ver]

    repo = ver_data.get("repository") or data.get("repository") or {}
    if isinstance(repo, str):
        repo_url = repo
    else:
        repo_url = repo.get("url", "")

    maintainers = importer._npm_maintainers(ver_data, data)
    if not maintainers:
        owner = _github_owner_handle(
            (
                record.get("extensions", {})
                .get("npm", {})
                .get("source_repository", "")
            )
            or repo_url
        )
        if owner:
            maintainers = [owner]
    if not maintainers:
        return False
    desc["maintainers"] = maintainers
    return True


def enrich_freebsd(record: dict, timeout: int) -> bool:
    changed = False
    desc = record.setdefault("descriptive", {})
    if not (
        _is_empty(desc.get("homepage"))
        or _is_empty(desc.get("categories"))
        or _is_empty(desc.get("maintainers"))
    ):
        return False

    prov = record.get("provenance", {})
    commit = prov.get("source_repo_commit")
    source_path = prov.get("source_path")
    if not commit or not source_path:
        return False

    meta = _freebsd_meta(commit, source_path, timeout)

    if _is_empty(desc.get("homepage")) and meta.get("homepage"):
        desc["homepage"] = meta["homepage"]
        changed = True
    if _is_empty(desc.get("maintainers")) and meta.get("maintainer"):
        desc["maintainers"] = [meta["maintainer"]]
        changed = True
    if _is_empty(desc.get("categories")) and meta.get("categories"):
        desc["categories"] = meta["categories"].split()
        changed = True
    if _is_empty(desc.get("categories")) and source_path:
        desc["categories"] = [source_path.split("/", 1)[0]]
        changed = True
    if _is_empty(desc.get("homepage")):
        for source in record.get("sources", []):
            source_url = source.get("url", "").replace("${PORTVERSION}", record.get("identity", {}).get("version", ""))
            homepage = _github_raw_to_repo_url(source_url)
            if homepage:
                desc["homepage"] = homepage
                changed = True
                break
    return changed


def iter_record_paths(paths: list[str]) -> list[Path]:
    if paths:
        return [Path(p) for p in paths]
    return sorted(Path("specs").glob("*.json"))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill missing canonical record metadata.")
    parser.add_argument("paths", nargs="*", help="Record paths to enrich; defaults to specs/*.json")
    parser.add_argument("--timeout", type=int, default=15, help="Per-request timeout in seconds")
    args = parser.parse_args(argv)

    changed_paths: list[str] = []
    for path in iter_record_paths(args.paths):
        record = _load_json(path)
        eco = record.get("identity", {}).get("ecosystem")
        changed = False
        if eco == "pypi":
            changed = enrich_pypi(record, args.timeout)
        elif eco == "npm":
            changed = enrich_npm(record, args.timeout)
        elif eco == "freebsd_ports":
            changed = enrich_freebsd(record, args.timeout)
        elif eco == "nixpkgs":
            changed = enrich_nixpkgs(record, args.timeout)

        if changed:
            _write_json(path, record)
            changed_paths.append(str(path))

    for path in changed_paths:
        print(path)
    print("updated", len(changed_paths), "record(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
