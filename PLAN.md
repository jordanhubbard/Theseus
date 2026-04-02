# Theseus — Plan and State

## Current State (2026-04-02)

**15 Z-layer specs · 257 invariants · 1025 tests · 3 CI platforms (ubuntu, macos, freebsd)**

### What is built

**Core pipeline** (original): bootstrap importer, overlap report, candidate ranker, phase-Z extractor, snapshot diff, record validator.

**Z-layer behavioral spec system** (added this cycle):

| Component | Description |
|-----------|-------------|
| `zspecs/*.zspec.json` | 15 machine-readable behavioral contracts for OSS libraries |
| `tools/verify_behavior.py` | Harness: loads a spec, runs every invariant against the installed library, reports pass/fail/skip |
| `tools/validate_zspec.py` | Static validation of spec files against `zspecs/schema/behavioral-spec.schema.json` |
| `tools/verify_all_specs.py` | Runs all specs in one pass; writes a JSON results file for CI dashboards and `--baseline` |
| `tools/spec_coverage.py` | Reads extraction output, reports which candidates have a spec (covered) vs not (gap list) |
| `zspecs/schema/behavioral-spec.schema.json` | JSON Schema for Z-spec files (schema_version 0.1) |

**Backends** supported by the harness:

| Backend | How it loads the library | Used by |
|---------|--------------------------|---------|
| `ctypes` | `ctypes.CDLL` via `find_library` | zlib, openssl (ctypes) |
| `python_module` | `importlib.import_module` | base64, datetime, hashlib, json, pathlib, re, sqlite3, struct |
| `cli` | subprocess (node, openssl, curl) | curl, openssl (CLI), ajv, minimist, semver, uuid |

**Invariant kinds** (30 total, all registered in schema enum and KNOWN_KINDS):

- **Equality**: `constant_eq`, `call_eq`, `call_ge`, `python_call_eq`, `node_module_call_eq`, `node_constructor_call_eq`
- **Returns/raises**: `call_returns`, `python_call_raises`, `error_on_bad_input`
- **Roundtrip**: `roundtrip`, `python_encode_decode_roundtrip`, `python_struct_roundtrip`, `python_sqlite_roundtrip`
- **Hash**: `hash_known_vector`, `hash_incremental`, `hash_object_attr`, `hash_digest_consistency`, `hash_copy_independence`, `hash_api_equivalence`, `python_set_contains`, `hash_digest_consistency`
- **CLI**: `cli_exits_with`, `cli_stdout_eq`, `cli_stdout_contains`, `cli_stdout_matches`, `cli_stderr_contains`
- **Version/wire**: `version_prefix`, `wire_bytes`, `incremental_eq_oneshot`

**Harness features**:
- `python_call_eq`: `method`/`method_args`/`method_chain` for chained attribute/method access on results
- `--baseline`: diff current run against saved JSON, exit non-zero on regressions
- `--watch`: polls spec file, reruns and clears terminal on each save (TDD-style)
- `--json-out`: write per-invariant results as JSON
- `--filter`: run only one category
- `--list`: list all invariant IDs with descriptions
- Version detection (`_get_lib_version`) for all 3 backends; `spec_for_versions` range check with warning; `skip_if` receives real `lib_version`

**Specs in `zspecs/`**:

| Spec | Backend | Invariants | Notes |
|------|---------|-----------|-------|
| `ajv` | cli/node | 12 | `node_constructor_call_eq`; compile+validate pattern |
| `base64` | python_module | 20 | encode/decode roundtrips, padding |
| `curl` | cli | 12 | offline-safe: version, --help, flag parsing |
| `datetime` | python_module | 15 | date/datetime attrs, strftime, method chaining |
| `hashlib` | python_module | 23 | SHA-256/SHA-1 vectors, incremental, copy independence |
| `json` | python_module | 22 | dumps/loads roundtrip, indent, sort_keys, error cases |
| `minimist` | cli/node | 9 | arg parsing, `function: null` direct-call pattern |
| `openssl` | cli | 16 | version, hash, rand, enc; cross-spec with hashlib |
| `pathlib` | python_module | 14 | PurePosixPath: components, predicates, manipulation |
| `re` | python_module | 22 | sub, findall, split, escape, error on bad pattern |
| `semver` | cli/node | 24 | valid, clean, satisfies, compare, range ops |
| `sqlite3` | python_module | 13 | DDL, DML, types, `python_sqlite_roundtrip` |
| `struct` | python_module | 24 | pack/unpack, calcsize, error cases |
| `uuid` | cli/node | 8 | validate, version detection |
| `zlib` | ctypes | 23 | compress/decompress roundtrip, crc32, adler32 |

**CI**: GitHub Actions matrix on ubuntu-latest + macos-latest (Python 3.9–3.12, Node 22) plus a separate FreeBSD 14.2 job via `cross-platform-actions/action@v0.25.0`.

---

## Completed Cycles

### Cycle 1 (2026-03-26 → 2026-04-01)
Added: ctypes backend (zlib), python_module backend (base64, json, hashlib, struct, sqlite3, re), CLI backend (curl, openssl), node backend (semver, uuid, minimist), cross-spec interoperability (openssl↔hashlib), `--baseline` diff mode, schema validation, behavioral_spec auto-injection in extract_candidates.py, validate_record.py integration, `make verify-all-specs`, macOS CI, FreeBSD self-hosted worker sync.

### Cycle 2 (2026-04-02)
Added: `node_constructor_call_eq` kind + ajv spec, datetime + pathlib specs, `python_call_eq` method/method_chain chaining, `spec_for_versions` enforcement + version detection for all backends, `spec_coverage.py`, `verify_all_specs.py`, `--watch` mode, FreeBSD CI job.

---

## Next Steps (Candidate Items)

### A. More Z-Specs

| Library | Backend | Notes |
|---------|---------|-------|
| `zstd` | ctypes | Compression; cross-spec invariant vs zlib |
| `libssl` | ctypes | Low-level TLS; cross-spec vs openssl CLI |
| `chalk` | cli/node | ANSI stripping; `NO_COLOR` env var behavior |
| `hashlib` ext | python_module | Add sha3_256, blake2b vectors to existing spec |
| `urllib.parse` | python_module | URL parsing; stdlib, pure functions |
| `difflib` | python_module | Sequence diff; stdlib, deterministic |

### B. `skip_if` Expression Language

Currently `skip_if` is a bare `eval()` against `{"lib_version": str}`. Extend to:
- `platform` variable (e.g. `platform == "freebsd"`) for OS-gated invariants
- `semver_satisfies(lib_version, ">=1.2")` helper available in the expression context
- Document the expression language in `docs/architecture.md`

### C. Spec Authoring Guide

A short `docs/writing-specs.md` covering:
- When to use each backend
- How to choose invariant kinds
- How to use `method`/`method_chain` for Python method chaining
- How to use `skip_if` for version-gated invariants
- Test vector discipline (fixed inputs, no `datetime.now()`)

### D. Extraction ↔ Spec Round-Trip Report

`spec_coverage.py` shows which candidates have specs, but doesn't show the reverse: which specs have no corresponding candidate record (orphan specs). A `tools/orphan_specs.py` script could identify specs whose `canonical_name` doesn't appear in any extraction record.

### E. CI: Publish `verify-all-specs` Results as Artifact

In `.github/workflows/ci.yml`, add a step that runs `make verify-all-specs-json` and uploads the output JSON as a GitHub Actions artifact. This makes the per-invariant results browsable in the Actions UI without having to re-run locally.
