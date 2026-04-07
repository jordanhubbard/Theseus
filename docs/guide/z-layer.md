# Z-Layer Behavioral Spec System

The Z-layer (Layer 2) is a system of 70 machine-readable behavioral specs — one per
OSS library — that describe how each library actually behaves. Each spec is:

- **Derived from public documentation only** — not from source code. This preserves
  clean-room provenance.
- **Versioned** against the library (`spec_for_versions` semver range).
- **Verifiable**: the harness runs every invariant against the real installed library
  and reports pass/fail/skip.
- **Cross-platform**: verified on macOS, Linux, and FreeBSD in CI.

---

## How It Works

```
zspecs/*.zspec.zsdl                  ← ZSDL spec sources (committed to git)
        │
        ▼  make compile-zsdl
_build/zspecs/*.zspec.json           ← compiled JSON (build artifact, not committed)
        │
        ├─► tools/verify_behavior.py     ← run invariants against installed library
        ├─► tools/verify_all_specs.py    ← batch runner; JSON results output
        ├─► tools/validate_zspec.py      ← static schema validation
        └─► make verify-all-specs        ← aggregate text report
```

ZSDL is a YAML authoring format that compiles losslessly to the JSON format read by
the harness. Always edit the `.zsdl` source — never the compiled JSON.

---

## Backends

The harness supports five backends:

| Backend | ZSDL header syntax | How the library is loaded |
|---------|-------------------|--------------------------|
| `ctypes` | `ctypes(zlib)` | `ctypes.CDLL` via `ctypes.util.find_library` |
| `python_module` | `python_module(hashlib)` | `importlib.import_module(module_name)` |
| `cli` | `cli(curl)` | `shutil.which(command)` + `subprocess.run` |
| `node/CJS` | `node(semver)` | `node -e "require('semver')..."` |
| `node/ESM` | `node(chalk)` + `esm: true` | `node -e "await import('chalk')..."` |

**Decision rule:** if `python3 -c "import X"` works, use `python_module`. If there
is only a binary and man page, use `cli`. If it ships as a `.so` with a C header,
use `ctypes`. npm packages always use `node`.

---

## Covered Libraries (70)

| Category | Libraries |
|----------|-----------|
| Compression | zlib, zstd, lz4 |
| Cryptography | hashlib, libcrypto, openssl |
| Serialization | base64, json, msgpack, struct, pyyaml, tomli, tomlkit, defusedxml, protobuf |
| Networking | urllib_parse, urllib3, curl, dns |
| Numeric / scientific | numpy |
| Data structures | attrs, more_itertools, networkx |
| Text processing | re, difflib, markdown, docutils, pygments, markupsafe, chardet |
| Parsing | pyparsing |
| Date/time | datetime, pytz, tzdata, isodate |
| Filesystem | pathlib, pathspec, fsspec, filelock |
| Database | sqlite3 |
| System | psutil, platformdirs, distro |
| Internationalization | idna |
| Python ecosystem | packaging, setuptools, typing_extensions, six, decorator, wrapt, pluggy, certifi, dotenv, colorama, traitlets, stevedore |
| Pattern matching | pcre2 |
| Image processing | pillow |
| XML/HTML | lxml |
| Node/npm | ajv, chalk, express, lodash, minimist, prettier, semver, uuid |
| Interfaces | zope_interface, fontTools |
| Async | tornado |

---

## Invariant Kinds

### python_module backend

| Kind | What it tests |
|------|--------------|
| `python_call_eq` | Call a function; compare return value. Supports `method`/`method_args`/`method_chain` for chained access. |
| `python_call_raises` | Call a function; verify it raises a named exception. |
| `python_encode_decode_roundtrip` | Encode then decode; verify round-trip equality. |
| `python_struct_roundtrip` | `struct.pack` then `unpack`; verify equality. |
| `python_sqlite_roundtrip` | Create in-memory SQLite DB; run setup SQL; verify rows. |
| `python_set_contains` | Verify a value is a member of a module-level set/frozenset. |

### ctypes backend

| Kind | What it tests |
|------|--------------|
| `call_eq` | Call a C function via ctypes; compare exact return value. |
| `call_ge` | Call a C function; verify return is `>=` a bound. |
| `call_returns` | Call a C function; verify return is non-null/non-zero. |
| `constant_eq` | Verify a named constant equals expected. |
| `roundtrip` | Compress+decompress or encode+decode in C; verify equality. |
| `wire_bytes` | Verify exact bytes at specific offsets in output. |
| `version_prefix` | Verify version string starts with a prefix. |
| `incremental_eq_oneshot` | Verify incremental API produces same output as one-shot. |
| `error_on_bad_input` | Verify C function returns error code on invalid input. |
| `hash_known_vector` | Hash a fixed input; compare to known digest. |
| `hash_incremental` | Verify incremental hash equals one-shot hash. |
| `hash_object_attr` | Verify a hash object attribute (e.g. `digest_size`). |
| `hash_digest_consistency` | Hash same input twice; verify results are identical. |
| `hash_copy_independence` | Verify copy of hash state is independent after mutation. |
| `hash_api_equivalence` | Verify two API paths produce the same digest. |
| `lz4_roundtrip` | LZ4 compress+decompress roundtrip. |
| `pcre2_match` | PCRE2 compile+match via ctypes. |

