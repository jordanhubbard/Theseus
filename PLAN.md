# Theseus — Next Steps

Current state (2026-04-01): 12 Z-layer specs, 216 invariants, 907 tests passing.
Backends: ctypes, python_module, cli (node included). Schema validation, cross-spec
interoperability, behavioral_spec wired into recipe records and extraction, CI on
linux+macos, --baseline/--diff mode, make verify-all-specs all in place.

---

## 1. More Z-Specs: Fill Out the Candidate Library

The extraction pipeline now auto-injects `behavioral_spec` for any library that has a
matching spec. High-value additions:

| Library       | Backend       | Notes                                              |
|---------------|---------------|----------------------------------------------------|
| `zstd`        | ctypes        | Compression library; cross-spec invariant vs zlib  |
| `libssl`      | ctypes        | Low-level TLS; cross-spec vs openssl CLI spec      |
| `pathlib`     | python_module | stdlib Path API; pure functions, easy              |
| `datetime`    | python_module | stdlib; parsing, formatting, arithmetic            |
| `hashlib` ext | python_module | Already done; add sha3_256, blake2b vectors        |
| `chalk`       | cli (node)    | ANSI stripping when NO_COLOR is set                |
| `ajv`         | cli (node)    | Requires new `node_constructor_call_eq` kind for `new Ajv()` |

---

## 2. `node_constructor_call_eq` Kind

Some npm packages export a class rather than plain functions (Ajv, Winston, etc.).
The current `node_module_call_eq` handler calls `m[fn](...args)` which doesn't work
for constructor-based APIs.

- Add a `node_constructor_call_eq` kind that calls `new m.ClassName(ctorArgs)` to
  create an instance, then calls `instance[method](...args)` and compares the result.
- Register in KNOWN_KINDS, PatternRegistry, schema enum, validator.
- Write `zspecs/ajv.zspec.json` using it: compile a schema, validate passing and
  failing objects.

---

## 3. Snapshot-Level Z-Spec Coverage Report

`extract_candidates.py` auto-injects `behavioral_spec` for known libraries. But there
is no visibility into which fraction of the top-N candidates have a spec.

- Add a `--coverage-report` flag to `extract_candidates.py` (or a new
  `tools/spec_coverage.py`) that scans the extraction output and prints:
  - Total candidates extracted
  - Candidates with a behavioral_spec (covered)
  - Candidates without (gap list, sorted by score)
- Add a `make spec-coverage` Makefile target.

---

## 4. `verify_behavior` Watch Mode

For development of new specs, re-running the harness manually after each edit is
friction. Add a `--watch` flag that uses `watchfiles` (or stdlib polling) to re-run
the spec on every save.

- Add `--watch` to `verify_behavior.py` argument parser.
- On each file-change event, clear the terminal and re-run the spec.
- Useful for TDD-style spec authoring: edit → save → see results instantly.

---

## 5. FreeBSD CI Job

The GitHub Actions workflow now covers ubuntu-latest and macos-latest. FreeBSD
behavioral divergences (LibreSSL vs OpenSSL, different libc errno values) are only
caught locally via the self-hosted worker.

- Add a GitHub Actions job using `cross-platform-actions/action@v0.25.0` (free,
  runs FreeBSD in a VM) to run `make test` on FreeBSD 14.
- On failure, compare JSON output against the macOS baseline and report divergences
  with the --baseline flag.
- Document any platform-specific `skip_if` conditions needed in the specs.

---

## 6. Spec Versioning and `spec_for_versions` Enforcement

Every spec has a `spec_for_versions` range (e.g. `">=1.3.0"`) but the harness never
checks it against the actual installed library version.

- In `LibraryLoader`, after loading the library, call the `version_function` (if set)
  to get the installed version string.
- If the version does not satisfy `spec_for_versions`, emit a warning and optionally
  exit with a dedicated exit code.
- Add `skip_if` support for version-gated invariants: if an invariant's `skip_if`
  expression evaluates to True given `lib_version`, skip it with a clear message.

`skip_if` support is already present in `InvariantRunner` but the version string is
hardcoded to `""` — just wire in the real version.

---

## 7. Export `verify-all-specs` Results to JSON

`make verify-all-specs` prints a text summary but throws away the per-spec results.
Useful for CI dashboards and regression tracking.

- Add a `tools/verify_all_specs.py` script that runs all specs in `zspecs/` and
  writes a single JSON file with per-spec results, per-invariant pass/fail, and an
  aggregate summary.
- Add `make verify-all-specs-json OUT=<file>` Makefile target.
- This output can feed the `--baseline` mode for cross-version comparisons.

---

## Order of Attack

1. **node_constructor_call_eq** (step 2) + **ajv spec** — extends the Node backend.
2. **More stdlib specs** (datetime, pathlib) from step 1 — low effort, high coverage.
3. **spec_for_versions enforcement** (step 6) — closes a correctness gap.
4. **spec_coverage report** (step 3) — visibility into the gap list.
5. **verify-all-specs JSON export** (step 7) — feeds the CI dashboard story.
6. **FreeBSD CI** (step 5) and **watch mode** (step 4) — polish.
