# Theseus — Architecture

## Overview

Theseus is a batch analysis toolchain. There is no server, no database, and no persistent state beyond the files you write to disk. The pipeline has two layers:

**Layer 1 — Package recipe pipeline:** normalizes Nixpkgs and FreeBSD Ports records into a shared canonical schema, ranks candidates, and produces merged extraction records.

**Layer 2 — Z-layer behavioral spec system:** machine-readable contracts that describe how OSS libraries actually behave; verified against the installed library by a test harness.

```
Source Trees (Nixpkgs, FreeBSD Ports)
        │
        ▼
  tools/bootstrap_canonical_recipes.py   ← walks source trees; run by user
        │
        ▼
  snapshots/<date>/                ← one JSON file per package per ecosystem
        │
        ├─► tools/overlap_report.py      ← compare ecosystems; write reports/overlap/
        ├─► tools/top_candidates.py      ← rank packages; write reports/top-candidates.json
        ├─► tools/validate_record.py     ← validate records against schema rules
        ├─► tools/diff_snapshots.py      ← diff two snapshots to track ecosystem drift
        └─► tools/extract_candidates.py  ← phase Z: merge top candidates; write reports/extractions/
                │                            (auto-injects behavioral_spec for known libraries)
                ▼
          reports/extractions/*.json     ← one merged record per top-N candidate
                │
                └─► tools/spec_coverage.py  ← report covered vs gap candidates

zspecs/*.zspec.json                      ← behavioral contracts (one per library)
        │
        ├─► tools/verify_behavior.py     ← harness: run invariants against installed library
        ├─► tools/validate_zspec.py      ← static JSON schema validation of spec files
        ├─► tools/verify_all_specs.py    ← run all specs; write JSON results file
        └─► make verify-all-specs        ← aggregate text report across all specs
```

---

## Layer 1 — Package Recipe Pipeline

### Schema

The canonical record format is defined in `schema/package-recipe.schema.json` (JSON Schema draft 2020-12). Key design decisions:

- **`provenance.confidence`** is a first-class field. Records admit their own uncertainty. Importers set this value; downstream tools can filter or weight by it.
- **`extensions`** is a pass-through object for ecosystem-specific fields that don't map cleanly to the canonical schema. Nothing in the toolchain reads it; it exists so information isn't discarded.
- **`unmapped`** and **`warnings`** in `provenance` capture fields the importer saw but couldn't normalize. These are signals for future schema evolution.
- **`behavioral_spec`** (optional, string) — repo-relative path to a matching Z-spec file. Injected automatically by `extract_candidates.py` when a spec exists for the candidate's `canonical_name`.
- The schema uses `additionalProperties: true` on most sub-objects. The canonical fields are required; extra fields are allowed. This makes forward-compatibility easier as ecosystems evolve.

See `docs/schema-evolution.md` for versioning rules, the version history, and guidance on when and how to bump `schema_version`.

### Snapshot Format

A snapshot is a directory tree of JSON files, one per record. File naming is arbitrary; tools discover records by walking the tree and checking for an `"identity"` key. The only reserved filename is `manifest.json` (skipped by all tools).

Records from different ecosystems for the same canonical package are separate files. The overlap tool joins them by `canonical_name`.

### Known importer limitations

#### Nixpkgs: regex-based parsing

The Nixpkgs importer uses regex heuristics on `default.nix` files rather than evaluating Nix expressions. This means:

- Values set by conditional expressions, `lib.optionalString`, or dynamic attribute paths may be parsed incorrectly or missed entirely.
- The `confidence` score reflects field presence, not parse correctness. A record can have `confidence: 0.95` and still contain a wrong dependency list if the Nix source used a non-obvious pattern.
- For higher accuracy, run `nix-instantiate --eval --json` against each package and feed the result to a future importer variant.

#### FreeBSD Ports: slave port support

FreeBSD Ports uses a "slave port" pattern where a port sets `MASTERDIR` to point to a sibling directory and inherits most of its Makefile. The importer handles this via `_resolve_masterdir()` (see `theseus/importer.py`): when `MASTERDIR` is detected, the master Makefile is loaded and its variables are merged as defaults, with the slave's own variables taking precedence. The slave's source path is preserved in `provenance.warnings` for traceability.

Three common `MASTERDIR` patterns are resolved:
- `${.CURDIR}/../<portname>` — sibling in same category
- `${.CURDIR}/../../<cat>/<portname>` — port in a different category
- `${.CURDIR:H:H}/<cat>/<portname>` — using `:H` (head = parent) modifiers

