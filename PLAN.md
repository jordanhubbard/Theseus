# Theseus — Next Steps

Current state: The Z-layer behavioral spec system (`zspecs/`, `tools/verify_behavior.py`) is working
across three backends (ctypes, python_module, cli) with 7 specs and 744 tests passing. The core
Theseus pipeline (bootstrap → overlap → rank → extract) is also working. The two systems have not
yet been connected.

---

## 1. Connect Z-specs to Package Recipes

The behavioral spec system was built in isolation. The payoff comes when a `package-recipe.schema.json`
record can reference the Z-spec that governs it.

- Add an optional `"behavioral_spec"` field to `schema/package-recipe.schema.json` pointing to a
  relative path like `"zspecs/openssl.zspec.json"`.
- Update `tools/validate_record.py` to, when `behavioral_spec` is present, load the spec and run
  `verify_behavior.py` against it as part of validation.
- Update `examples/` records for `openssl`, `zlib`, and `curl` (once a curl spec exists) to
  reference their specs.

**Why now:** The Z-spec system has proven it scales. Wiring it into record validation closes the
loop: a canonical record is only trustworthy if the library it describes passes its own behavioral
invariants on the current machine.

---

## 2. Write Z-Specs for the Remaining Candidate Libraries

The top extraction candidates (curl, zlib, openssl) are already in `examples/`. Only zlib and
openssl have Z-specs. Priority order:

| Library     | Backend       | Key invariants to cover                              |
|-------------|---------------|------------------------------------------------------|
| `curl`      | cli           | `--version` exits 0, HTTP GET returns 200, TLS works |
| `sqlite3`   | python_module | `connect()`, `execute()`, round-trip insert/select   |
| `libz`/zlib | ctypes        | already done — extend with `uncompress` roundtrip    |
| `re` (stdlib)| python_module | `match`, `search`, `sub`, `compile` + flags          |

**Why:** Having Z-specs for the top-N candidates means `extract_candidates.py` can emit records that
carry verified behavioral contracts, not just metadata.

---

## 3. Schema Validation of `.zspec.json` Files

`zspecs/schema/behavioral-spec.schema.json` exists but is not enforced anywhere.

- Add a `tools/validate_zspec.py` script that validates all `zspecs/*.zspec.json` files against
  the schema using stdlib `json` + a minimal JSON Schema validator, or `jsonschema` if it is
  available.
- Add `make validate-zspecs` target to the Makefile.
- Run `validate_zspec.py` as part of `make test`.

**Why:** Currently the spec files are only validated structurally by `SpecLoader` at runtime. Static
schema validation catches typos and missing fields before the harness ever runs.

---

## 4. Multi-Platform CI Verification

The `verify_behavior.py` harness exists to catch platform divergence. It only has value if it runs
on all three platforms (macOS, Linux, FreeBSD).

- Add a CI job (GitHub Actions) that runs `make test` on ubuntu-latest.
- Add a CI job that SSHes to `freebsd.local` and runs `make test` there (or use the existing
  FreeBSD worker setup documented in memory).
- Flag any invariant that passes on one platform but not another as a **known divergence** — add a
  `platform_notes` field to the invariant in the spec.

**Why:** The whole point of the Z-layer is cross-platform behavioral contracts. A spec that only
runs on macOS isn't verifying much.

---

## 5. Slave Port Support in the FreeBSD Importer

Documented in `docs/architecture.md` as a known limitation. Slave ports are silently skipped,
which means variants like `openssl-legacy` are invisible to the ranker and extractor.

- In `theseus/importer.py`, detect `MASTERDIR =` in the Makefile.
- Follow the path, load the master Makefile, merge slave-specific variables on top.
- Emit a record with `provenance.notes` indicating it is a slave port.

**Why:** Several high-value packages (openssl variants, python versions) use this pattern. Skipping
them skews the overlap report and ranking.

---

## 6. `node_module_call_eq` — Expand to More npm Packages

The Node.js backend works. Natural next specs:

| Package   | Key invariants                                      |
|-----------|-----------------------------------------------------|
| `uuid`    | `v4()` returns a valid UUID, `validate()` works     |
| `ajv`     | Schema validation passes/fails as expected          |
| `chalk`   | Color output strips ANSI when `NO_COLOR` is set     |
| `minimist`| Argument parsing (flags, values, `--` separator)    |

These are useful for two reasons: (1) they stress-test the `node_module_call_eq` kind with more
complex return types, and (2) they generate Z-specs for the npm packages that Theseus will
eventually normalize across registries.

---

## 7. `verify_behavior --diff` Mode

When a spec is re-run after a library upgrade, it would be useful to see which invariants changed
status (pass→fail or fail→pass) rather than just the current pass/fail count.

- Add a `--baseline` flag to `verify_behavior.py` that reads a previous `--json-out` file.
- Print a diff: invariants that flipped from pass to fail (regressions), fail to pass (fixes), and
  newly added or removed invariants.

**Why:** This makes the harness useful for tracking upgrade safety — the same use case as the
`diff_snapshots.py` tool but for behavioral contracts rather than metadata.

---

## Order of Attack

1. **Schema validation** (step 3) — quick, high-value, unblocks everything else.
2. **Connect specs to recipes** (step 1) — closes the loop between the two systems.
3. **curl Z-spec** (step 2) — the most visible missing spec given `curl` is in examples/.
4. **Slave port support** (step 5) — improves data quality for the ranker.
5. **Multi-platform CI** (step 4) — validates the cross-platform story.
6. **diff mode** (step 7) and **more npm specs** (step 6) — once the core is solid.
