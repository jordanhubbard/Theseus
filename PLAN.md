# Theseus — Plan and State

## Current State (2026-04-04)

**30 Z-layer specs · 540 invariants · 3 CI platforms (ubuntu, macos, freebsd)**

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
| `numpy` | python_module | 20 | dtype/itemsize, shape/ndim, constants, arithmetic, array ops, errors |
| `pyyaml` | python_module | 18 | safe_load scalars+structures, dump, safe_dump, errors |
| `re` | python_module | 22 | sub, findall, split, escape, error on bad pattern |
| `semver` | node/CJS | 24 | valid, clean, satisfies, compare, range ops |
| `sqlite3` | python_module | 13 | DDL, DML, types, `python_sqlite_roundtrip` |
| `struct` | python_module | 24 | pack/unpack, calcsize, error cases |
| `urllib_parse` | python_module | 18 | urlparse, quote/unquote, urljoin, urlencode, parse_qs |
| `urllib3` | python_module | 18 | URL parse, Retry config, exceptions, version, request headers |
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

### Cycle 6 (2026-04-04)
Real-data pipeline run (141 records, 4 ecosystems); numpy spec (20 invariants), pyyaml spec (18 invariants), urllib3 spec (18 invariants); `tools/spec_vector_coverage.py` (item C); schema v0.2 with `esm`/`arg_types`/length validation (item D). Total: 23 specs · 408 invariants · 1398 tests.

### Cycle 7 (2026-04-04)
lxml (25), packaging (24), pillow (21), psutil (17), pygments (19). Added `packaging` submodule preloads to `verify_behavior.py` alongside existing `pygments` preloads. Total: 28 specs · 514 invariants · 1628 tests.

### Cycle 8 (2026-04-04)
lz4 (8, ctypes + new `lz4_roundtrip` kind), express (16, node/CJS + new `node_factory_call_eq` kind). Total: 30 specs · 540 invariants · 1675 tests.

---

## Next Steps (Candidate Items)

### A. Real-data pipeline run — DONE (2026-04-04)

Pipeline exercised against a real snapshot (`snapshots/2026-04-03/`): 141 canonical records
across nixpkgs (3), freebsd_ports (3), pypi (99), npm (36).

**Results:**
- 136 unique candidates ranked; top 50 extracted to `reports/extractions/`
- Spec coverage: **3/50 (6%)** — curl, openssl, zlib covered
- Orphan specs: 17/20 specs have no extraction record — all Python stdlib and most Node specs
  are absent from PyPI/npm snapshots (stdlib is not a package; semver/chalk ranked #94/#115)

**Gap list highlights** (top uncovered PyPI candidates):
lxml, numpy, pillow, psutil, pygments, pyyaml, urllib3, packaging, markupsafe, msgpack

**Key insight:** Python stdlib specs (base64, datetime, hashlib, json, pathlib, re, sqlite3,
struct, urllib_parse, difflib) cannot appear in a PyPI snapshot — they are built-in. Orphan
coverage for those specs is expected and correct.

**To reproduce:**
```bash
python3 theseus/importer.py --nixpkgs output/nixpkgs/ --out snapshots/2026-04-03/
python3 theseus/importer.py --pypi-list /tmp/pypi-packages.txt --out snapshots/2026-04-03/
python3 theseus/importer.py --npm-list /tmp/npm-packages.txt --out snapshots/2026-04-03/
python3 tools/top_candidates.py snapshots/2026-04-03/ --out reports/top-candidates.json
python3 tools/extract_candidates.py snapshots/2026-04-03/ reports/top-candidates.json --top 50 --out reports/extractions/
python3 tools/spec_coverage.py reports/extractions/
python3 tools/orphan_specs.py reports/extractions/
```

### B. More Z-specs — DONE (all priorities, 2026-04-04)

numpy (20), pyyaml (18), urllib3 (18) added in Cycle 6.

Remaining candidates from the gap list:

| Library | Backend | Priority | Notes |
|---------|---------|----------|-------|
All planned B-candidates complete. Next candidates (if needed):
| `pcre2` | ctypes | — | Regex engine; cross-spec vs Python re |
| `markupsafe` | python_module | — | HTML escaping; Jinja2 dependency |
| `msgpack` | python_module | — | Binary serialization; pack/unpack roundtrip |

### C. Test vector coverage report — DONE (2026-04-04)

`tools/spec_vector_coverage.py`: reports per-spec, per-category invariant description coverage.
All 23 specs score 100% (408/408 described). `make spec-vector-coverage`.

### D. Spec schema v0.2 — DONE (2026-04-04)

- `esm: bool` added to library schema
- `arg_types: string[]` added to invariant schema
- `schema_version` enum accepts `"0.1"` (compat) and `"0.2"` (current)
- `validate_zspec.py`: programmatic `arg_types`/`args` length check
- `zsdl_compile.py`: emits `schema_version: "0.2"` on all new compilations
