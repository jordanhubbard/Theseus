"""Derived dependency-reference scan frontier; git remains the catalog database.

A reference is one distinct consuming canonical package, across all scopes and
recipe copies. Registry namespaces remain separate. Plans and run reports are
rebuildable operational artifacts, never a second reverse-dependency database.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from theseus import importer
from theseus.fabric import ingest, iter_recipe_files, load_recipe, package_filename
from theseus.refresh import merge_refresh, now_imported_at

REGISTRIES = ('pypi', 'npm')
_SCOPES = ('build', 'host', 'runtime', 'test')
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*$')
_NPM = re.compile(r'^(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*$', re.I)


def normalized(name: str, ecosystem: str) -> str:
    name = name.strip()
    if ecosystem == 'pypi':
        return re.sub(r'[-_.]+', '-', name).lower()
    return name.lower() if ecosystem == 'npm' else name


def _key(name: str, ecosystem: str) -> tuple:
    return ecosystem, normalized(name, ecosystem)


def _records(root: Path):
    for path in iter_recipe_files([root / 'specs', root / 'examples']):
        record = load_recipe(path)
        if record and (record.get('identity') or {}).get('canonical_name'):
            yield path, record


def plan(root: Path) -> dict:
    root = Path(root)
    recipes = list(_records(root))
    aliases, covered, source = {}, set(), hashlib.sha256()
    fingerprints = []
    for path in sorted((root / 'fabric/packages').glob('*.json')):
        data = path.read_bytes()
        record = json.loads(data)
        fingerprints.append(record)
        source.update(path.name.encode() + b'\0' + data + b'\0')
        ident = record['identity']
        for eco in record.get('ecosystems') or []:
            ecosystem = eco['ecosystem']
            for name in [ident['canonical_name'], eco.get('ecosystem_id'), *(ident.get('aliases') or [])]:
                if name:
                    aliases[_key(name, ecosystem)] = _key((eco.get('ecosystem_id') or ident['canonical_name']) if ecosystem in REGISTRIES else ident['canonical_name'], ecosystem)
    recipe_keys = set()
    for path, record in recipes:
        source.update(str(path.relative_to(root)).encode() + b'\0' + path.read_bytes() + b'\0')
        ident = record['identity']
        ecosystem = ident.get('ecosystem', 'unknown')
        ecosystems = (record.get('extensions') or {}).get('merged_from') or [ecosystem]
        for eco in ecosystems:
            recipe_keys.add(aliases.get(_key(ident['canonical_name'], eco), _key(ident['canonical_name'], eco)))
    for key, target in aliases.items():
        if target in recipe_keys:
            covered.add(target)
    refs, scopes = defaultdict(set), defaultdict(set)

    def add(consumer, name, ecosystem, scope):
        if not isinstance(name, str) or not name.strip():
            return
        name = name.strip()
        # Ignore expressions/paths, but preserve scoped npm packages.
        if not (_NPM.fullmatch(name) if ecosystem == 'npm' else _NAME.fullmatch(name)):
            return
        key = aliases.get(_key(name, ecosystem), _key(name, ecosystem))
        if key[1] == normalized(consumer, ecosystem):
            return
        refs[key].add(consumer)
        scopes[key].add(scope)

    for _, record in recipes:
        ident = record['identity']
        for scope in _SCOPES:
            for name in (record.get('dependencies') or {}).get(scope) or []:
                add(ident['canonical_name'], name, ident.get('ecosystem', 'unknown'), scope)
    for record in fingerprints:
        for dep in record.get('depends_on') or []:
            add(record['identity']['canonical_name'], dep.get('resolved_to') or dep.get('name'),
                dep.get('ecosystem') or 'unknown', dep.get('scope', 'runtime'))
    entries = []
    for (ecosystem, name), consumers in refs.items():
        is_covered = (ecosystem, name) in covered
        state = 'covered' if is_covered else 'pending' if ecosystem in REGISTRIES else 'manual'
        entries.append(dict(ecosystem=ecosystem, name=name, ref_count=len(consumers),
                            referrers=sorted(consumers), scopes=sorted(scopes[(ecosystem, name)]),
                            state=state, reason=('Recipe and fingerprint present' if is_covered else
                            'Registry metadata scan required' if state == 'pending' else
                            'Needs a verified recipe source path or supported registry; no namespace guessing')))
    entries.sort(key=lambda item: (-item['ref_count'], item['name'], item['ecosystem']))
    return dict(schema='theseus-scan-queue@1', source_sha256=source.hexdigest(),
                reference_basis='Distinct consuming canonical packages in local recipes and fingerprints, not global popularity or downloads',
                entries=entries, counts={state: sum(e['state'] == state for e in entries)
                                        for state in ('pending', 'covered', 'manual')})


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(prefix='.' + path.name, dir=str(path.parent))
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def run(root: Path, queue: dict, *, limit: int = 20, timeout: int = 15, jobs: int = 1,
        ecosystems: Optional[list] = None, packages: Optional[list] = None,
        refresh_covered: bool = False) -> dict:
    """One finite batch in priority order; failures leave old evidence unchanged.

    Only public registry metadata is fetched. This does not download, execute or
    approve package implementation source, licenses or optional behavioral specs.
    """
    if not 1 <= limit <= 500 or not 1 <= timeout <= 120:
        raise ValueError('limit must be 1..500 and timeout 1..120 seconds')
    if not 1 <= jobs <= 16:
        raise ValueError('jobs must be 1..16')
    if queue.get('schema') != 'theseus-scan-queue@1':
        raise ValueError('unsupported queue schema')
    root = Path(root)
    current = plan(root)
    states = {(e['ecosystem'], e['name']): e['state'] for e in current['entries']}
    requested = set(packages or [])
    entries = sorted(queue['entries'], key=lambda e: (-e['ref_count'], e['name'], e['ecosystem']))
    results, attempted = [], set()
    existing = {}
    for path, record in _records(root):
        ident = record['identity']
        for eco in (record.get('extensions') or {}).get('merged_from') or [ident.get('ecosystem')]:
            existing[_key(ident['canonical_name'], eco)] = (path, record)
            if eco == ident.get('ecosystem') and ident.get('ecosystem_id'):
                existing[_key(ident['ecosystem_id'], eco)] = (path, record)
    selected = []
    for entry in entries:
        ecosystem, name = entry['ecosystem'], entry['name']
        key = _key(name, ecosystem)
        if ecosystems and ecosystem not in ecosystems:
            continue
        if requested and '%s:%s' % (ecosystem, name) not in requested:
            continue
        if ecosystem not in REGISTRIES or key in attempted:
            continue
        if states.get(key) == 'covered' and not refresh_covered:
            continue
        if len(attempted) >= limit:
            break
        attempted.add(key)
        selected.append(entry)

    def fetch(entry):
        ecosystem, name = entry['ecosystem'], entry['name']
        if not (_NPM.fullmatch(name) if ecosystem == 'npm' else _NAME.fullmatch(name)):
            raise ValueError('invalid registry package name')
        loader = importer.pypi_record if ecosystem == 'pypi' else importer.npm_record
        record = loader(name, timeout=timeout)
        if not record:
            raise ValueError('registry metadata unavailable')
        return record

    def fetched():
        # At most jobs metadata results are in flight or retained. Commit in rank
        # order on the caller thread; workers never mutate recipes or the fabric.
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            remaining = iter(selected)
            pending = deque((entry, pool.submit(fetch, entry)) for entry in
                            [next(remaining, None) for _ in range(min(jobs, len(selected)))])
            while pending:
                entry, future = pending.popleft()
                try:
                    record, error = future.result(), None
                except Exception as exc:
                    record, error = None, exc
                yield entry, record, error
                entry = next(remaining, None)
                if entry is not None:
                    pending.append((entry, pool.submit(fetch, entry)))

    for entry, record, error in fetched():
        ecosystem, name = entry['ecosystem'], entry['name']
        key = _key(name, ecosystem)
        result = dict(name=name, ecosystem=ecosystem, ref_count=entry['ref_count'])
        try:
            if error is not None:
                raise error
            ident = record.get('identity') or {}
            if ident.get('ecosystem') != ecosystem or normalized(ident.get('ecosystem_id') or ident.get('canonical_name', ''), ecosystem) != key[1]:
                raise ValueError('registry returned a different package identity')
            prior = existing.get(key)
            if prior:
                path, old = prior
                record = merge_refresh(old, {ecosystem: record})
            else:
                path = root / 'specs' / package_filename(ident['canonical_name'])
                if path.exists():
                    raise ValueError('recipe filename collision; existing evidence retained')
            record.setdefault('provenance', {})['imported_at'] = now_imported_at()
            _atomic_json(path, record)
            existing[key] = (path, record)
            result.update(state='scanned', recipe=str(path.relative_to(root)))
        except Exception as exc:
            result.update(state='failed', error=str(exc))
        results.append(result)
    ingestion = None
    if any(row['state'] == 'scanned' for row in results):
        ingestion = ingest(root, [root / 'specs', root / 'examples'], jobs=1)
        # A scan is complete only when its fingerprint actually validates.
        from theseus.fabric import validate_fingerprint
        for row in results:
            if row['state'] != 'scanned':
                continue
            recipe = json.loads((root / row['recipe']).read_text())
            name = recipe['identity']['canonical_name']
            fingerprint = root / 'fabric/packages' / package_filename(name)
            errors = validate_fingerprint(json.loads(fingerprint.read_text()), filename=fingerprint.name)
            if errors:
                row.update(state='failed', error='fingerprint validation failed: %s' % errors)
    return dict(schema='theseus-scan-run@1', source_sha256=queue['source_sha256'],
                stale_plan=queue['source_sha256'] != current['source_sha256'],
                jobs=jobs, attempted=len(results), scanned=sum(r['state'] == 'scanned' for r in results),
                failed=sum(r['state'] == 'failed' for r in results), results=results,
                ingestion=ingestion)
