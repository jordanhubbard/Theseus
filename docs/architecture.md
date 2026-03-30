# Theseus — Architecture

## Overview

Theseus is a batch analysis toolchain. There is no server, no database, and no persistent state beyond the files you write to disk. The pipeline has three stages:

```
Source Trees (Nixpkgs, FreeBSD Ports)
        │
        ▼
  tools/bootstrap_canonical_recipes.py   ← walks Nixpkgs and/or FreeBSD Ports; run by user
        │
        ▼
  snapshots/<date>/                ← one JSON file per package per ecosystem
        │
        ├─► tools/overlap_report.py      ← compare ecosystems; write reports/overlap/
        ├─► tools/top_candidates.py      ← rank packages; write reports/top-candidates.json
        ├─► tools/validate_record.py     ← validate records against schema rules
        ├─► tools/diff_snapshots.py      ← diff two snapshots to track ecosystem drift
        └─► tools/extract_candidates.py  ← phase Z: merge top candidates; write reports/extractions/
```

## Schema

The canonical record format is defined in `schema/package-recipe.schema.json` (JSON Schema draft 2020-12). Key design decisions:

- **`provenance.confidence`** is a first-class field. Records admit their own uncertainty. Importers set this value; downstream tools can filter or weight by it.
- **`extensions`** is a pass-through object for ecosystem-specific fields that don't map cleanly to the canonical schema. Nothing in the toolchain reads it; it exists so information isn't discarded.
- **`unmapped`** and **`warnings`** in `provenance` capture fields the importer saw but couldn't normalize. These are signals for future schema evolution.
- The schema uses `additionalProperties: true` on most sub-objects. The canonical fields are required; extra fields are allowed. This makes forward-compatibility easier as ecosystems evolve.

See `docs/schema-evolution.md` for versioning rules, the version history, and guidance on when and how to bump `schema_version`.

## Snapshot Format

A snapshot is a directory tree of JSON files, one per record. File naming is arbitrary; tools discover records by walking the tree and checking for an `"identity"` key. The only reserved filename is `manifest.json` (skipped by all tools).

Records from different ecosystems for the same canonical package are separate files. The overlap tool joins them by `canonical_name`.

## Known importer limitations

### Nixpkgs: regex-based parsing

The Nixpkgs importer uses regex heuristics on `default.nix` files rather than evaluating Nix expressions. This means:

- Values set by conditional expressions, `lib.optionalString`, or dynamic attribute paths may be parsed incorrectly or missed entirely.
- The `confidence` score reflects field presence, not parse correctness. A record can have `confidence: 0.95` and still contain a wrong dependency list if the Nix source used a non-obvious pattern.
- For higher accuracy, run `nix-instantiate --eval --json` against each package and feed the result to a future importer variant.

### FreeBSD Ports: slave ports are not imported

FreeBSD Ports uses a "slave port" pattern where a port sets `MASTERDIR` to point to a sibling directory and inherits most of its Makefile. Slave port Makefiles typically don't set `PORTNAME` directly, so the importer returns `None` for them and they are silently skipped. Slave ports are common for packages that build multiple variants (e.g. `openssl` vs `openssl-legacy`). A future importer should detect `MASTERDIR`, follow it, and merge the slave-specific variables into the inherited record.

## Tools

### `tools/overlap_report.py`

Reads a snapshot directory, groups records by `canonical_name`, and classifies each group:

- **overlap**: present in both `nixpkgs` and `freebsd_ports`
- **only_nix**: present only in `nixpkgs`
- **only_ports**: present only in `freebsd_ports`
- **version_skew**: present in both, but with different versions

Writes five JSON files to `--out`: `summary.json`, `overlap.json`, `only_nix.json`, `only_ports.json`, `version_skew.json`.

### `tools/top_candidates.py`

Reads a snapshot directory, groups records by `canonical_name`, scores each group, and writes a ranked list.

Scoring heuristics (see source for current weights):

| Signal | Direction | Rationale |
|--------|-----------|-----------|
| `provenance.confidence` | Higher = better | More reliable records |
| Dual-ecosystem presence | +25 bonus | Already normalized in two worlds |
| Test presence | +15 | Easier to validate extraction |
| Dependency count | Fewer = better | Less surface area |
| Patch count | More = worse | Patches signal divergence from upstream |

### `tools/validate_record.py`

Validates one or more canonical records (files or directories) against the schema rules. Stdlib-only structural validation — checks required fields, types, and value ranges. Exits non-zero if any record is invalid.

```bash
python3 tools/validate_record.py examples/
python3 tools/validate_record.py --strict snapshot/
python3 tools/validate_record.py record.json
```

`--strict` additionally flags empty summaries, empty homepages, and non-empty `unmapped`/`warnings` fields. Useful for catching low-quality importer output before feeding it into analysis tools.

### `tools/diff_snapshots.py`

Compares two snapshot directories (e.g. from consecutive bootstrap runs) and classifies every package as added, removed, version-changed, ecosystem-changed, or unchanged. Useful for tracking ecosystem drift over time.

```bash
python3 tools/diff_snapshots.py --before snapshots/2026-03-01 --after snapshots/2026-03-26
python3 tools/diff_snapshots.py --before snapshots/old --after snapshots/new --out reports/drift.json
```

Output categories mirror those of `overlap_report.py`: the diff groups packages by their movement across the two snapshots rather than their movement across ecosystems.

### `tools/extract_candidates.py`

Phase Z: takes the `top_candidates.json` ranking and the snapshot directory, and produces
one merged extraction record per top-N candidate in `reports/extractions/`.

Each extraction record contains three sections:

- **`merged`** — a unified view of the package across all ecosystems: summary, homepage, license union, maintainer union, conflict union, dependency union, platform union, source URL union, and a `deprecated` flag (true if deprecated in any ecosystem).
- **`per_ecosystem`** — the full original canonical record for each ecosystem, keyed by ecosystem name.
- **`analysis`** — structured comparison: version agreement flag, versions by ecosystem, confidence average and by ecosystem, dependency union size and count by ecosystem, license agreement flag, list of ecosystems where deprecated, `has_conflicts` flag, and a `notes` list of human-readable observations (e.g. "version agreement: all at '1.3.1'", "nixpkgs has 2 more deps than freebsd_ports").

A `manifest.json` is written alongside the per-package files listing all extracted candidates.

```bash
python3 tools/extract_candidates.py snapshots/2026-03-27 reports/top-candidates.json \
    --out reports/extractions --top 100
```

Or via make:

```bash
make extract SNAPSHOT=./snapshots/2026-03-27
```

## Tests

Tests live in `tests/`. Run with `make test` (requires `pytest`).

- `tests/conftest.py` — adds repo root and `tools/` to `sys.path` for all test modules
- `tests/test_schema.py` — validates the JSON schema structure and all example records
- `tests/test_bootstrap.py` — unit tests for all bootstrap importer parsing functions and import runners
- `tests/test_overlap_report.py` — unit tests for `overlap_report.py` logic using `tmp_path` fixtures
- `tests/test_top_candidates.py` — unit tests for `top_candidates.py` scoring and ranking logic
- `tests/test_validate_record.py` — unit tests for `validate_record.py` field and type checking
- `tests/test_diff_snapshots.py` — unit tests for `diff_snapshots.py` snapshot comparison logic
- `tests/test_extract_candidates.py` — unit tests for `extract_candidates.py` merging, analysis, and extraction logic
