# Theseus — Plan and State

## Current State (2026-04-04)

**20 Z-layer specs · 371 invariants · 1240 tests · 3 CI platforms (ubuntu, macos, freebsd)**

### What is built

**Core pipeline** (original): bootstrap importer, overlap report, candidate ranker, phase-Z extractor, snapshot diff, record validator.

**Z-layer behavioral spec system:**

| Component | Description |
|-----------|-------------|
| `zspecs/*.zspec.zsdl` | 20 ZSDL spec sources (committed); compiled to `_build/zspecs/` |
| `zspecs/schema/` | JSON Schema for spec files (schema_version 0.1) |
| `_build/zspecs/*.zspec.json` | Compiled specs (build artifacts, gitignored; `make compile-zsdl` regenerates) |
| `tools/verify_behavior.py` | Harness: loads a spec, runs every invariant against the installed library |
| `tools/validate_zspec.py` | Static validation of spec files against the JSON Schema |
| `tools/verify_all_specs.py` | Runs all specs in one pass; writes a JSON results file for CI dashboards |
| `tools/spec_coverage.py` | Reads extraction output, reports which candidates have a spec |
| `tools/orphan_specs.py` | Reports specs with no matching extraction record (reverse of spec_coverage) |
| `tools/zsdl_compile.py` | ZSDL → JSON compiler |
| `docs/zsdl-design.md` | ZSDL language design document |
| `docs/writing-specs.md` | Spec authoring guide (practical, with examples) |

**Backends** supported by the harness:

| Backend | How it loads the library | Used by |
|---------|--------------------------|---------|
| `ctypes` | `ctypes.CDLL` via `find_library` | zlib, zstd, libcrypto |
| `python_module` | `importlib.import_module` | base64, datetime, difflib, hashlib, json, pathlib, re, sqlite3, struct, urllib_parse |
| `cli` | subprocess (openssl, curl) | curl, openssl |
| `node` (CJS) | `require()` via `node -e` | ajv, minimist, semver, uuid |
| `node` (ESM) | `await import()` via `node -e` | chalk |

**Specs in `zspecs/`:**

| Spec | Backend | Invariants | Notes |
|------|---------|-----------|-------|
| `ajv` | node/CJS | 12 | `node_constructor_call_eq`; compile+validate pattern |
| `base64` | python_module | 20 | encode/decode roundtrips, padding |
| `chalk` | node/ESM | 10 | ANSI color codes, level:0 stripping; ESM (`esm: true`) |
| `curl` | cli | 12 | offline-safe: version, --help, flag parsing |
| `datetime` | python_module | 15 | date/datetime attrs, strftime, method chaining |
| `difflib` | python_module | 17 | SequenceMatcher, get_close_matches, junk predicates |
| `hashlib` | python_module | 41 | SHA-256/SHA-1/MD5/SHA-512 + SHA-3/BLAKE2 extensions |
| `json` | python_module | 22 | dumps/loads roundtrip, indent, sort_keys, error cases |
| `libcrypto` | ctypes | 14 | OpenSSL version, RAND_bytes/status, OID/NID registry |
| `minimist` | node/CJS | 9 | arg parsing, `function: null` direct-call pattern |
| `openssl` | cli | 16 | version, hash, rand, enc; cross-spec with hashlib |
| `pathlib` | python_module | 17 | PurePosixPath: components, predicates, manipulation |
| `re` | python_module | 22 | sub, findall, split, escape, error on bad pattern |
| `semver` | node/CJS | 24 | valid, clean, satisfies, compare, range ops |
| `sqlite3` | python_module | 13 | DDL, DML, types, `python_sqlite_roundtrip` |
| `struct` | python_module | 24 | pack/unpack, calcsize, error cases |
| `urllib_parse` | python_module | 18 | urlparse, quote/unquote, urljoin, urlencode, parse_qs |
| `uuid` | node/CJS | 8 | validate, version detection |
| `zlib` | ctypes | 23 | compress/decompress roundtrip, crc32, adler32 |
| `zstd` | ctypes | 15 | versionString, maxCLevel, compressBound, isError |

