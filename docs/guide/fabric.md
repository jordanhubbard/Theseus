# Knowledge Fabric

Theseus fingerprints OSS packages and stores those fingerprints **in git**.
The product question is how much software we can know — provenance, repository,
license, and dependencies in both directions — not how much we can recreate
from a spec.

Full design: [knowledge-fabric.md](https://github.com/jordanhubbard/Theseus/blob/main/docs/knowledge-fabric.md)
and [ADR 0007](https://github.com/jordanhubbard/Theseus/blob/main/docs/decisions/0007-knowledge-fabric.md).

## Git is the database

Each package is one committed file:

```text
fabric/packages/requests.json
```

- Current snapshot: the working tree
- History: `git log -- fabric/packages/requests.json`
- Point in time: `python3 tools/fabric.py --rev HEAD~1 show requests`

Reverse dependencies are computed from outbound `depends_on` edges. They are
not stored, so they cannot drift.

## Commands

```bash
make refresh                      # restock specs/ from live upstreams, then ingest
make reingest                     # alias for make refresh
make fabric-stats                 # coverage dashboard
make fabric-show PKG=requests
make fabric-deps PKG=requests     # who it depends on
make fabric-rdeps PKG=urllib3     # who depends on it
make fabric-query FABRIC_LICENSE=MIT
make fabric-query FABRIC_REPO=github.com/psf
make fabric-query FABRIC_ECOSYSTEM=pypi
make fabric-ingest                # rebuild from specs/ + examples/ (parallel)
make fabric-ingest FABRIC_JOBS=4
make fabric-validate
make fabric-history PKG=requests
```

`make refresh` is the supported way to keep fingerprints current. It re-fetches
the committed `specs/` corpus from PyPI, npm, and Nixpkgs/Ports (local tree or
GitHub raw) and then runs ingest. `make fabric-ingest` alone only re-derives
fingerprints from already-committed recipes.

## What is recorded

A fingerprint has identity, repository (URL only when confidence is high),
license (raw tokens plus a light SPDX mapping), ecosystem sightings, outbound
dependencies, links to the recipes and optional behavioral spec that support
the claim, and a provenance block.

Ambiguous GitHub URLs stay in `repository.candidates`. Conflicting license
strings across ecosystems are unioned, not silently dropped.

## Coverage

`make fabric-stats` reports how many fingerprints have a repository, a license,
outbound deps, inbound dependents, and an optional Layer 2 spec. Growing those
counts is the work.