If `MASTERDIR` contains unresolvable make variables or the resolved path does not exist, the port is still imported with a warning rather than silently skipped.

### Tools

#### `tools/overlap_report.py`

Reads a snapshot directory, groups records by `canonical_name`, and classifies each group:

- **overlap**: present in both `nixpkgs` and `freebsd_ports`
- **only_nix**: present only in `nixpkgs`
- **only_ports**: present only in `freebsd_ports`
- **version_skew**: present in both, but with different versions

Writes five JSON files to `--out`: `summary.json`, `overlap.json`, `only_nix.json`, `only_ports.json`, `version_skew.json`.

#### `tools/top_candidates.py`

Reads a snapshot directory, groups records by `canonical_name`, scores each group, and writes a ranked list.

Scoring heuristics (see source for current weights):

| Signal | Direction | Rationale |
|--------|-----------|-----------|
| `provenance.confidence` | Higher = better | More reliable records |
| Dual-ecosystem presence | +25 bonus | Already normalized in two worlds |
| Test presence | +15 | Easier to validate extraction |
| Dependency count | Fewer = better | Less surface area |
| Patch count | More = worse | Patches signal divergence from upstream |

#### `tools/validate_record.py`

Validates one or more canonical records (files or directories) against the schema rules. Stdlib-only structural validation — checks required fields, types, and value ranges. Also runs the behavioral spec harness (`verify_behavior.py`) for any record that has a `behavioral_spec` field. Exits non-zero if any record is invalid.

```bash
python3 tools/validate_record.py examples/
python3 tools/validate_record.py --strict snapshot/
python3 tools/validate_record.py record.json
```

`--strict` additionally flags empty summaries, empty homepages, and non-empty `unmapped`/`warnings` fields.

#### `tools/diff_snapshots.py`

Compares two snapshot directories (e.g. from consecutive bootstrap runs) and classifies every package as added, removed, version-changed, ecosystem-changed, or unchanged.

```bash
python3 tools/diff_snapshots.py --before snapshots/2026-03-01 --after snapshots/2026-03-26
python3 tools/diff_snapshots.py --before snapshots/old --after snapshots/new --out reports/drift.json
```

#### `tools/extract_candidates.py`

Phase Z: takes the `top_candidates.json` ranking and the snapshot directory, and produces one merged extraction record per top-N candidate in `reports/extractions/`.

Each extraction record contains three sections:

- **`merged`** — unified view across all ecosystems: summary, homepage, license union, maintainer union, conflict union, dependency union, platform union, source URL union, and a `deprecated` flag.
- **`per_ecosystem`** — the full original canonical record for each ecosystem, keyed by ecosystem name.
- **`analysis`** — structured comparison: version agreement, confidence averages, dependency counts, license agreement, deprecation status, and human-readable notes.

A `manifest.json` is written alongside the per-package files. The tool also auto-injects `behavioral_spec` pointing to `zspecs/<canonical_name>.zspec.json` for any candidate whose name matches a spec file.

#### `tools/spec_coverage.py`

Reads an extraction output directory and reports which candidates have a behavioral spec (covered) and which do not (gap list), sorted by composite score. Useful for deciding where to write the next spec.

```bash
python3 tools/spec_coverage.py reports/extractions/ --top 50
python3 tools/spec_coverage.py reports/extractions/ --json > coverage.json
make spec-coverage EXTRACTION_DIR=reports/extractions/ TOP=50
```

---

## Layer 2 — Z-Layer Behavioral Spec System

### Purpose

A behavioral spec (`*.zspec.json`) is a machine-readable contract that describes how a library actually behaves: what functions it exposes, what they return for specific inputs, and what invariants must hold regardless of implementation. Specs are:

- Derived from public documentation only — not from source code. This preserves clean-room provenance.
- Versioned against the library (`spec_for_versions` semver range).
- Verifiable: the harness runs every invariant against the real installed library and reports pass/fail/skip.

### Z-Spec Schema

Every spec is a JSON file validated against `zspecs/schema/behavioral-spec.schema.json` (schema_version 0.1). Required top-level fields:

| Field | Description |
|-------|-------------|
| `schema_version` | Spec schema version (currently `"0.1"`) |
| `identity` | `canonical_name`, `spec_for_versions` semver range, `public_docs_url` |
| `provenance` | `derived_from` (list of sources), `not_derived_from` (clean-room boundary) |
| `library` | `backend`, `module_name`/`command`, `soname_patterns` |
| `constants` | Named constants grouped by category |
| `types` | C struct layouts (ctypes field lists) |
| `functions` | Public API function signatures |
| `invariants` | Array of executable behavioral contracts |
| `wire_formats` | Byte-level format definitions |
| `error_model` | Return code semantics, error codes |

Each invariant has: `id` (unique stable string), `description`, `category`, `kind`, `spec` (kind-specific parameters), and optional `rfc_reference` and `skip_if`.

### Backends

The harness supports three backends, selected by `library.backend` in the spec:

| Backend | Value | How it loads | Used for |
|---------|-------|-------------|----------|
| C shared library | `"ctypes"` | `ctypes.CDLL` via `ctypes.util.find_library`, falling back to platform-conventional names | Native C libraries (zlib, openssl ctypes) |
| Python module | `"python_module"` | `importlib.import_module(module_name)` | Python stdlib and pip packages |
| CLI / subprocess | `"cli"` | `shutil.which(command)`, then `subprocess.run` per invariant | CLI tools and Node.js npm packages |

For the `cli` backend with `module_name` set, the harness verifies that `require(module_name)` succeeds in Node.js before running any invariants.

### Invariant Kinds

Invariants are grouped by their execution pattern (`kind`):

**Equality (python_module backend)**
- `python_call_eq` — call `module.function(*args, **kwargs)`, compare result to `expected`. Supports `method`/`method_args`/`method_chain` for chained attribute/method access on the return value.
- `python_call_raises` — call function and verify it raises the named exception class.
- `python_encode_decode_roundtrip` — encode then decode bytes and verify round-trip equality.
- `python_struct_roundtrip` — pack then unpack struct bytes and verify equality.
- `python_sqlite_roundtrip` — create in-memory SQLite DB, run setup SQL, query, verify rows.
- `python_set_contains` — verify a value is a member of a module-level set.

**Equality (ctypes backend)**
- `call_eq` — call C function via ctypes, compare return value.
- `call_ge` — compare return value with `>=`.
- `call_returns` — verify return value is non-null/non-zero.
- `constant_eq` — verify a named constant equals `expected`.
- `roundtrip` — compress+decompress or encode+decode in C.
- `wire_bytes` — verify exact byte output.
- `version_prefix` — verify version string starts with expected prefix.
- `incremental_eq_oneshot` — verify incremental API produces same output as one-shot.
- `error_on_bad_input` — verify C function returns error code on invalid input.
- `hash_known_vector` — hash a fixed input and compare to known digest.
- `hash_incremental` — verify incremental hash equals one-shot hash.
- `hash_object_attr` — verify a hash object attribute (e.g. `digest_size`).
- `hash_digest_consistency` — hash same input twice, verify results are identical.
- `hash_copy_independence` — verify copy of hash state is independent after mutation.
- `hash_api_equivalence` — verify two API paths produce the same digest.

**CLI / Node.js**
- `cli_exits_with` — verify exit code.
- `cli_stdout_eq` — verify stdout equals expected string.
- `cli_stdout_contains` — verify stdout contains a substring.
- `cli_stdout_matches` — verify stdout matches a regex.
- `cli_stderr_contains` — verify stderr contains a substring.
- `node_module_call_eq` — run `node -e` inline script: `require(mod)[fn](...args)`, compare result.
- `node_constructor_call_eq` — run `node -e` inline script: `new m[Class](...ctorArgs)[method](...args)`, optionally call result as function (`then_call: true`). Used for constructor-based npm APIs (e.g. Ajv).

### Method Chaining in `python_call_eq`

`python_call_eq` supports three optional chaining fields in the spec block:

| Field | Type | Meaning |
|-------|------|---------|
| `method` | string | Attribute or method to access/call on the function's return value |
| `method_args` | array | Arguments to pass when `method` is callable |
| `method_chain` | string | Second attribute or zero-arg method to call on the result of `method` |

Example — `date.fromisoformat("2024-03-15").strftime("%Y/%m/%d")`:
```json
{
  "function": "date.fromisoformat",
  "args": [{"type": "str", "value": "2024-03-15"}],
  "method": "strftime",
  "method_args": [{"type": "str", "value": "%Y/%m/%d"}],
  "expected": {"type": "str", "value": "2024/03/15"}
}
```

