# Theseus — Plan and State

## Current State (2026-04-13)

**356 core specs · 10,480 wave-series specs · 10,836 total .zsdl files · 2 CI platforms (ubuntu, macos)**
**Synthesis pipeline landed (theseus/pipeline.py) — compile→verify_real→synthesize→gate→annotate**
**Synthesis gate not yet applied to any existing spec — full backlog pending (see Backlog section)**

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

**CI**: GitHub Actions matrix on ubuntu-latest + macos-latest (Python 3.9–3.12, Node 22). The ubuntu/3.12 job uploads `verify-all-specs-results.json` as a GitHub Actions artifact.

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

### Cycle 9 (2026-04-05)
pcre2 (16, ctypes + new `pcre2_match` kind), markupsafe (21), msgpack (22). Pipeline coverage 6% → 22% → 24% (12/50). Total: 33 specs · 579 invariants · 1777 tests.

### Cycle 10 (2026-04-05)
attrs (14), chardet (16), pyparsing (15), tomli/tomllib (22). Pipeline coverage → 34% (17/50). Total: 37 specs · 650 invariants · 1880 tests.

### Cycle 11 (2026-04-05)
six (11), decorator (12), idna (16), platformdirs (13), pytz (16). Pipeline coverage → 44% (22/50). Total: 42 specs · 732 invariants · 2088 tests.

### Cycle 12 (2026-04-05)
setuptools (14), typing_extensions (13), tzdata (13), wrapt (12), pluggy (13). Pipeline coverage → 52% (26/50). Total: 47 specs · 797 invariants · 2309 tests.

### Cycle 13 (2026-04-05)
certifi (11), colorama (12), more_itertools (14), fsspec (12), dotenv (12). Pipeline coverage → 64% (32/50). Total: 52 specs · 858 invariants · 2499 tests.

### Cycle 14 (2026-04-05)
pathspec (14), filelock (12), traitlets (14), tomlkit (16), defusedxml (14). Pipeline coverage → 74% (37/50). Total: 57 specs · 928 invariants · 2701 tests.

### Cycle 15 (2026-04-05)
distro (15), docutils (12), isodate (16), markdown (14), stevedore (14). Pipeline coverage → 84% (42/50). Total: 62 specs · 999 invariants · 2915 tests.

### Cycle 16 (2026-04-05)
dns (19), networkx (14), tornado (15), zope_interface (13), fontTools (10), protobuf (13), lodash (25), prettier (10). Pipeline coverage → **100% (50/50)**. Total: 70 specs · 1118 invariants · 3203 tests.

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
All planned B-candidates complete (including pcre2, markupsafe, msgpack in Cycle 9).

**All 50 top candidates covered. Pipeline coverage: 100% (50/50).**

### C. Test vector coverage report — DONE (2026-04-04)

`tools/spec_vector_coverage.py`: reports per-spec, per-category invariant description coverage.
All 23 specs score 100% (408/408 described). `make spec-vector-coverage`.

### D. Spec schema v0.2 — DONE (2026-04-04)

- `esm: bool` added to library schema
- `arg_types: string[]` added to invariant schema
- `schema_version` enum accepts `"0.1"` (compat) and `"0.2"` (current)
- `validate_zspec.py`: programmatic `arg_types`/`args` length check
- `zsdl_compile.py`: emits `schema_version: "0.2"` on all new compilations

---

## Wave Series (dict-presence zspecs)

The wave series is a systematic set of dunder-method dict-presence checks across 16 Python stdlib modules: `abc`, `asyncio`, `concurrent.futures`, `decimal`, `functools`, `hashlib`, `inspect`, `io`, `itertools`, `multiprocessing`, `pathlib`, `re`, `socket`, `struct`, `threading`, `uuid`.

Each wave covers 3 dunder methods × 16 modules = 16 zspec files, with suffix `_extraNNNN` where NNNN increments by 15 per wave.

### Completed waves

| Wave | Suffix | Theme |
|------|--------|-------|
| 670 | _extra3346 | `__neg__/__pos__/__abs__` — unary arithmetic |
| 671 | _extra3361 | `__invert__/__floor__/__ceil__` — bitwise/rounding |
| 672 | _extra3376 | `__trunc__/__round__/__index__` — numeric conversion |
| 673 | _extra3391 | `__int__/__float__/__complex__` — type coercion |
| 674 | _extra3406 | `__bool__/__str__/__repr__` — truth/string conversion |
| 675 | _extra3421 | `__hash__/__eq__/__lt__` — hashing + comparison |
| 676 | _extra3436 | `__le__/__gt__/__ge__` — ordering comparison |
| 677 | _extra3451 | `__getitem__/__setitem__/__delitem__` — item access |
| 678 | _extra3466 | `__iter__/__next__/__len__` — iterator/sequence protocol |
| 679 | _extra3481 | `__enter__/__exit__/__call__` — context manager + callable |
| 680 | _extra3496 | `__aenter__/__aexit__/__await__` — async protocol |
| 681 | _extra3511 | `__get__/__set__/__delete__` — descriptor protocol |
| 682 | _extra3526 | `__set_name__/__init_subclass__/__class_getitem__` — class creation hooks |
| 683 | _extra3541 | `__format__/__sizeof__/__dir__` — object introspection |

