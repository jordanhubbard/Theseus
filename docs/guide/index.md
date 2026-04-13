# Theseus User Guide

**Theseus** is a two-layer toolchain for working with OSS package metadata.

**Layer 1** normalizes package recipes from [Nixpkgs](https://github.com/NixOS/nixpkgs),
PyPI, and npm into a shared canonical JSON schema, then ranks and extracts the most
important candidates. [FreeBSD Ports](https://github.com/freebsd/freebsd-ports) is also
supported as a build recipe source — its 20,000+ port Makefiles complement Nixpkgs.

**Layer 2** provides 70 machine-readable behavioral specs — one per OSS library —
that are verified against the real installed library on macOS and Linux.

---

## Installation

### Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.9+ | All tools and test suite |
| Node.js | 22+ | Node.js-backed Z-specs (ajv, chalk, express, lodash, minimist, prettier, semver, uuid) |
| npm | any | Install Node.js test dependencies |
| pytest | any | `make test` |
| PyYAML | any | `make compile-zsdl` / `make test` (ZSDL compiler) |

To run the full behavioral spec suite (`make verify-all-specs`), the libraries under test must also be installed. The CI workflow installs them automatically. For local use, install the ones you want to verify individually.

### Clone and set up

```bash
git clone https://github.com/jordanhubbard/Theseus
cd Theseus
pip install pytest pyyaml
npm install
make
```

`make` (with no target) checks your Python version and prints usage. If it exits
cleanly, you are ready to go.

### Verify the installation

```bash
make test
```

All 3,203 tests should pass. The suite runs in a few seconds — it uses no network
access and does not require any external tools to be installed beyond Python and Node.js.

---

## Quick Start

### Option A: Demo on built-in examples (no snapshot needed)

```bash
make start
```

This runs the overlap report and candidate ranker against the three example records
in `examples/` (curl, openssl, zlib). Reports land in `reports/demo-overlap/` and
`reports/demo-candidates.json`.

### Option B: Full pipeline on a real snapshot

If you have Nixpkgs and FreeBSD Ports source trees available:

```bash
# 1. Bootstrap canonical records from source trees
python3 tools/bootstrap_canonical_recipes.py \
  --nixpkgs /path/to/nixpkgs \
  --ports   /path/to/freebsd-ports \
  --out     ./snapshots/$(date +%Y-%m-%d)

# 2. Generate overlap report
make report SNAPSHOT=./snapshots/2026-04-06

# 3. Rank candidates
make candidates SNAPSHOT=./snapshots/2026-04-06

# 4. Extract top 50 candidates
make extract SNAPSHOT=./snapshots/2026-04-06

# 5. Check behavioral spec coverage
make spec-coverage EXTRACTION_DIR=reports/extractions/ TOP=50
```

### Option C: Verify behavioral specs

```bash
# Compile ZSDL sources to JSON (required before verification)
make compile-zsdl

# Run all 70 specs
make verify-all-specs

# Run a single spec
make verify-behavior ZSPEC=_build/zspecs/zlib.zspec.json

# Run all specs and write JSON results (for CI dashboards)
make verify-all-specs-json OUT=results.json
```

---

## Project Layout

```
theseus/        Python package: importer, drivers, store, agent
tools/          CLI analysis and verification scripts
zspecs/         Z-spec ZSDL sources (*.zspec.zsdl) — committed to git
_build/zspecs/  Compiled JSON specs — build artifact, not committed
schema/         JSON Schema for canonical package records
zspecs/schema/  JSON Schema for Z-spec files
examples/       Sample records: curl, openssl, zlib
specs/          239 committed canonical package records
docs/           Architecture and design documentation
docs/guide/     This user guide (MkDocs source)
tests/          Test suite (3,203 tests)
scripts/        Release automation
```

---

## Make Targets Reference

| Target | Description |
|--------|-------------|
| `make` / `make all` | Check Python version, print usage |
| `make start` | Demo on examples/ or analysis on SNAPSHOT= |
| `make test` | Validate Z-specs + run pytest suite |
| `make clean` | Remove `_build/`, `.pytest_cache`, `*.pyc` |
| `make compile-zsdl` | Compile all ZSDL sources (or one: `ZSDL=path`) |
| `make verify-all-specs` | Run all specs; text summary |
| `make verify-all-specs-json` | Run all specs; write JSON results |
| `make verify-behavior` | Run one spec (`ZSPEC=path`, supports `FILTER=`, `VERBOSE=1`) |
| `make validate-zspecs` | Static schema validation of all compiled specs |
| `make spec-coverage` | Coverage report (`EXTRACTION_DIR=` required) |
| `make orphan-specs` | Specs with no matching extraction record |
| `make spec-vector-coverage` | Per-spec invariant description coverage |
| `make report` | Overlap report (`SNAPSHOT=` required) |
| `make candidates` | Candidate ranking (`SNAPSHOT=` required) |
| `make extract` | Phase Z extraction (`SNAPSHOT=` and `CANDIDATES_OUT=` required) |
| `make validate` | Validate records (`PATHS=dir`, default: `examples/`) |
| `make diff` | Diff two snapshots (`BEFORE=` and `AFTER=` required) |
| `make release` | Cut a release (`BUMP=major\|minor\|patch`, default: `patch`) |
| `make help` | Full variable and target reference |

---

## Next Steps

- [Package Recipe Pipeline](pipeline.md) — how Layer 1 works end-to-end
- [Z-Layer Behavioral Specs](z-layer.md) — how Layer 2 works; all backends and invariant kinds
- [Writing a Spec](writing-specs.md) — step-by-step guide to authoring a new ZSDL spec
- [Reference](reference.md) — complete ZSDL syntax, all invariant kinds, all `skip_if` helpers
