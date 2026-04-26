# Reference

Complete reference for ZSDL syntax, all invariant kinds, harness CLI flags,
and Makefile variables.

---

## ZSDL File Structure

A ZSDL file has three parts in order:

```
[HEADER]              spec identity + provenance + library (required)
[DOC SECTIONS]        constants, functions, wire_formats, error_model (optional)
[INVARIANT SECTIONS]  invariant blocks and tables (at least one required)
```

---

## Header Fields

### Required

```yaml
spec: canonical_name          # matches spec file stem (e.g. "hashlib" → hashlib.zspec.zsdl)
version: ">=3.6"              # spec_for_versions: semver range
backend: python_module(name)  # library section (see Backend Syntax below)
```

### Optional

```yaml
docs: https://...             # public_docs_url
api_header: zstd.h            # C header (for ctypes specs; default "N/A")
rfcs:
  - "RFC 1952 — GZIP file format specification"
  - "FIPS 180-4 — Secure Hash Standard"
```

### Provenance block (required)

```yaml
provenance:
  derived_from:
    - "Source title — URL"
    - "Verified with library X.Y.Z on platform, YYYY-MM-DD"
  not_derived_from:
    - "src/implementation.c"
    - "Any other implementation source files"
  notes: "Optional free-form notes."
```

---

## Backend Syntax

| Backend | ZSDL Syntax | Notes |
|---------|-------------|-------|
| Python module | `python_module(hashlib)` | Uses `importlib.import_module` |
| C shared library | `ctypes(zlib)` | Uses `ctypes.CDLL` via `find_library` |
| CLI subprocess | `cli(curl)` | Uses `shutil.which` + `subprocess.run` |
| Node.js CJS | `node(semver)` | Uses `require()` via `node -e` |
| Node.js ESM | `node(chalk)` + `esm: true` | Uses `await import()` via `node -e` |

---

## Invariant Forms

### Standalone invariant

```yaml
invariant unique.dotted.id:
  description: "Human-readable description"
  category: category_name
  kind: python_call_eq
  # ... kind-specific fields
```

### Inline `call:` shorthand (python_module only)

```yaml
invariant mylib.fn.basic:
  call: function_name("arg1", "arg2")
  eq: "expected"

invariant mylib.fn.error:
  call: function_name(None)
  raises: TypeError
```

### Table

```yaml
table dotted.table.id:
  kind: python_call_eq        # shared kind
  category: category_name     # shared category
  function: function_name     # shared function (can be overridden per row)
  id_prefix: prefix           # prepended to each row id; use ~ to use row id as-is

  columns: [id, args, expected]
  rows:
    - [row_id_1, ["arg1"], "result1"]
    - [row_id_2, ["arg2"], "result2"]
```

Tables generate one invariant per row with id `<id_prefix>.<row_id>` (or just
`<row_id>` when `id_prefix: ~`).

**Adding per-row `skip_if`:** Append a dict as the last element of a row:

```yaml
rows:
  - [row_id, ["arg"], "result", {skip_if: 'platform == "freebsd"'}]
```

---

## Invariant Kinds — python_module

### `python_call_eq`

Call a function and compare the return value.

```yaml
kind: python_call_eq
function: function_name          # required; dotted path ok: "date.fromisoformat"
args: ["arg1", 42, null]         # positional arguments; null → Python None
kwargs: {key: value}             # keyword arguments (optional)
expected: "expected_value"       # compared with ==
# Optional chaining:
method: method_name              # access/call this on the return value
method_args: ["arg"]             # args for method (omit for zero-arg)
method_chain: attr_name          # zero-arg access/call on result of method
```

**Typed arg syntax:**
```yaml
args:
  - {type: str,   value: "hello"}
  - {type: int,   value: 42}
  - {type: bytes_b64, value: "aGVsbG8="}
  - {type: float, value: 3.14}
```

### `python_call_raises`

```yaml
kind: python_call_raises
function: function_name
args: [bad_input]
expected_exception: ValueError   # or TypeError, KeyError, etc.
```

