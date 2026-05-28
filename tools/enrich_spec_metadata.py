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
import re
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from theseus import importer


_FREEBSD_RAW = "https://raw.githubusercontent.com/freebsd/freebsd-ports/{commit}/{path}/Makefile"


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

    text = _fetch_text(_FREEBSD_RAW.format(commit=commit, path=source_path), timeout)
    if not text:
        return False
    meta = _parse_freebsd_makefile(text)

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

        if changed:
            _write_json(path, record)
            changed_paths.append(str(path))

    for path in changed_paths:
        print(path)
    print("updated", len(changed_paths), "record(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