### cli / node backends

| Kind | What it tests |
|------|--------------|
| `cli_exits_with` | Verify process exit code. |
| `cli_stdout_eq` | Verify stdout equals a string exactly. |
| `cli_stdout_contains` | Verify stdout contains a substring. |
| `cli_stdout_matches` | Verify stdout matches a regex. |
| `cli_stderr_contains` | Verify stderr contains a substring. |
| `node_module_call_eq` | `require(mod)[fn](...args)` — compare result. |
| `node_constructor_call_eq` | `new mod.Class(ctorArgs).method(args)` — compare result. |
| `node_factory_call_eq` | Factory function call pattern for npm packages. |

---

## Method Chaining in `python_call_eq`

`python_call_eq` supports chaining via three optional fields:

| Field | Type | Meaning |
|-------|------|---------|
| `method` | string | Attribute or method to access/call on the function's return value |
| `method_args` | array | Arguments passed when calling `method` |
| `method_chain` | string | Second attribute or **zero-arg** method called on the result of `method` |

**Example** — `date.fromisoformat("2024-03-15").strftime("%Y/%m/%d")`:
```yaml
invariant datetime.date.strftime_slash:
  call: date.fromisoformat("2024-03-15").strftime("%Y/%m/%d")
  eq: "2024/03/15"
```

**Important:** `method_chain` calls the chained attribute as a **zero-argument method**.
Do not use it with `__contains__`, `__bool__`, or any dunder that requires arguments —
these will fail or return unexpected results. Use `method: __contains__` +
`method_args: [value]` instead.

---

## Version Detection and `spec_for_versions`

The harness automatically detects the installed library version:

- **python_module**: `importlib.metadata.version(module_name)`, falling back to `sys.version_info` for stdlib.
- **node**: `node -e "process.stdout.write(require('<mod>/package.json').version)"`.
- **ctypes**: calls `lib.<version_function>()` if `version_function` is set in the spec.

The detected version is checked against `identity.spec_for_versions` (a semver range).
Mismatches produce a `WARNING`. The version is also available as `lib_version` in
`skip_if` expressions.

---

## `skip_if` Expression Language

Any invariant can have an optional `skip_if` field — a Python expression that, if
truthy, marks the invariant as skipped rather than run.

| Name | Type | Example |
|------|------|---------|
| `lib_version` | `str` | `"1.2.12"` |
| `platform` | `str` | `"darwin"`, `"linux"`, `"freebsd"`, `"win32"` |
| `semver_satisfies(v, c)` | `bool` | `semver_satisfies(lib_version, ">=3.9")` |

Examples:
```yaml
skip_if: 'semver_satisfies(lib_version, "<1.3")'
skip_if: 'platform == "freebsd"'
skip_if: 'platform == "freebsd" or not semver_satisfies(lib_version, ">=3.9")'
```

---

## Running Specs

```bash
# Compile all ZSDL sources first
make compile-zsdl

# Run all 70 specs — text summary
make verify-all-specs

# Run all specs — JSON results (for CI dashboards, --baseline diffs)
make verify-all-specs-json OUT=results.json

# Run a single spec
make verify-behavior ZSPEC=_build/zspecs/hashlib.zspec.json

# Filter to one category
make verify-behavior ZSPEC=_build/zspecs/hashlib.zspec.json FILTER=sha256

# Verbose output (print each invariant)
make verify-behavior ZSPEC=_build/zspecs/hashlib.zspec.json VERBOSE=1

# TDD watch mode (rerun on every save)
python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json --watch

# Baseline/regression diff
python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json \
  --json-out current.json
python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json \
  --baseline previous.json
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All invariants passed (or skipped) |
| 1 | One or more invariants failed |
| 2 | Harness error (spec could not be loaded, library not found) |

---

## Coverage Reporting

After running phase Z extraction:

```bash
# Which top-50 candidates have a spec?
make spec-coverage EXTRACTION_DIR=reports/extractions/ TOP=50

# Which specs have no extraction record? (reverse coverage)
make orphan-specs EXTRACTION_DIR=reports/extractions/

# Per-spec invariant description coverage
make spec-vector-coverage
```

---

## CI Integration

The GitHub Actions workflow runs `make verify-all-specs-json` on ubuntu/Python-3.12
and uploads `verify-all-specs-results.json` as an artifact. Use this file with
`--baseline` to detect regressions between runs.

The JSON results file has this structure:
```json
{
  "generated_at": "2026-04-06T00:00:00Z",
  "summary": {
    "total_specs": 70,
    "specs_ok": 70,
    "specs_failed": 0,
    "total_invariants": 1118,
    "passed": 1118,
    "failed": 0,
    "skipped": 0
  },
  "specs": [
    {
      "spec": "_build/zspecs/zlib.zspec.json",
      "canonical_name": "zlib",
      "lib_version": "1.2.12",
      "error": null,
      "summary": {"total": 23, "passed": 23, "failed": 0, "skipped": 0},
      "invariants": [{"id": "zlib.compress.roundtrip", "passed": true, ...}]
    }
  ]
}
```