### `python_encode_decode_roundtrip`

```yaml
kind: python_encode_decode_roundtrip
encode_function: b64encode
decode_function: b64decode
input: {type: bytes_b64, value: "aGVsbG8="}
```

### `python_struct_roundtrip`

```yaml
kind: python_struct_roundtrip
format: ">HI"
values: [1, 2]
```

### `python_sqlite_roundtrip`

```yaml
kind: python_sqlite_roundtrip
setup_sql: "CREATE TABLE t (x INTEGER); INSERT INTO t VALUES (42);"
query_sql: "SELECT x FROM t;"
expected_rows: [[42]]
```

### `python_set_contains`

```yaml
kind: python_set_contains
set_attr: algorithms_guaranteed   # module-level attribute name
value: "sha256"
```

---

## Invariant Kinds — ctypes

### `call_eq`

```yaml
kind: call_eq
function: crc32
args: [0, "aGVsbG8=", 5]
arg_types: [int, bytes_b64, int]   # required
expected: 907060870
```

### `call_ge`

```yaml
kind: call_ge
function: compressBound
args: [1024]
arg_types: [int]
lower_bound: 1024
```

### `call_returns`

```yaml
kind: call_returns
function: RAND_bytes
```

### `constant_eq`

Requires a `constants:` section in the spec:

```yaml
constants:
  return_codes:
    Z_OK: {value: 0, description: "Success"}

invariant zlib.const.Z_OK:
  kind: constant_eq
  name: Z_OK
  expected_value: 0
```

### `roundtrip`

```yaml
kind: roundtrip
data_b64: "SGVsbG8gV29ybGQ="     # base64-encoded input
```

### `wire_bytes`

```yaml
kind: wire_bytes
produce_via: compress2
produce_args:
  data_b64: "SGVsbG8gV29ybGQ="
  level: 6
assertions:
  - description: "First two bytes are zlib header"
    offset: 0
    length: 2
    python_check: "(data[0] * 256 + data[1]) % 31 == 0"
```

### `version_prefix`

```yaml
kind: version_prefix
expected_prefix: "1.2"
```

### `hash_known_vector`

```yaml
kind: hash_known_vector
algorithm: sha256
data_b64: ""
expected_hex: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
rfc: "FIPS 180-4"
```

---

## Invariant Kinds — cli / node

### `cli_exits_with`

```yaml
kind: cli_exits_with
args: ["--version"]
expected_exit_code: 0
```

### `cli_stdout_contains`

```yaml
kind: cli_stdout_contains
args: ["--version"]
expected_substring: "curl"
```

### `cli_stdout_eq`

```yaml
kind: cli_stdout_eq
args: ["--version"]
expected_output: "1.2.3\n"
```

### `cli_stdout_matches`

```yaml
kind: cli_stdout_matches
args: ["--version"]
expected_regex: 'curl \d+\.\d+'
```

### `node_module_call_eq`

```yaml
kind: node_module_call_eq
function: valid
args: ["1.2.3"]
expected: "1.2.3"
```

### `node_constructor_call_eq`

```yaml
kind: node_constructor_call_eq
class: Ajv
ctor_args: []
method: validate
args: [{"type": "string"}, "hello"]
expected: true
# then_call: true     # optionally invoke method's return as a function
# then_args: [...]    # args for the chained invocation
```

### `node_factory_call_eq`

Two-step factory + method (e.g. `express()`, `yargs(argv).parseSync()`).

```yaml
kind: node_factory_call_eq
factory: ~                        # null = call module itself; or name a property
factory_args: [["--foo", "bar"]]
method: parseSync
method_args: []
expected: {_: [], foo: "bar", "$0": ""}
```

### `node_chain_eq`

Arbitrary `{method|get|call}` chain off an initial value. Use this for fluent
builder APIs that need 3+ chained calls — e.g. commander's
`new Command().option(f).parse(argv).opts()`.

`entry` is one of:

