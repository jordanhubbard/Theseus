# OSS knowledge fabric

This directory is the database. Git is the storage engine.

Each file under `packages/` is one package fingerprint: canonical identity,
source repository (when known with confidence), license, ecosystem sightings,
and **outbound** dependencies. Reverse dependencies are not stored; they are
derived by scanning the committed graph.

```
fabric/packages/<canonical-name>.json   ← one row
git log -- fabric/packages/foo.json     ← mutation history
git show HEAD:fabric/packages/foo.json  ← point-in-time read
```

Do not put a SQL database, SQLite file, or generated reverse-edge index here
as source of truth. Ingest from package recipes, commit the fingerprints,
query the tree.

```bash
make refresh           # restock specs/ from live upstreams, then ingest
make reingest          # alias for make refresh
make fabric-ingest     # specs/ + examples/ → fabric/packages/
make fabric-stats      # coverage of the committed graph
make fabric-show PKG=requests
make fabric-deps PKG=requests
make fabric-rdeps PKG=urllib3
make fabric-query FABRIC_LICENSE=MIT
make fabric-validate
```

See [docs/knowledge-fabric.md](../docs/knowledge-fabric.md) and
[ADR 0007](../docs/decisions/0007-knowledge-fabric.md).