**CI**: GitHub Actions matrix on ubuntu-latest + macos-latest (Python 3.9–3.12, Node 22) plus a separate FreeBSD 14.2 job. The ubuntu/3.12 job uploads `verify-all-specs-results.json` as a GitHub Actions artifact.

**`skip_if` expression language:**
- `lib_version` — library version string (e.g. `"1.2.12"`)
- `platform` — OS: `"darwin"`, `"linux"`, `"freebsd"`, `"win32"`
- `semver_satisfies(lib_version, ">=1.3")` — semver range check

---

## Completed Cycles

### Cycle 1 (2026-03-26 → 2026-04-01)
Added: ctypes backend (zlib), python_module backend (base64, json, hashlib, struct, sqlite3, re), CLI backend (curl, openssl), node backend (semver, uuid, minimist), cross-spec interoperability (openssl↔hashlib), `--baseline` diff mode, schema validation, behavioral_spec auto-injection in extract_candidates.py, validate_record.py integration, `make verify-all-specs`, macOS CI, FreeBSD self-hosted worker sync.

### Cycle 2 (2026-04-02)
Added: `node_constructor_call_eq` kind + ajv spec, datetime + pathlib specs, `python_call_eq` method/method_chain chaining, `spec_for_versions` enforcement + version detection for all backends, `spec_coverage.py`, `verify_all_specs.py`, `--watch` mode, FreeBSD CI job.

### Cycle 3 (2026-04-03)
Added: hashlib SHA-3/BLAKE2 extensions (41 total invariants), `urllib_parse` spec (18 invariants), `difflib` spec (17 invariants), `zstd` ctypes spec (15 invariants).

### Cycle 4 (2026-04-03)
Added: ZSDL compiler (`tools/zsdl_compile.py`), all 18 specs converted to ZSDL, 68 compiler tests. `_build/zspecs/` is the build output directory (gitignored); `zspecs/*.zspec.zsdl` are the committed sources.

### Cycle 5 (2026-04-03 → 2026-04-04)
Added: `skip_if` expression language (`platform`, `semver_satisfies`), spec authoring guide (`docs/writing-specs.md`), `tools/orphan_specs.py`, CI artifact upload (verify-all-specs JSON), ESM node backend support (`esm: true`), chalk spec (10 invariants), libcrypto ctypes spec (14 invariants).

---

## Next Steps (Candidate Items)

### A. Real-data pipeline run

All tooling is in place but no real snapshot has been imported. To exercise the full pipeline:

```bash
# 1. Import a nixpkgs or FreeBSD ports snapshot
make import-npm NPM_SEED=reports/npm-seed.txt      # or import-pypi
# 2. Extract Z-layer candidates
make extract SNAPSHOT=snapshots/YYYY-MM-DD CANDIDATES_OUT=reports/top-candidates.json
# 3. Check coverage
make spec-coverage EXTRACTION_DIR=reports/extractions/
# 4. Find orphans
make orphan-specs EXTRACTION_DIR=reports/extractions/
```

The gap list from `spec-coverage` will show which high-priority candidates need specs next.

### B. More Z-specs

Candidates based on dependency fan-in (once a real snapshot is available):

| Library | Backend | Notes |
|---------|---------|-------|
| `lz4` | ctypes | Fast compression; similar pattern to zstd |
| `pcre2` | ctypes | Regex engine; cross-spec vs Python re |
| `zlib-ng` | ctypes | Drop-in zlib replacement; test version detection |
| `express` | node/CJS | HTTP framework; needs a mock server pattern |

### C. Test vector coverage report

A tool that reports, per spec, which RFC sections have test vectors and which are untested. Useful for auditing spec completeness before a compliance review.

### D. Spec schema v0.2

Current schema (v0.1) doesn't validate `skip_if` syntax or `esm` flag. A v0.2 bump could:
- Add `esm: bool` to the library schema
- Add `skip_if` as an optional string field on invariants (already used, not yet in schema)
- Validate that `arg_types` length matches `args` length for ctypes specs
