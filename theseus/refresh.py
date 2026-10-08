"""Refresh committed package recipes from live upstreams.

The corpus in ``specs/`` is the index. Re-ingest does not require a prior
snapshot directory. Registry ecosystems (PyPI, npm) are always fetched from
their public JSON APIs. Tree ecosystems (Nixpkgs, FreeBSD Ports) prefer a
local checkout and fall back to GitHub raw so refresh works on a laptop
without those trees.

``make refresh`` runs this module then fabric ingest. That is the supported
way to restock Theseus as upstream collections move.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import theseus.importer as imp


GENERATED_BY = "refresh_recipes.py"
NIXPKGS_GITHUB = ("NixOS", "nixpkgs")
PORTS_GITHUB = ("freebsd", "freebsd-ports")
DEFAULT_NIXPKGS_REF = "master"
DEFAULT_PORTS_REF = "main"
DEFAULT_NIXPKGS_ROOT = "~/.nix-defexpr/channels/nixpkgs"
DEFAULT_PORTS_ROOT = "/usr/ports"

_PORT_PATH_RE = re.compile(r"^[A-Za-z0-9._+-]+/[A-Za-z0-9._+-]+$")
_SUPPORTED = ("pypi", "npm", "nixpkgs", "freebsd_ports", "cargo")


def now_imported_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def recipe_ecosystems(rec: dict) -> list[str]:
    merged = (rec.get("extensions") or {}).get("merged_from")
    if isinstance(merged, list) and merged:
        return [str(x) for x in merged if x]
    eco = (rec.get("identity") or {}).get("ecosystem")
    return [eco] if eco else []


def registry_query_name(rec: dict, ecosystem: str) -> str:
    ident = rec.get("identity") or {}
    eid = (ident.get("ecosystem_id") or "").strip()
    name = (ident.get("canonical_name") or "").strip()
    if ecosystem == ident.get("ecosystem") and eid:
        if ecosystem == "npm":
            return eid
        if ecosystem == "pypi":
            return eid
        if ecosystem == "cargo":
            return eid
    return name


def ports_source_path(rec: dict) -> Optional[str]:
    ident = rec.get("identity") or {}
    candidates = [
        ident.get("ecosystem_id"),
        (rec.get("provenance") or {}).get("source_path"),
        ((rec.get("extensions") or {}).get("freebsd_ports") or {}).get("source_path"),
    ]
    for cand in candidates:
        if not cand or not isinstance(cand, str):
            continue
        text = cand.strip().strip("/")
        if _PORT_PATH_RE.match(text):
            return text
    return None


def nixpkgs_source_candidates(rec: dict) -> list[str]:
    ident = rec.get("identity") or {}
    name = (ident.get("canonical_name") or "").strip()
    ext = ((rec.get("extensions") or {}).get("nixpkgs") or {})
    raw = [
        (rec.get("provenance") or {}).get("source_path"),
        ident.get("ecosystem_id"),
        ext.get("recipe_file"),
        ext.get("source_path"),
    ]
    out: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        text = path.strip().strip("/")
        if not text or text in seen:
            return
        if text.startswith("http"):
            return
        seen.add(text)
        out.append(text)

    for cand in raw:
        if not cand or not isinstance(cand, str):
            continue
        text = cand.strip()
        if "pkgs/" in text or text.endswith(".nix"):
            add(text)
            if not text.endswith(".nix"):
                add(text.rstrip("/") + "/default.nix")
                add(text.rstrip("/") + "/package.nix")

    if name and len(name) >= 2:
        prefix = name[:2].lower()
        add("pkgs/by-name/%s/%s/package.nix" % (prefix, name))
        add("pkgs/by-name/%s/%s/default.nix" % (prefix, name))
    return out


def _raw_url(owner: str, repo: str, ref: str, path: str) -> str:
    return "https://raw.githubusercontent.com/%s/%s/%s/%s" % (
        owner, repo, ref, path.lstrip("/"),
    )


def github_ref_sha(owner: str, repo: str, ref: str, timeout: int = 15) -> Optional[str]:
    url = "https://api.github.com/repos/%s/%s/commits/%s" % (owner, repo, ref)
    data = imp._fetch_json(url, timeout=timeout)
    if not data:
        return None
    sha = data.get("sha")
    return sha if isinstance(sha, str) and sha else None


def _dir_or_none(path: Optional[Path]) -> Optional[Path]:
    if path is None:
        return None
    return path if path.is_dir() else None


def default_nixpkgs_root(cli: Optional[Path] = None) -> Optional[Path]:
    if cli is not None:
        return _dir_or_none(cli)
    for env_name in ("THESEUS_NIXPKGS", "NIXPKGS_ROOT"):
        val = os.environ.get(env_name)
        if val:
            found = _dir_or_none(Path(val).expanduser())
            if found:
                return found
    return _dir_or_none(Path(DEFAULT_NIXPKGS_ROOT).expanduser())


def default_ports_root(cli: Optional[Path] = None) -> Optional[Path]:
    if cli is not None:
        return _dir_or_none(cli)
    for env_name in ("THESEUS_PORTS", "PORTS_ROOT"):
        val = os.environ.get(env_name)
        if val:
            found = _dir_or_none(Path(val).expanduser())
            if found:
                return found
    return _dir_or_none(Path(DEFAULT_PORTS_ROOT))


def _pin_commit(rec: Optional[dict], commit: Optional[str]) -> Optional[dict]:
    if rec is None:
        return None
    if commit:
        rec.setdefault("provenance", {})["source_repo_commit"] = commit
    return rec


def fetch_pypi(rec: dict, timeout: int) -> Optional[dict]:
    return imp.pypi_record(registry_query_name(rec, "pypi"), timeout=timeout)


def fetch_npm(rec: dict, timeout: int) -> Optional[dict]:
    return imp.npm_record(registry_query_name(rec, "npm"), timeout=timeout)


_NIX_OVERRIDE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\.override\b")
_NIX_CALLPACKAGE_RE = re.compile(r"callPackage\s+\./([A-Za-z0-9._/-]+\.nix)")


def _nix_follow_paths(content: str, current_path: str) -> list[str]:
    """When a nix file is an alias or callPackage wrapper, try the target next."""
    extra: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        text = path.strip().replace("\\", "/")
        if not text or text in seen:
            return
        seen.add(text)
        extra.append(text)

    match = _NIX_OVERRIDE_RE.search(content or "")
    if match:
        alias = match.group(1)
        if len(alias) >= 2:
            add("pkgs/by-name/%s/%s/package.nix" % (alias[:2].lower(), alias))
            add("pkgs/by-name/%s/%s/default.nix" % (alias[:2].lower(), alias))
    parent = str(Path(current_path).parent).replace("\\", "/")
    for rel in _NIX_CALLPACKAGE_RE.findall(content or ""):
        add("%s/%s" % (parent, rel))
    if current_path.endswith(".nix"):
        add("%s/default.nix" % parent)
        add("%s/package.nix" % parent)
        add("%s/common.nix" % parent)
    return extra


def fetch_nixpkgs(
    rec: dict,
    *,
    nixpkgs_root: Optional[Path],
    allow_remote: bool,
    ref: str,
    commit: Optional[str],
    timeout: int,
    work_dir: Path,
) -> Optional[dict]:
    local_commit = None
    if nixpkgs_root is not None:
        local_commit = commit or imp._get_git_commit(nixpkgs_root)
    pkg_dir = work_dir / "nix" / (rec.get("identity") or {}).get("canonical_name", "pkg")
    pkg_dir.mkdir(parents=True, exist_ok=True)
    queue = list(nixpkgs_source_candidates(rec))
    tried: set[str] = set()
    while queue:
        cand = queue.pop(0)
        if cand in tried:
            continue
        tried.add(cand)
        parsed = None
        content = ""
        local_hit = False
        if nixpkgs_root is not None:
            path = nixpkgs_root / cand
            if path.is_dir():
                for name in ("package.nix", "default.nix", "common.nix"):
                    nested = path / name
                    if nested.is_file():
                        path = nested
                        cand = str(nested.relative_to(nixpkgs_root))
                        break
            if path.is_file():
                local_hit = True
                parsed = imp.parse_nix_file(path, nixpkgs_root)
                if parsed is not None:
                    return _pin_commit(parsed, local_commit)
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    content = ""
        if parsed is None and allow_remote and not local_hit:
            url = _raw_url(NIXPKGS_GITHUB[0], NIXPKGS_GITHUB[1], ref, cand)
            content = imp._fetch_text(url, timeout=timeout) or ""
            if content:
                dest = pkg_dir / cand
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                parsed = imp.parse_nix_file(dest, pkg_dir)
                if parsed is not None:
                    parsed.setdefault("provenance", {})["source_path"] = cand
                    return _pin_commit(parsed, commit)
        if content:
            queue.extend(_nix_follow_paths(content, cand))
        else:
            queue.extend(_nix_follow_paths("", cand))
    return None


def _write_port_makefile(root: Path, source_path: str, text: str) -> Path:
    dest = root / source_path / "Makefile"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def fetch_ports(
    rec: dict,
    *,
    ports_root: Optional[Path],
    allow_remote: bool,
    ref: str,
    commit: Optional[str],
    timeout: int,
    work_dir: Path,
) -> Optional[dict]:
    source_path = ports_source_path(rec)
    if ports_root is not None and source_path:
        makefile = ports_root / source_path / "Makefile"
        if makefile.is_file():
            parsed = imp.parse_ports_makefile(makefile, ports_root)
            return _pin_commit(parsed, commit or imp._get_git_commit(ports_root))
    if not allow_remote or not source_path:
        return None
    url = _raw_url(PORTS_GITHUB[0], PORTS_GITHUB[1], ref, source_path + "/Makefile")
    text = imp._fetch_text(url, timeout=timeout)
    if not text:
        return None
    tree = (
        work_dir / "ports" / (rec.get("identity") or {}).get("canonical_name", "pkg")
    ).resolve()
    makefile = _write_port_makefile(tree, source_path, text)
    vars_ = imp._ports_vars(text)
    master_val = vars_.get("MASTERDIR", "")
    if master_val:
        master_rel = imp.masterdir_source_path(master_val, source_path)
        if master_rel:
            master_url = _raw_url(
                PORTS_GITHUB[0], PORTS_GITHUB[1], ref, master_rel + "/Makefile",
            )
            master_text = imp._fetch_text(master_url, timeout=timeout)
            if master_text:
                _write_port_makefile(tree, master_rel, master_text)
    parsed = imp.parse_ports_makefile(makefile, tree)
    return _pin_commit(parsed, commit)


def _union_into(spec: dict, rec: dict) -> None:
    existing_urls = {s.get("url") for s in spec.get("sources") or []}
    for src in rec.get("sources") or []:
        if src.get("url") not in existing_urls:
            spec.setdefault("sources", []).append(src)
            existing_urls.add(src.get("url"))
    for bucket in ("build", "host", "runtime", "test"):
        existing = set(spec.get("dependencies", {}).get(bucket, []))
        for dep in (rec.get("dependencies") or {}).get(bucket, []):
            if dep not in existing:
                spec.setdefault("dependencies", {}).setdefault(bucket, []).append(dep)
                existing.add(dep)
    existing_m = set((spec.get("descriptive") or {}).get("maintainers") or [])
    for maint in (rec.get("descriptive") or {}).get("maintainers") or []:
        if maint not in existing_m:
            spec.setdefault("descriptive", {}).setdefault("maintainers", []).append(maint)
            existing_m.add(maint)
    existing_lic = set((spec.get("descriptive") or {}).get("license") or [])
    for lic in (rec.get("descriptive") or {}).get("license") or []:
        if lic not in existing_lic:
            spec.setdefault("descriptive", {}).setdefault("license", []).append(lic)
            existing_lic.add(lic)
    existing_c = set(spec.get("conflicts") or [])
    for conflict in rec.get("conflicts") or []:
        if conflict not in existing_c:
            spec.setdefault("conflicts", []).append(conflict)
            existing_c.add(conflict)
    for key, value in (rec.get("extensions") or {}).items():
        if key == "merged_from":
            continue
        spec.setdefault("extensions", {})[key] = value


def merge_refresh(original: dict, new_by_eco: dict) -> dict:
    """Merge successful refreshes; keep original data for ecosystems that failed."""
    if not new_by_eco:
        return original
    original_name = (original.get("identity") or {}).get("canonical_name")
    original_id = (original.get("identity") or {}).get("canonical_id") or (
        "pkg:%s" % original_name if original_name else None
    )
    base = max(
        new_by_eco.values(),
        key=lambda r: float((r.get("provenance") or {}).get("confidence") or 0),
    )
    spec = json.loads(json.dumps(base))
    for rec in new_by_eco.values():
        if rec is base:
            continue
        _union_into(spec, rec)
    original_ecos = set(recipe_ecosystems(original))
    missing = original_ecos - set(new_by_eco)
    warnings = list((spec.get("provenance") or {}).get("warnings") or [])
    if missing:
        _union_into(spec, original)
        warnings.append(
            "partial refresh; kept prior data for: %s" % ", ".join(sorted(missing))
        )
    orig_desc = original.get("descriptive") or {}
    new_desc = spec.setdefault("descriptive", {})
    for field in ("license", "homepage", "summary", "maintainers"):
        if not new_desc.get(field) and orig_desc.get(field):
            new_desc[field] = orig_desc[field]
    if original_name:
        spec.setdefault("identity", {})["canonical_name"] = original_name
        if original_id:
            spec["identity"]["canonical_id"] = original_id
    merged_from = sorted((original_ecos | set(new_by_eco)) - {""})
    spec.setdefault("extensions", {})["merged_from"] = merged_from
    spec.setdefault("provenance", {})
    spec["provenance"]["generated_by"] = GENERATED_BY
    spec["provenance"]["imported_at"] = now_imported_at()
    spec["provenance"]["warnings"] = warnings
    paths = []
    for rec in new_by_eco.values():
        path = (rec.get("provenance") or {}).get("source_path")
        if path and path not in paths:
            paths.append(path)
    if len(paths) == 1:
        spec["provenance"]["source_path"] = paths[0]
    elif paths:
        spec["provenance"]["source_path"] = paths[0]
        spec["provenance"]["source_paths"] = paths
    commits = []
    for rec in new_by_eco.values():
        commit = (rec.get("provenance") or {}).get("source_repo_commit")
        if commit and commit not in commits:
            commits.append(commit)
    spec["provenance"]["source_repo_commit"] = commits[0] if len(commits) == 1 else None
    if len(commits) > 1:
        spec["provenance"]["source_repo_commits"] = commits
    if "behavioral_spec" in original:
        spec["behavioral_spec"] = original["behavioral_spec"]
    return spec


class RefreshContext:
    def __init__(
        self,
        *,
        nixpkgs_root: Optional[Path],
        ports_root: Optional[Path],
        allow_remote: bool,
        timeout: int,
        ecosystems: Optional[Iterable[str]],
        nixpkgs_ref: str,
        ports_ref: str,
        nixpkgs_commit: Optional[str],
        ports_commit: Optional[str],
        work_dir: Path,
    ):
        self.nixpkgs_root = nixpkgs_root
        self.ports_root = ports_root
        self.allow_remote = allow_remote
        self.timeout = timeout
        wanted = set(ecosystems) if ecosystems else set(_SUPPORTED)
        self.ecosystems = wanted
        self.nixpkgs_ref = nixpkgs_ref
        self.ports_ref = ports_ref
        self.nixpkgs_commit = nixpkgs_commit
        self.ports_commit = ports_commit
        self.work_dir = work_dir


def refresh_record(original: dict, ctx: RefreshContext) -> tuple[dict, list[str], list[str]]:
    """Return (maybe-updated record, updated ecosystems, failed ecosystems)."""
    updated: list[str] = []
    failed: list[str] = []
    new_by_eco: dict = {}
    for eco in recipe_ecosystems(original):
        if eco not in ctx.ecosystems:
            continue
        fetched = None
        if eco == "pypi":
            fetched = fetch_pypi(original, ctx.timeout)
        elif eco == "npm":
            fetched = fetch_npm(original, ctx.timeout)
        elif eco == "nixpkgs":
            fetched = fetch_nixpkgs(
                original,
                nixpkgs_root=ctx.nixpkgs_root,
                allow_remote=ctx.allow_remote,
                ref=ctx.nixpkgs_ref,
                commit=ctx.nixpkgs_commit,
                timeout=ctx.timeout,
                work_dir=ctx.work_dir,
            )
        elif eco == "freebsd_ports":
            fetched = fetch_ports(
                original,
                ports_root=ctx.ports_root,
                allow_remote=ctx.allow_remote,
                ref=ctx.ports_ref,
                commit=ctx.ports_commit,
                timeout=ctx.timeout,
                work_dir=ctx.work_dir,
            )
        elif eco == "cargo":
            failed.append(eco)
            continue
        else:
            failed.append(eco)
            continue
        if fetched is None:
            failed.append(eco)
        else:
            new_by_eco[eco] = fetched
            updated.append(eco)
    if not new_by_eco:
        return original, updated, failed
    return merge_refresh(original, new_by_eco), updated, failed


def load_recipes(specs_dir: Path) -> list[Path]:
    return sorted(
        path for path in specs_dir.glob("*.json") if path.name != "manifest.json"
    )


def _refresh_one_file(path: Path, ctx: RefreshContext, dry_run: bool) -> dict:
    try:
        original = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "name": path.stem,
            "status": "error",
            "error": str(exc),
            "updated": [],
            "failed": [],
        }
    name = (original.get("identity") or {}).get("canonical_name") or path.stem
    try:
        new_rec, updated, failed = refresh_record(original, ctx)
    except Exception as exc:
        print("refresh: error %s: %s" % (name, exc), file=sys.stderr, flush=True)
        return {
            "name": name,
            "status": "error",
            "error": str(exc),
            "updated": [],
            "failed": recipe_ecosystems(original),
        }
    status = "unchanged"
    if updated and not dry_run:
        path.write_text(
            json.dumps(new_rec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        status = "refreshed" if not failed else "partial"
    elif updated and dry_run:
        status = "dry_run"
    elif failed:
        status = "failed"
    print("refresh: %s %s" % (status, name), file=sys.stderr, flush=True)
    return {
        "name": name,
        "status": status,
        "updated": updated,
        "failed": failed,
        "version": (new_rec.get("identity") or {}).get("version"),
    }


def refresh_recipes(
    specs_dir: Path,
    *,
    nixpkgs_root: Optional[Path] = None,
    ports_root: Optional[Path] = None,
    allow_remote: bool = True,
    timeout: int = 15,
    jobs: int = 8,
    dry_run: bool = False,
    ecosystems: Optional[Iterable[str]] = None,
    nixpkgs_ref: str = DEFAULT_NIXPKGS_REF,
    ports_ref: str = DEFAULT_PORTS_REF,
) -> dict:
    """Refresh every recipe in specs_dir. Returns a JSON-serializable report."""
    nixpkgs_root = default_nixpkgs_root(nixpkgs_root)
    ports_root = default_ports_root(ports_root)
    paths = load_recipes(specs_dir)
    nix_commit = None
    ports_commit = None
    if nixpkgs_root is not None:
        nix_commit = imp._get_git_commit(nixpkgs_root)
    elif allow_remote:
        nix_commit = github_ref_sha(
            NIXPKGS_GITHUB[0], NIXPKGS_GITHUB[1], nixpkgs_ref, timeout=timeout
        )
    if ports_root is not None:
        ports_commit = imp._get_git_commit(ports_root)
    elif allow_remote:
        ports_commit = github_ref_sha(
            PORTS_GITHUB[0], PORTS_GITHUB[1], ports_ref, timeout=timeout
        )

    workers = jobs if jobs and jobs > 0 else 1
    results = []
    with tempfile.TemporaryDirectory(prefix="theseus-refresh-") as tmp:
        ctx = RefreshContext(
            nixpkgs_root=nixpkgs_root,
            ports_root=ports_root,
            allow_remote=allow_remote,
            timeout=timeout,
            ecosystems=ecosystems,
            nixpkgs_ref=nixpkgs_ref,
            ports_ref=ports_ref,
            nixpkgs_commit=nix_commit,
            ports_commit=ports_commit,
            work_dir=Path(tmp),
        )
        if workers == 1:
            for path in paths:
                results.append(_refresh_one_file(path, ctx, dry_run))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_refresh_one_file, path, ctx, dry_run): path
                    for path in paths
                }
                for fut in as_completed(futures):
                    results.append(fut.result())

    results.sort(key=lambda row: row.get("name") or "")
    counts = {"refreshed": 0, "partial": 0, "failed": 0, "unchanged": 0, "dry_run": 0, "error": 0}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "specs_dir": str(specs_dir),
        "count": len(results),
        "jobs": workers,
        "dry_run": dry_run,
        "allow_remote": allow_remote,
        "nixpkgs_root": str(nixpkgs_root) if nixpkgs_root else None,
        "ports_root": str(ports_root) if ports_root else None,
        "nixpkgs_commit": nix_commit,
        "ports_commit": ports_commit,
        "summary": counts,
        "recipes": results,
    }