| Entry | Initial value |
|-------|---------------|
| `module` | `m(...entry_args)` |
| `named` | `m[function](...entry_args)` |
| `constructor` | `new m[class](...entry_args)` (default `class: "default"`) |
| `factory` | `m[factory](...entry_args)` |

`class`/`factory`/`function` accept **dotted paths** (e.g. `default.Separator`)
for ESM packages whose default export bundle nests classes.

Each chain step is one of `{method, args}`, `{get}`, or `{call}`:

```yaml
kind: node_chain_eq
entry: constructor
class: Command
entry_args: []
chain:
  - {method: option, args: ["--foo <val>"]}
  - {method: parse,  args: [["--foo", "bar"], {from: "user"}]}
  - {method: opts,   args: []}
expected: {foo: "bar"}
```

### `node_property_eq`

Sugar for `node_chain_eq` with a single `{get}` step — "construct/call, then read
one property". Used for ora, inquirer's `Separator`, meow's `cli.flags`.

```yaml
kind: node_property_eq
entry: named
function: default
entry_args: ["Loading..."]
property: text
expected: "Loading..."
```

### `node_sandbox_chain_eq`

Same chain semantics as `node_chain_eq`, but the script runs inside a fresh
per-invariant tempdir whose contents are seeded by `setup`. The harness
require/imports the module while cwd is the project root (so node_modules
resolves), then `process.chdir()`s into the sandbox before running the chain.
The sandbox is removed after the run.

`setup` entries: `{path: "rel", content: "string"}` (text file),
`{path: "rel", content_b64: "..."}` (binary file via base64), or
`{path: "rel", dir: true}` (directory). Paths must be relative and free of `..`.

Used for filesystem packages: `glob`, `fs-extra`, `mkdirp`, `rimraf`, `find-up`.

```yaml
kind: node_sandbox_chain_eq
entry: named
function: globSync
entry_args: ["**/*.txt"]
chain:
  - {method: sort, args: []}
setup:
  - {path: "a.txt", content: ""}
  - {path: "sub/b.txt", content: ""}
expected: ["a.txt", "sub/b.txt"]
```

### `ctypes_chain_eq`