### Next wave to implement

**Wave 684 — suffix `_extra3556`**

Suggested theme: `__reduce__/__reduce_ex__/__getstate__` — pickle/copy serialization protocol dict-presence checks.

This continues the object model coverage by checking whether each of the 16 stdlib module types defines these pickle-protocol methods in their own `__dict__`. Notable expected results:
- Most types will have `__reduce_ex__` (inherited from `object`) as false (not in their own `__dict__`)
- Some types like `decimal.Decimal` may override these

**Subsequent waves (685+):**

| Wave | Suffix | Suggested Theme |
|------|--------|----------------|
| 685 | _extra3571 | `__copy__/__deepcopy__/__setstate__` — copy protocol |
| 686 | _extra3586 | `__init__/__new__/__del__` — object lifecycle |
| 687 | _extra3601 | `__contains__/__missing__/__reversed__` — container extras |
| 688 | _extra3616 | `__add__/__radd__/__iadd__` — binary addition |
| 689 | _extra3631 | `__sub__/__rsub__/__isub__` — subtraction operators |
| 690 | _extra3646 | `__mul__/__rmul__/__imul__` — multiplication operators |

Each wave follows the same structure: 16 files, one per module, all verified with Python 3.14.x on macOS/Darwin.

---

## Backlog Plan (as of 2026-04-13)

### Context

The unified pipeline (`theseus/pipeline.py`) was established on 2026-04-13.  It
runs five steps in sequence for every `.zspec.zsdl` source file:

```
compile → verify_real → synthesize → gate → annotate
```

The **gate** rejects specs whose synthesis status is `failed` or `build_failed`
(zero passing invariants after all LLM iterations).  `partial` and `infeasible`
pass through.  Every spec that existed before 2026-04-13 was authored without
this gate — the entire repo is backlog.

### Spec inventory (2026-04-13)

| Group | Count | Description |
|-------|------:|-------------|
| Core specs | 356 | Full behavioral specs for real libraries (no `_extra` in name) |
| Extra tier 0 | 216 | Per-module `_extra.zspec.zsdl` — first supplement per module |
| Extra tier 1 | 3,592 | `_extra2` – `_extra99` — incremental per-module behaviors |
| Extra tier 2 | 3,952 | `_extra100` – `_extra3105` — extended per-module coverage |
| PLAN.md waves | ~480 | `_extra3346` – `_extra3541` (waves 670–683, dict-presence checks) |
| **Total** | **~10,836** | |

The core 356 specs are the highest-value targets.  The ~10,480 wave-series
specs are simpler (dict-presence checks, incremental behaviors) and lower
synthesis risk but much higher volume.

### Phase 1 — Commit infrastructure  (target: 2026-04-14)

Everything in the synthesis layer and pipeline is currently untracked.  Must
be committed before any further pipeline work.

| Item | Status |
|------|--------|
| `theseus/synthesis/` — runner, prompt, build, annotate, audit, __init__ | untracked |
| `theseus/pipeline.py` — unified pipeline engine | untracked |
| `tools/run_pipeline.py` — primary authoring CLI | untracked |
| `tools/synthesize_spec.py` — single-spec synthesis CLI | untracked |
| `tools/synthesize_all_specs.py` — bulk synthesis | untracked |
| `tools/synthesize_waves.py` — wave-based synthesis | untracked |
| `tools/synthesize_waves.py` — refactored to use ZSpecPipeline | done (2026-04-13) |
| `tools/synthesize_all_specs.py` — refactored to use ZSpecPipeline | done (2026-04-13) |
| `schema/synthesis-result.schema.json` | untracked |
| `tests/test_synthesis_*.py` (6 files) | untracked |
| `tests/test_synthesize_spec_cli.py` | untracked |
| `.github/workflows/synthesis.yml` | untracked |
| `zspecs/*_extra3511/3526/3541.zspec.zsdl` (48 files, waves 681–683) | untracked |
| `Makefile` — pipeline/synthesize targets | modified |
| `AGENTS.md`, `README.md`, docs — FreeBSD demotion, counter updates | modified |

**Action:** `git add` all of the above and commit.  Run `make test` first to
confirm the 6 new synthesis test modules pass.

### Phase 2 — Compile all specs  (target: 2026-04-14, ~30 min)

```bash
make compile-zsdl   # compiles all 10,836 .zsdl → _build/zspecs/*.zspec.json
```

This is fast (no LLM).  Failures here mean the ZSDL source has syntax or
schema errors that must be fixed before the pipeline can run on them.

Expected: a handful of compile errors in older extra-tier specs that use
syntax not yet in the compiler.  Fix or mark as `infeasible_reason: compile_error`
in the source.