Example — `PurePosixPath("/etc/passwd").parent.__str__()`:
```json
{
  "function": "PurePosixPath",
  "args": [{"type": "str", "value": "/etc/passwd"}],
  "method": "parent",
  "method_chain": "__str__",
  "expected": {"type": "str", "value": "/etc"}
}
```

### Version Detection and `spec_for_versions`

The harness automatically detects the installed library version via `_get_lib_version()`:

- **python_module**: `importlib.metadata.version(module_name)`, falling back to `sys.version_info` for stdlib modules.
- **cli (node)**: runs `node -e "process.stdout.write(require('<mod>/package.json').version)"`.
- **ctypes**: calls `lib.<version_function>()` if `version_function` is set in the spec's `library` block.

The detected version is:
1. Printed on stdout (`Library version: X.Y.Z`).
2. Checked against `identity.spec_for_versions` (a semver range). Mismatches emit a `WARNING` to stderr. Parsing uses `packaging.specifiers.SpecifierSet` if available, with a stdlib fallback for simple `>=X.Y` ranges.
3. Passed as `lib_version` to all `skip_if` expressions, enabling version-gated invariants.

### Harness Tools

#### `tools/verify_behavior.py`

Primary verification harness. Loads a single spec, resolves the library, and runs all invariants.

```bash
python3 tools/verify_behavior.py zspecs/zlib.zspec.json
python3 tools/verify_behavior.py zspecs/zlib.zspec.json --filter checksum
python3 tools/verify_behavior.py zspecs/zlib.zspec.json --verbose
python3 tools/verify_behavior.py zspecs/zlib.zspec.json --list
python3 tools/verify_behavior.py zspecs/zlib.zspec.json --json-out results.json
python3 tools/verify_behavior.py zspecs/zlib.zspec.json --baseline baseline.json
python3 tools/verify_behavior.py zspecs/zlib.zspec.json --watch
```

Exit codes: `0` all passed, `1` one or more failed, `2` harness error.

**`--baseline`**: loads a previous `--json-out` file, diffs current results against it, prints regressions (pass→fail), fixes (fail→pass), added, and removed invariants. Exits non-zero if there are regressions.

**`--watch`**: polls the spec file every 0.5s; clears the terminal and reruns on each save. Useful for TDD-style spec authoring. Exits 0 on Ctrl-C.

#### `tools/validate_zspec.py`

Static validator for spec files. Uses `jsonschema` if installed, stdlib structural checks otherwise.

```bash
python3 tools/validate_zspec.py                   # validate all zspecs/*.zspec.json
python3 tools/validate_zspec.py zspecs/zlib.zspec.json
make validate-zspecs
```

Exit codes: `0` all valid, `1` one or more invalid, `2` usage error.

#### `tools/verify_all_specs.py`

Runs every spec in `zspecs/` and writes a single JSON results document. Suitable for CI dashboards and `--baseline` regression tracking.

```bash
python3 tools/verify_all_specs.py
python3 tools/verify_all_specs.py --out reports/results.json
python3 tools/verify_all_specs.py zspecs/zlib.zspec.json zspecs/re.zspec.json
make verify-all-specs-json OUT=reports/results.json
```

Output JSON structure:
```json
{
  "generated_at": "2026-04-02T12:00:00Z",
  "summary": { "total_specs": 15, "specs_ok": 15, "specs_failed": 0,
                "total_invariants": 257, "passed": 257, "failed": 0, "skipped": 0 },
  "specs": [
    { "spec": "zspecs/zlib.zspec.json", "canonical_name": "zlib",
      "lib_version": "1.2.12", "error": null,
      "summary": { "total": 23, "passed": 23, "failed": 0, "skipped": 0 },
      "invariants": [ { "id": "zlib.compress.roundtrip", "passed": true, ... } ]
    }
  ]
}
```

The per-invariant list format is compatible with `--baseline` (same `{id, passed, message, skip_reason}` structure).

### Currently Implemented Specs

