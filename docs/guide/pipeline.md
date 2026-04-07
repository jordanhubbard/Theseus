# Package Recipe Pipeline

The package recipe pipeline (Layer 1) normalizes package metadata from Nixpkgs and
FreeBSD Ports into a shared canonical JSON schema. It then ranks packages by importance
and produces merged extraction records for the top candidates.

---

## Architecture

```
Source Trees (Nixpkgs, FreeBSD Ports, PyPI, npm)
        │
        ▼
  theseus/importer.py              ← bootstrap: walks trees, emits records
  (via tools/bootstrap_canonical_recipes.py)
        │
        ▼
  snapshots/<date>/                ← one JSON file per package per ecosystem
        │
        ├─► tools/overlap_report.py      → reports/overlap/
        ├─► tools/top_candidates.py      → reports/top-candidates.json
        ├─► tools/validate_record.py     → validates individual records
        ├─► tools/diff_snapshots.py      → reports drift between runs
        └─► tools/extract_candidates.py  → reports/extractions/
                │
                └─► tools/spec_coverage.py   → coverage report
```

---

## Canonical Schema

Every record is a JSON file validated against `schema/package-recipe.schema.json`
(JSON Schema draft 2020-12).

| Field | Description |
|-------|-------------|
| `schema_version` | Schema version string (currently `"0.2"`) |
| `identity` | `canonical_name`, `ecosystem`, `ecosystem_id`, `version` |
| `descriptive` | `summary`, `homepage`, `license`, `categories` |
| `sources` | Download URLs and types |
| `dependencies` | `build`, `host`, `runtime`, `test` dependency lists |
| `build` | Build system `kind` and flags |
| `features` | Optional feature flags |
| `platforms` | Include/exclude platform lists |
| `patches` | Applied patches with reasons |
| `tests` | Test phase presence and structure |
| `provenance` | `source_path`, `confidence` (0–1), `warnings`, `unmapped` |
| `extensions` | Pass-through object for ecosystem-specific fields |
| `behavioral_spec` | Optional: path to a matching `_build/zspecs/*.zspec.json` |

The `provenance.confidence` field is a first-class signal. Records admit their own
uncertainty — importers set this value and downstream tools can filter or weight by it.

### Snapshot format

A snapshot is a directory tree of JSON files, one per record. Tools discover records
by walking the tree and looking for an `"identity"` key. The only reserved filename
is `manifest.json` (skipped by all tools).

Records from different ecosystems for the same canonical package are separate files.
The overlap tool joins them by `canonical_name`.

---

## Step 1: Bootstrap

```bash
python3 tools/bootstrap_canonical_recipes.py \
  --nixpkgs /path/to/nixpkgs \
  --ports   /path/to/freebsd-ports \
  --out     ./snapshots/$(date +%Y-%m-%d)
```

Or import from PyPI and npm registries:

```bash
# Generate seed lists from FreeBSD Ports
make seed SNAPSHOT=./snapshots/2026-04-06

# Import PyPI packages
make import-pypi PYPI_SEED=reports/pypi-seed.txt

# Import npm packages
make import-npm NPM_SEED=reports/npm-seed.txt
```

### Importer limitations

**Nixpkgs:** The importer uses regex heuristics on `default.nix` files rather than
evaluating Nix expressions. Values set by conditional expressions or dynamic attribute
paths may be parsed incorrectly. The `confidence` score reflects field presence, not
parse correctness.

**FreeBSD Ports (slave ports):** The importer handles `MASTERDIR`-based slave ports
via `_resolve_masterdir()` in `theseus/importer.py`. When `MASTERDIR` is detected,
the master Makefile is loaded and its variables are merged as defaults. If `MASTERDIR`
cannot be resolved, the port is still imported with a warning.

---

## Step 2: Overlap Report

```bash
make report SNAPSHOT=./snapshots/2026-04-06
# Output: reports/overlap/{summary,overlap,only_nix,only_ports,version_skew}.json
```

Classifies every package as:

- **overlap** — present in both Nixpkgs and FreeBSD Ports
- **only_nix** — present only in Nixpkgs
- **only_ports** — present only in FreeBSD Ports
- **version_skew** — present in both, but with different versions

---

## Step 3: Candidate Ranking

```bash
make candidates SNAPSHOT=./snapshots/2026-04-06
# Output: reports/top-candidates.json
```

Scores each package with these heuristics:

| Signal | Direction | Weight |
|--------|-----------|--------|
| Dual-ecosystem presence | Higher | +25 bonus |
| `provenance.confidence` | Higher is better | linear |
| Test presence | Better | +15 |
| Dependency count | Fewer is better | negative |
| Patch count | More is worse | negative |

### Ranking by reverse dependency fan-in

For large snapshots, rank by how many other packages depend on each package:

```bash
make rank SNAPSHOT=./snapshots/2026-04-06 RANK_TOP=500
```

---

## Step 4: Extract Top Candidates (Phase Z)

```bash
make extract SNAPSHOT=./snapshots/2026-04-06
# Output: reports/extractions/*.json + reports/extractions/manifest.json
```

Produces one merged record per top-N candidate containing:

- **`merged`** — unified view: summary, homepage, license union, dependency union, source URLs
- **`per_ecosystem`** — full original record per ecosystem
- **`analysis`** — version agreement, confidence, license agreement, composite score

The extractor automatically injects `behavioral_spec` for any candidate whose
`canonical_name` matches a compiled spec in `_build/zspecs/`.

---

## Step 5: Validate Records

```bash
python3 tools/validate_record.py examples/          # validate a directory
python3 tools/validate_record.py record.json         # validate one file
python3 tools/validate_record.py examples/ --strict  # also flag empty fields
```

`--strict` additionally flags empty summaries, empty homepages, and non-empty
`unmapped`/`warnings` fields.

For records with a `behavioral_spec` field, the validator also runs the spec harness
and reports pass/fail for each invariant.

---

## Step 6: Coverage Report

After extraction, check which candidates have a behavioral spec:

```bash
make spec-coverage EXTRACTION_DIR=reports/extractions/ TOP=50
```

This reports covered and gap candidates sorted by composite score. Use it to decide
where to write the next spec.

---

## Step 7: Diff Two Snapshots

Track ecosystem drift between bootstrap runs:

```bash
make diff BEFORE=./snapshots/2026-03-01 AFTER=./snapshots/2026-04-06
```

Classifies every package as added, removed, version-changed, or unchanged.

---

## Bulk Build Pipeline

For large-scale automated spec generation:

```bash
# 1. Rank by reverse-dep fan-in
make rank SNAPSHOT=./snapshots/2026-04-06 RANK_TOP=500 RANK_MIN_REFS=2

# 2. Run bulk build (top-100 packages, 2 parallel jobs)
make bulk-build SNAPSHOT=./snapshots/2026-04-06 BULK_TOP=100 BULK_JOBS=2
```