### Phase 3 — Pipeline the 356 core specs  (target: 2026-04-15 → 2026-04-18)

Core specs are the highest-value: full behavioral specs with many meaningful
invariants.  These are the specs most likely to fail the synthesis gate (they
describe complex library behavior).  Failures here are actionable — the spec
needs revision.

```bash
# Process core specs only (exclude wave-series _extra files):
python3 tools/run_pipeline.py $(ls zspecs/*.zspec.zsdl | grep -v '_extra') \
  --jobs 4 --skip-real-verify --max-iterations 3 \
  --out reports/synthesis/core_pipeline_audit.json
```

**Expected outcomes after Phase 3:**

| Outcome | Likely count | Action |
|---------|-------------:|--------|
| `success` | ~80 | No action |
| `partial` | ~120 | Review which invariants fail; may improve with more iterations |
| `infeasible` | ~80 | Confirm and annotate with reason |
| `gated` (failed synthesis) | ~76 | Revise spec or mark `infeasible_reason` |

Specs that are gated must be addressed before they can be considered complete.
The gate is the correctness signal the pipeline was built to provide.

### Phase 4 — Pipeline the extra-tier specs  (target: 2026-04-19 → 2026-05-10)

The ~10,480 wave-series specs are simpler (most invariants are dict-presence
checks with `python_call_eq` returning bool).  Synthesis should be
straightforward for the LLM.  However, the volume demands batched processing.

**Strategy:** process by module prefix in alphabetical batches of ~20 modules
at a time, using `--jobs 4` to parallelize LLM calls.

```bash
# Example: process all 'abc' extra specs
python3 tools/run_pipeline.py zspecs/abc_extra*.zspec.zsdl \
  --jobs 4 --skip-real-verify --max-iterations 2 \
  --out reports/synthesis/abc_extras_audit.json
```

For the PLAN.md wave-series specs (`_extra3346`+), use the wave runner:

```bash
make synthesize-waves-next   # runs next pending wave through pipeline
```

**Automation note:** once Phase 3 is complete and the gate thresholds are
calibrated, Phase 4 can run as a background job over several days.  The
`synthesize_waves.py` state file (`reports/synthesis/wave_state.json`)
persists progress so interrupted runs resume cleanly.

### Phase 5 — Continue PLAN.md wave creation  (ongoing from 2026-04-18)

New dunder-method waves can be created in parallel with Phase 4 synthesis.
The next waves to implement:

| Wave | Suffix | Theme |
|------|--------|-------|
| 684 | _extra3556 | `__reduce__/__reduce_ex__/__getstate__` — pickle protocol |
| 685 | _extra3571 | `__copy__/__deepcopy__/__setstate__` — copy protocol |
| 686 | _extra3586 | `__init__/__new__/__del__` — object lifecycle |
| 687 | _extra3601 | `__contains__/__missing__/__reversed__` — container extras |
| 688 | _extra3616 | `__add__/__radd__/__iadd__` — binary addition |
| 689 | _extra3631 | `__sub__/__rsub__/__isub__` — subtraction operators |
| 690 | _extra3646 | `__mul__/__rmul__/__imul__` — multiplication operators |

Each new wave must go through `make pipeline` (not just `make compile-zsdl`)
before it can be considered complete.  This is the enforcement point of the
new pipeline design.

### Phase 6 — CI integration  (target: 2026-04-20)

Update `.github/workflows/synthesis.yml` to use `run_pipeline.py` instead of
`synthesize_spec.py` so CI runs the full pipeline (not synthesis-only) on any
changed `.zsdl` files:

```yaml
- name: Run pipeline on changed specs
  run: |
    python3 tools/run_pipeline.py ${{ steps.changed.outputs.specs }} \
      --skip-real-verify --max-iterations 3 --no-annotate
```

Also add a `make test-pipeline` target that runs the pipeline in `--dry-run`
mode on a sample of specs (no LLM call) to verify compile + real-verify work
in CI without incurring LLM costs.

### Gate calibration notes

After Phase 3, review the gated specs and establish:

1. **Threshold for `partial`** — if a spec consistently hits 80%+ pass rate, is
   that good enough to commit?  Consider adding `--min-pass-rate` to the gate.

2. **Infeasible categories** — some spec types are structurally infeasible for
   synthesis (C library internals, OS-level calls).  Add a vocabulary of
   `infeasible_reason` values to the ZSDL authoring guide so spec authors can
   annotate proactively.

3. **LLM timeout calibration** — complex specs (pcre2, libxml2) may need
   `--timeout 600` for the synthesis step.  Track per-spec timings in the
   audit report.

### Success criteria

The backlog is cleared when:
- [ ] All 356 core specs have a `synthesis:` block in their `.zspec.zsdl`
- [ ] No core spec is in `gated` state without a documented `infeasible_reason`
- [ ] All PLAN.md waves (670–690+) have synthesis annotations
- [ ] CI runs the pipeline on every `.zsdl` PR diff
- [ ] `make test` passes including synthesis unit tests