| Spec | Backend | Invariants | Highlights |
|------|---------|-----------|------------|
| `ajv` | cli/node | 12 | `node_constructor_call_eq`; compile+validate two-step |
| `base64` | python_module | 20 | encode/decode, urlsafe, padding edge cases |
| `curl` | cli | 12 | offline-safe: version flags, help output, --max-time |
| `datetime` | python_module | 15 | date/datetime attrs, strftime, `method`/`method_args` chaining |
| `difflib` | python_module | 17 | SequenceMatcher ratio, find_longest_match, get_close_matches, junk predicates |
| `hashlib` | python_module | 41 | SHA-256/SHA-1/MD5/SHA-512 vectors; SHA-3/BLAKE2b/BLAKE2s extensions; incremental, copy independence |
| `json` | python_module | 22 | dumps/loads roundtrip, indent, sort_keys, unicode, error cases |
| `minimist` | cli/node | 9 | CLI arg parsing; `function: null` for direct-callable modules |
| `openssl` | cli | 16 | version, dgst, rand, enc; cross-spec vector shared with hashlib |
| `pathlib` | python_module | 14 | PurePosixPath: name/stem/suffix, parent (method_chain), relative_to |
| `re` | python_module | 22 | sub, findall, split, escape, error on invalid pattern |
| `semver` | cli/node | 24 | valid, clean, satisfies, gt/lt/eq, compare, range ops |
| `sqlite3` | python_module | 13 | DDL, DML, `python_sqlite_roundtrip` for row comparison |
| `struct` | python_module | 24 | pack/unpack formats, calcsize, big/little endian, error cases |
| `urllib_parse` | python_module | 18 | urlparse attributes, quote/unquote, urljoin, urlencode, parse_qs |
| `uuid` | cli/node | 8 | validate v4, version detection |
| `zlib` | ctypes | 23 | compress/decompress roundtrip, crc32, adler32, error codes |
| `zstd` | ctypes | 15 | ZSTD_versionString, maxCLevel, compressBound, isError; `call_ge` simple mode |

---

## Tests

Tests live in `tests/`. Run with `make test` (requires `pytest`).

### Layer 1 tests

| File | Tests |
|------|-------|
| `tests/conftest.py` | Adds repo root and `tools/` to `sys.path` |
| `tests/test_schema.py` | JSON Schema structure and all example records |
| `tests/test_bootstrap.py` | Bootstrap importer parsing functions and import runners |
| `tests/test_overlap_report.py` | Overlap report logic |
| `tests/test_top_candidates.py` | Candidate scoring and ranking |
| `tests/test_validate_record.py` | Record field and type checking, behavioral_spec integration |
| `tests/test_diff_snapshots.py` | Snapshot comparison logic |
| `tests/test_extract_candidates.py` | Merging, analysis, auto behavioral_spec injection |

### Layer 2 (Z-layer) tests

| File | Tests |
|------|-------|
| `tests/test_verify_behavior.py` | Core harness: spec loading, library loading, ctypes backend |
| `tests/test_verify_behavior_cli.py` | CLI backend, baseline/diff mode |
| `tests/test_verify_behavior_curl.py` | curl spec integration |
| `tests/test_verify_behavior_npm.py` | uuid, minimist, compact JSON comparison |
| `tests/test_verify_behavior_semver.py` | semver spec integration (45 tests) |
| `tests/test_verify_behavior_stdlib.py` | base64, json, hashlib, struct, sqlite3 specs |
| `tests/test_verify_behavior_stdlib2.py` | re, sqlite3 python_sqlite_roundtrip |
| `tests/test_verify_behavior_stdlib3.py` | datetime, pathlib; method chaining unit tests |
| `tests/test_verify_behavior_stdlib4.py` | hashlib SHA-3/BLAKE2 extensions, urllib_parse, difflib specs |
| `tests/test_verify_behavior_zstd.py` | zstd ctypes spec; call_ge simple mode, version_prefix |
| `tests/test_verify_behavior_version.py` | Version detection, spec_for_versions enforcement |
| `tests/test_verify_behavior_watch.py` | --watch mode (subprocess + unit) |
| `tests/test_validate_zspec.py` | Z-spec static validator |
| `tests/test_spec_coverage.py` | spec_coverage.py report generation |
| `tests/test_verify_all_specs.py` | verify_all_specs.py, integration: all 19 specs pass |

---

## Continuous Integration

`.github/workflows/ci.yml` runs on every push and pull request to `main`.

**Matrix job** (`test`): ubuntu-latest + macos-latest × Python 3.9/3.10/3.11/3.12 × Node 22. Steps: checkout, setup-python, setup-node, `npm install`, `make validate-zspecs`, `make test`, `python3 tools/validate_record.py examples/ --quiet`.

**FreeBSD job** (`freebsd`): ubuntu-latest runner with `cross-platform-actions/action@v0.25.0` launching a FreeBSD 14.2 VM. Installs Python 3.11, Node 22, npm packages via `pkg`, then runs `make validate-zspecs && make test`. Catches platform-specific divergences (LibreSSL vs OpenSSL, different libc errno values).
