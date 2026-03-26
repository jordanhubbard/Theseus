# Theseus — Architecture

## Overview

Theseus is a batch analysis toolchain. There is no server, no database, and no persistent state beyond the files you write to disk. The pipeline has three stages:

```
Source Trees (Nixpkgs, FreeBSD Ports)
        │
        ▼
  bootstrap_canonical_recipes.py   ← not included in this repo; run by user
        │
        ▼
  snapshots/<date>/                ← one JSON file per package per ecosystem
        │
        ▼
  tools/overlap_report.py          ← compare ecosystems; write reports/overlap/
  tools/top_candidates.py          ← rank packages; write reports/top-candidates.json
```

## Schema

The canonical record format is defined in `schema/package-recipe.schema.json` (JSON Schema draft 2020-12). Key design decisions:

- **`provenance.confidence`** is a first-class field. Records admit their own uncertainty. Importers set this value; downstream tools can filter or weight by it.
- **`extensions`** is a pass-through object for ecosystem-specific fields that don't map cleanly to the canonical schema. Nothing in the toolchain reads it; it exists so information isn't discarded.
- **`unmapped`** and **`warnings`** in `provenance` capture fields the importer saw but couldn't normalize. These are signals for future schema evolution.
- The schema uses `additionalProperties: true` on most sub-objects. The canonical fields are required; extra fields are allowed. This makes forward-compatibility easier as ecosystems evolve.

## Snapshot Format

A snapshot is a directory tree of JSON files, one per record. File naming is arbitrary; tools discover records by walking the tree and checking for an `"identity"` key. The only reserved filename is `manifest.json` (skipped by all tools).

Records from different ecosystems for the same canonical package are separate files. The overlap tool joins them by `canonical_name`.

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

## Tests

Tests live in `tests/`. Run with `make test` (requires `pytest`).

- `tests/test_schema.py` — validates the JSON schema structure and all example records
- `tests/test_overlap_report.py` — unit tests for `overlap_report.py` logic using `tmp_path` fixtures
- `tests/test_top_candidates.py` — unit tests for `top_candidates.py` scoring and ranking logic