Threads opaque handles through a sequence of ctypes calls. Required for
stateful C library APIs whose return value from one call is the input to the
next (libpcap's `pcap_open_offline → pcap_datalink → pcap_close`, sqlite3's
`prepare/step/finalize`, OpenSSL's BIO chains).

Each chain step has `function`, `args`, `arg_types`, `restype` (one of
`c_int` / `c_uint` / `c_long` / `c_ulong` / `c_char_p` / `c_void_p` — default
`c_int`). Optional per-step `capture: name` stores the result; subsequent
steps reference it via `{capture: name}` arg dicts. `{errbuf: N}` allocates a
caller-owned scratch buffer. Plain string args auto-encode to bytes when the
slot is `c_char_p`.

Comparison modes: `expected` (int), `expected_b64` (bytes equality),
`expected_prefix_b64` (bytes startswith). Mark which step's return is compared
via `compare: true` (default: last step).

```yaml
kind: ctypes_chain_eq
chain:
  - function: pcap_lib_version
    restype: c_char_p
    args: []
    arg_types: []
expected_prefix_b64: bGlicGNhcCB2ZXJzaW9u   # b'libpcap version'
```

### `ctypes_sandbox_chain_eq`

Same mechanics as `ctypes_chain_eq` plus a `setup` list that seeds a
per-invariant tempdir with file blobs. Chain references files via
`{sandbox_path: rel}`, which resolves to absolute path bytes (utf-8 encoded).
Setup paths must be relative and free of `..`.

Used for libpcap and pcapng to read synthesized savefile/section headers
without touching real network interfaces.

```yaml
kind: ctypes_sandbox_chain_eq
setup:
  - path: "trace.pcap"
    content_b64: "1MOyoQIABAAAAAAAAAAAAP//AAABAAAA"   # 24-byte pcap header
chain:
  - function: pcap_open_offline
    restype: c_void_p
    args: [{sandbox_path: "trace.pcap"}, {errbuf: 256}]
    arg_types: [c_char_p, c_char_p]
    capture: handle
  - function: pcap_datalink
    restype: c_int
    args: [{capture: handle}]
    arg_types: [c_void_p]
    compare: true
  - function: pcap_close
    restype: c_int
    args: [{capture: handle}]
    arg_types: [c_void_p]
expected: 1   # DLT_EN10MB
```

---

## `skip_if` Reference

| Expression | Effect |
|------------|--------|
| `'platform == "freebsd"'` | Skip on FreeBSD |
| `'platform != "linux"'` | Skip on non-Linux |
| `'semver_satisfies(lib_version, "<1.3")'` | Skip if version < 1.3 |
| `'not semver_satisfies(lib_version, ">=3.9")'` | Skip if version < 3.9 |
| `'platform == "freebsd" or not semver_satisfies(lib_version, ">=3.9")'` | Combined |

`semver_satisfies` uses `packaging.specifiers` if available; falls back to a simple
`>=X.Y` prefix check. A malformed version string returns `False` (invariant runs).

---

## `verify_behavior.py` CLI

```
python3 tools/verify_behavior.py SPEC [options]

Arguments:
  SPEC                  Path to compiled spec (*.zspec.json)

Options:
  --filter SUBSTR       Run only invariants whose id contains SUBSTR
  --verbose             Print each invariant result (not just summary)
  --list                List invariant ids and exit (no execution)
  --json-out FILE       Write JSON results to FILE
  --baseline FILE       Diff current results against FILE; exit non-zero on regression
  --watch               Poll spec file; rerun on every save (Ctrl-C to exit)

Exit codes:
  0  All passed (or skipped)
  1  One or more failed
  2  Harness error
```

---

## `verify_all_specs.py` CLI

```
python3 tools/verify_all_specs.py [SPEC ...] [--out FILE]

Arguments:
  SPEC ...     Paths to compiled specs (default: all _build/zspecs/*.zspec.json)
  --out FILE   Write JSON results to FILE (default: stdout)
```

---

## Makefile Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SNAPSHOT` | `./snapshots/YYYY-MM-DD` | Snapshot directory |
| `REPORT_OUT` | `./reports/overlap` | Overlap report output dir |
| `CANDIDATES_OUT` | `./reports/top-candidates.json` | Candidate ranking output |
| `EXTRACT_OUT` | `./reports/extractions` | Phase Z extraction output dir |
| `EXTRACT_TOP` | `50` | How many top candidates to extract |
| `NIXPKGS_ROOT` | `~/.nix-defexpr/channels/nixpkgs` | Nixpkgs root for filldeps |
| `FILL_TIMEOUT` | `60` | Per-package dep eval timeout (seconds) |
| `RANK_OUT` | `./reports/ranked-by-deps.json` | Ranking output file |
| `RANK_TOP` | `500` | How many ranked entries to emit |
| `RANK_MIN_REFS` | `2` | Minimum reverse-dep count to include |
| `BULK_TOP` | `100` | Packages to process in bulk-build |
| `BULK_JOBS` | `2` | Parallel build threads |
| `ZSPEC` | `_build/zspecs/zlib.zspec.json` | Spec for `make verify-behavior` |
| `ZSDL` | (all) | ZSDL file for `make compile-zsdl` |
| `FILTER` | (none) | Invariant id filter for `make verify-behavior` |
| `VERBOSE` | (none) | Set to any value for verbose output |
| `BUMP` | `patch` | Version bump type for `make release` |
| `SYNC_TARGETS` | `freebsd.local ubuntu.local` | rsync targets for `make sync` |

---

## JSON Schema Versions

| `schema_version` | Notes |
|------------------|-------|
| `"0.1"` | Original schema (accepted for compatibility) |
| `"0.2"` | Current: adds `esm: bool`, `arg_types: string[]`, length validation |

All new specs compiled by `make compile-zsdl` emit `schema_version: "0.2"`.
