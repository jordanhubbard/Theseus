# OSS Knowledge Fabric

Theseus fingerprints open-source packages and stores those fingerprints
in git. The question the project now answers is not “can we recreate
this from a spec?” but “how much of OSS can we *know*?” — provenance,
repository, license, and bidirectional dependencies.

## Git is the database

| Database idea | Theseus equivalent |
|---------------|--------------------|
| Table row | `fabric/packages/<name>.json` |
| Primary key | `identity.canonical_name` |
| Current snapshot | git working tree / `HEAD` |
| Transaction log | `git log -- fabric/packages/` |
| Point-in-time query | `python3 tools/fabric.py --rev <commit> show zlib` |
| Schema | `schema/fingerprint.schema.json` |

Do not add SQLite, Postgres, or a generated reverse-edge file as source
of truth. Reverse dependencies are computed from outbound `depends_on`
edges at query time so they cannot drift from the committed graph.

## What a fingerprint contains

```json
{
  "schema_version": "1.0",
  "kind": "oss_fingerprint",
  "identity": { "canonical_name": "requests", "canonical_id": "pkg:requests" },
  "repository": { "url": "https://github.com/psf/requests", "confidence": 0.95 },
  "license": { "spdx": ["Apache-2.0"], "raw": ["Apache-2.0"] },
  "depends_on": [{ "name": "urllib3", "scope": "runtime", "ecosystem": "pypi" }],
  "provenance": { "sources": [{ "path": "specs/requests.json", "kind": "package_recipe" }] }
}
```

Repository URLs are recorded only when an explicit ecosystem field
(`pypi.source_repository`, npm/cargo `repository`) or a repository-host
homepage supports the claim. Ambiguous GitHub URLs harvested from recipe
`sources` stay in `repository.candidates` so the fabric does not
confidently attach `github.com/ruby/zlib` to `zlib`.

Conflicting license tokens across ecosystems are unioned and kept in
`license.raw`. SPDX-like values in `license.spdx` are a convenience
mapping, not a legal determination.

## Commands

```bash
make fabric-ingest              # specs/ + examples/ → fabric/packages/
make fabric-stats               # how much we know
make fabric-show PKG=requests
make fabric-deps PKG=requests   # who it depends on
make fabric-rdeps PKG=urllib3   # who depends on it
make fabric-query FABRIC_LICENSE=MIT
make fabric-query FABRIC_REPO=github.com/psf
make fabric-query FABRIC_ECOSYSTEM=pypi
make fabric-validate
python3 tools/fabric.py --rev HEAD~1 stats
python3 tools/fabric.py history requests
```

Ingest is idempotent: recipes for the same `canonical_name` merge
(ecosystems, licenses, dependencies, provenance sources). Commit the
resulting JSON; that commit *is* the write.

## How records enter the fabric

```
Nixpkgs / Ports / PyPI / npm recipes
        │
        ▼
  theseus/importer.py  →  snapshots/ (ephemeral)
        │
        ▼
  specs/ + examples/   →  committed package recipes
        │
        ▼
  tools/fabric.py ingest
        │
        ▼
  fabric/packages/*.json   ← git is the database
        │
        ├─ show / query / stats
        ├─ deps  (outbound)
        └─ rdeps (derived inbound)
```

Layer 2 ZSDL specs, when present, are linked as `evidence.behavioral_spec`.
They enrich a fingerprint; they do not define it.

## Coverage metric

`make fabric-stats` is the product dashboard: package count, how many
have a repository URL, a license, outbound deps, inbound dependents,
and an optional behavioral spec. Growing those numerators — especially
confident repositories and a connected dependency graph — is the work.

See [ADR 0007](decisions/0007-knowledge-fabric.md).
