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
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


SCHEMA_VERSION = "1.0"
FINGERPRINT_KIND = "oss_fingerprint"
PACKAGES_RELDIR = "fabric/packages"
GENERATED_BY = "theseus.fabric"

_SCOPES = ("runtime", "build", "host", "test")
_REPO_HOSTS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "codeberg.org",
    "git.savannah.gnu.org",
    "sr.ht",
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


def normalize_repo_url(url: str) -> Optional[str]:
    if not url:
        return None
    text = url.strip()
    if text.startswith("git+"):
        text = text[4:]
    if text.startswith("git://"):
        text = "https://" + text[6:]
    match = _GITHUBISH.match(text)
    if match:
        host, owner, repo = match.group(1), match.group(2), match.group(3)
        repo = _strip_git_suffix(repo.split("#", 1)[0])
        return "https://%s/%s/%s" % (host.lower(), owner, repo)
    for host in _REPO_HOSTS:
        if host in text.lower():
            cleaned = text.split("#", 1)[0].rstrip("/")
            if cleaned.endswith(".git"):
                cleaned = cleaned[:-4]
            return cleaned
    return None


def _explicit_repository(recipe: dict) -> Optional[tuple]:
    """Return (url, source_field) from ecosystem-specific metadata."""
    extensions = recipe.get("extensions") or {}
    for eco_key, field in (
        ("pypi", "source_repository"),
        ("npm", "repository"),
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
            url = normalize_repo_url(value) or value.strip()
            return url, "%s.%s" % (eco_key, field)
    return None


def _candidate_urls(recipe: dict) -> list:
    found = []
    seen = set()

    def add(url):
        norm = normalize_repo_url(url)
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


def extract_repository(recipe: dict) -> dict:
    explicit = _explicit_repository(recipe)
    candidates = _candidate_urls(recipe)
    if explicit:
        url, source = explicit
        kind = "git" if url and any(h in url.lower() for h in _REPO_HOSTS) else None
        extra = [c for c in candidates if c != url]
        return {
            "url": url,
            "kind": kind,
            "web": url,
            "confidence": 0.95,
            "source": source,
            "candidates": extra,
        }
    homepage = (recipe.get("descriptive") or {}).get("homepage")
    from_home = normalize_repo_url(homepage) if isinstance(homepage, str) else None
    if from_home:
        extra = [c for c in candidates if c != from_home]
        return {
            "url": from_home,
            "kind": "git",
            "web": from_home,
            "confidence": 0.8,
            "source": "homepage",
            "candidates": extra,
        }
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
    evidence = {"recipes": [source_path], "behavioral_spec": None}
    if root is not None:
        evidence["behavioral_spec"] = _zsdl_for(root, name)

    src_prov = recipe.get("provenance") or {}
    confidence = src_prov.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    imported_at = src_prov.get("imported_at") or _now_iso()

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
    base["evidence"] = {"recipes": recipes, "behavioral_spec": spec}
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


def ingest(root: Path, recipe_dirs: Iterable[Path], out_dir: Optional[Path] = None) -> dict:
    """Convert package-recipe records into committed fingerprints."""
    root = Path(root).resolve()
    dest = Path(out_dir) if out_dir is not None else packages_dir(root)
    dest.mkdir(parents=True, exist_ok=True)
    grouped = defaultdict(list)
    skipped = 0
    for path in iter_recipe_files(recipe_dirs):
        recipe = load_recipe(path)
        if recipe is None:
            skipped += 1
            continue
        try:
            rel = str(path.resolve().relative_to(root))
        except ValueError:
            rel = str(path)
        grouped[recipe["identity"]["canonical_name"]].append(
            recipe_to_fingerprint(recipe, rel, root=root)
        )
    written = []
    for name in sorted(grouped, key=lambda n: n.lower()):
        record = merge_fingerprints(grouped[name])
        path = dest / package_filename(name)
        write_fingerprint(path, record)
        written.append(name)
    return {
        "written": len(written),
        "packages": written,
        "skipped": skipped,
        "out_dir": str(dest),
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
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %s" % SCHEMA_VERSION)
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
