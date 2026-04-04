# Writing Behavioral Specs (ZSDL)

This guide is for developers writing their first Z-layer spec. It covers practical
decisions, common patterns, and mistakes to avoid. For the full language reference,
see `docs/zsdl-design.md`.

---

## Workflow

```bash
# 1. Author the spec
$EDITOR zspecs/mylib.zspec.zsdl

# 2. Compile to JSON
make compile-zsdl ZSDL=zspecs/mylib.zspec.zsdl

# 3. Verify against the installed library
python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json

# 4. Iterate (auto-recompile + rerun on each save)
make compile-zsdl ZSDL=zspecs/mylib.zspec.zsdl && \
  python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json --watch
```

Compiled JSON files go in `_build/` and are not committed to git. The `.zsdl`
source is the canonical artifact; commit that.

---

## 1. When to use each backend

| Backend | ZSDL syntax | Decision rule |
|---------|-------------|---------------|
| `ctypes` | `ctypes(z)` | The library is a C shared library (`.so`/`.dylib`). You call C functions directly. |
| `python_module` | `python_module(hashlib)` | The library is importable Python — stdlib or a pip package. |
| `cli` | `cli(curl)` | The library exposes a command-line interface and you test it via subprocess. |
| `node` | `node(semver)` | The library is an npm package. Thin wrapper over `cli` that loads Node.js. |

When in doubt: if `python3 -c "import X"` works, use `python_module`. If there is only
a binary and a man page, use `cli`. If it ships as a `.so` with a C header, use `ctypes`.
npm packages always use `node`.

---

## 2. Choosing invariant kinds

### For `python_module` specs

| Situation | Kind to use |
|-----------|-------------|
| Call a function, compare return value | `python_call_eq` |
| Call a function, verify it raises a specific exception | `python_call_raises` |
| encode(x) followed by decode → original x | `python_encode_decode_roundtrip` |
| struct.pack then unpack → original values | `python_struct_roundtrip` |
| Create an in-memory SQLite DB, verify rows | `python_sqlite_roundtrip` |
| Verify a value is in a module-level set/frozenset | `python_set_contains` |

Use `python_call_eq` for the vast majority of Python specs. Reach for the specialized
kinds only when the pattern genuinely fits (e.g., `python_sqlite_roundtrip` for sqlite3
row comparison, `python_set_contains` for `hashlib.algorithms_guaranteed`).

### For `ctypes` specs

| Situation | Kind to use |
|-----------|-------------|
| Call a C function, compare exact integer return | `call_eq` |
| Call a C function, verify return is non-null/non-zero | `call_returns` |
| Verify return value is >= some bound | `call_ge` |
| Compress then decompress, verify round-trip equality | `roundtrip` |
| Verify exact bytes at specific offsets in output | `wire_bytes` |
| Verify a named library constant equals a value | `constant_eq` |
| Verify version string starts with a prefix | `version_prefix` |
| Verify incremental API matches one-shot API | `incremental_eq_oneshot` |
| Verify C function returns error on invalid input | `error_on_bad_input` |
| Hash a fixed input and compare known digest | `hash_known_vector` |

Use `call_eq` for simple integer-returning functions. Use `call_returns` when you only
care that the function succeeds (returns `Z_OK`, non-NULL), not the exact value.
Use `call_ge` for bound functions like `compressBound` where the contract is a
lower bound, not an exact value.

### For `cli` and `node` specs

| Situation | Kind to use |
|-----------|-------------|
| Verify process exit code | `cli_exits_with` |
| Verify stdout equals a string | `cli_stdout_eq` |
| Verify stdout contains a substring | `cli_stdout_contains` |
| Verify stdout matches a regex | `cli_stdout_matches` |
| Verify stderr contains a substring | `cli_stderr_contains` |
| Call `require(mod).fn(args)`, compare result | `node_module_call_eq` |
| Call `new require(mod).Class(ctorArgs).method(args)` | `node_constructor_call_eq` |

For CLI specs, prefer `cli_stdout_contains` over `cli_stdout_eq` unless the exact
full output is contractually fixed. Exact output is brittle across versions.

---

## 3. Tables vs single invariants

### Use a table when

- You are calling the **same function** (or same kind) with **varying inputs** and comparing to
  varying expected outputs.
- The rows share the same `kind`, `category`, and most fields.
- You have three or more rows. Two rows can still benefit from a table, but one row
  is always a standalone `invariant`.

**Table example** — SHA-256 known vectors, all `hash_known_vector`, all varying only
in `data_b64`/`expected_hex`:

```yaml
table hashlib.sha256.known_vectors:
  kind: hash_known_vector
  category: known_vector
  algorithm: sha256
  id_prefix: sha256

  columns: [id, data_b64, expected_hex, rfc]
  rows:
    - [empty, "",     "e3b0c44...", "FIPS 180-4"]
    - [abc,   "YWJj", "ba7816b...", "FIPS 180-4"]
```

### Use a standalone `invariant` when

- The invariant has a unique setup that does not generalize.
- It uses a specialized kind (`wire_bytes`, `incremental_eq_oneshot`) with fields
  not shared by any other invariant in the spec.
- It is a one-off edge case (e.g., the empty-input behavior of a checksum).

**Standalone example** — the RFC 1950 wire format check is unique; no other invariant
in `zlib.zspec.zsdl` inspects raw bytes at specific offsets:

```yaml
invariant zlib.wire.rfc1950.header_check:
  description: "(CMF * 256 + FLG) % 31 == 0 — RFC 1950 §2.2 header checksum"
  category: wire_format
  kind: wire_bytes
  produce_via: compress2
  produce_args:
    data_b64: SGVsbG8gV29ybGQ=
    level: 6
  assertions:
    - description: "(CMF * 256 + FLG) % 31 == 0"
      offset: 0
      length: 2
      python_check: "(data[0] * 256 + data[1]) % 31 == 0"
```

### Table with varying function per row

When rows share a kind but call different functions, add `function` as a column:

```yaml
table semver.comparison:
  kind: node_module_call_eq
  category: comparison
  id_prefix: ~          # row id used as full suffix

  columns: [id, function, args, expected]
  rows:
    - [gt.true,  gt,      ["2.0.0", "1.9.9"], true ]
    - [lt.true,  lt,      ["1.0.0", "2.0.0"], true ]
    - [eq.true,  eq,      ["1.2.3", "1.2.3"], true ]
```

---

## 4. Python method chaining

`python_call_eq` supports chaining through `method`, `method_args`, and `method_chain`.
Use these to test patterns like `obj.method().attr` without needing a special kind.

| Pattern | Fields needed |
|---------|---------------|
| `fn().attr` | `method: attr` |
| `fn().method()` | `method: method` (zero-arg, harness calls it) |
| `fn().method(args)` | `method: method`, `method_args: [...]` |
| `fn().method(args).attr` | `method`, `method_args`, `method_chain: attr` |
| `fn().attr.__str__()` | `method: attr`, `method_chain: "__str__"` |

**Real example from `difflib.zspec.zsdl`** — testing `SequenceMatcher.find_longest_match()`:

The call `SequenceMatcher(None, "ABCDBDE", "BCDE").find_longest_match()` returns a
`Match` named tuple. Each attribute (`size`, `b`) is tested as a separate row, with
`args` fixed at the table level and `method_chain` varying per row:

```yaml
table difflib.sequence_matcher.find_longest:
  kind: python_call_eq
  category: matching
  id_prefix: sequence_matcher
  function: SequenceMatcher
  args: [null, "ABCDBDE", "BCDE"]
  method: find_longest_match

  columns: [id, method_chain, expected]
  rows:
    - [find_longest_match_size,    size, 3]
    - [find_longest_match_b_index, b,    0]
```

The `call:` expression shorthand in standalone invariants handles the same patterns
more readably when only one or two invariants need chaining:

```yaml
invariant difflib.sequence_matcher.ratio_identical:
  call: SequenceMatcher(None, "abcde", "abcde").ratio()
  eq: 1.0
```

The chain depth limit is two levels: `fn().method` and `fn().method.chain`.
Deeper chains must be broken into helper invariants or use the structured form.

---

## 5. `skip_if` for version-gated invariants

Some invariants only apply to specific library versions or platforms. Use `skip_if`
to gate them rather than removing them from the spec.

### Available variables

| Variable | Type | Example value |
|----------|------|---------------|
| `lib_version` | string | `"3.11.0"`, `"1.2.12"`, `"7.6.0"` |
| `platform` | string | `"darwin"`, `"linux"`, `"freebsd"` |

### Available helpers

| Helper | Example |
|--------|---------|
| `semver_satisfies(lib_version, range)` | `semver_satisfies(lib_version, ">=3.9")` |

### Version gating

```yaml
invariant hashlib.sha3_256.known_vector:
  description: "SHA3-256 of empty string — Python 3.6+ guaranteed algorithm"
  category: known_vector
  skip_if: "not semver_satisfies(lib_version, '>=3.6')"
  kind: hash_known_vector
  algorithm: sha3_256
  data_b64: ""
  expected_hex: "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"
```

### Platform gating

```yaml
invariant openssl.version.libressl_variant:
  description: "LibreSSL build reports 'LibreSSL' in version string (FreeBSD/macOS)"
  category: health
  skip_if: "platform not in ('darwin', 'freebsd')"
  kind: cli_stdout_contains
  args: [version]
  expected_substring: LibreSSL
```

### Combined conditions

```yaml
skip_if: "platform == 'freebsd' or not semver_satisfies(lib_version, '>=3.9')"
```

`skip_if` expressions are plain Python expressions evaluated by the harness. Keep
them simple. If the condition is true, the invariant is skipped (not failed).

Per-row `skip_if` can also be provided as a column in a table, or as a key in a
trailing per-row override dict:

```yaml
rows:
  - [sha3_256, "a7ffc6...", {skip_if: "not semver_satisfies(lib_version, '>=3.6')"}]
```

---

## 6. Test vector discipline

**All inputs must be fixed literals.** Never generate test data at runtime.

Bad:
```yaml
# Do not do this — non-reproducible
args: [str(datetime.now())]
```

Good:
```yaml
args: ["2024-03-15"]
```

**Why this matters:** Specs are verified on macOS, Linux, and FreeBSD across multiple
Python/Node versions. A spec that produces different inputs on each run cannot be used
as a baseline or regression tool. The entire value of the Z-layer depends on specs
being deterministic.

**The gold standard is RFC test vectors.** If the specification document (RFC, FIPS
publication, algorithm spec) includes known-answer test vectors, use them verbatim and
cite them in `rfc:`. These vectors are the strongest form of behavioral evidence because
they are cross-checkable against independent implementations.

```yaml
table hashlib.sha256.known_vectors:
  kind: hash_known_vector
  algorithm: sha256

  columns: [id, data_b64, expected_hex, rfc]
  rows:
    - [empty, "", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "FIPS 180-4"]
    - [abc,   "YWJj", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "FIPS 180-4 Appendix B"]
```

When no RFC vector exists, document in `provenance.notes` which tool or version you
used to verify the expected value (e.g., `"Verified with Python 3.14.3 + sha256sum on
macOS/Darwin 25.3.0, 2026-04-02"`).

---

## 7. Provenance section

The provenance block is not bureaucratic overhead — it is the clean-room boundary.
It documents what the spec author read, and what they explicitly did not read.

**`derived_from`** — list every source you consulted:
- RFC or standard document (include title and date)
- Public API documentation URL
- The specific version and platform you ran to verify expected values

**`not_derived_from`** — list implementation source files you did not read:
- Name the actual files if you know them (`Modules/_hashopenssl.c`)
- A general statement is acceptable if specific files are unknown (`"Any zlib C source"`)

The purpose: the implementation team reads specs, not sources. If a spec author
accidentally reads the implementation, the clean-room separation is broken. The
`not_derived_from` list is the spec author's attestation that they stayed on the
correct side of the boundary.

```yaml
provenance:
  derived_from:
    - "RFC 1952 — GZIP file format specification (May 1996)"
    - "https://zlib.net/manual.html — zlib API manual (public documentation)"
    - "Test vectors verified with zlib 1.2.12 on macOS/Darwin 25.3.0, 2026-04-01"
  not_derived_from:
    - "zlib/deflate.c"
    - "zlib/inflate.c"
    - "Any other zlib C implementation source file"
  notes: "This spec constitutes the clean-room boundary."
```

---

## 8. Common mistakes to avoid

### Wrong arg types in ctypes specs

C functions require explicit `arg_types`. A Python integer is not the same as a
`c_ulong`. Always set `arg_types` on every `call_eq` invariant:

```yaml
# Wrong — missing arg_types
invariant zlib.crc32.empty:
  kind: call_eq
  function: crc32
  args: [0, null, 0]
  expected: 0

# Correct
invariant zlib.crc32.empty:
  kind: call_eq
  function: crc32
  args: [0, null, 0]
  arg_types: [int, "null", int]
  expected: 0
```

### Using `!b64` in ctypes args

The `!b64` YAML tag produces a `bytes_b64` typed object, which works for
`python_module` specs. In ctypes specs, binary data in `args` must use the
`_b64` field-name suffix convention instead (`args_b64`, `src_b64`). Check the
ctypes-specific field names for your invariant kind in `docs/zsdl-design.md`.

```yaml
# Wrong — !b64 tag in ctypes call_eq args
invariant zlib.crc32.hello:
  kind: call_eq
  function: crc32
  args: [0, !b64 aGVsbG8=, 5]   # do not do this in ctypes specs
  arg_types: [int, bytes_b64, int]
  expected: 907060870

# Correct — plain base64 string, arg_types carries the encoding
invariant zlib.crc32.hello:
  kind: call_eq
  function: crc32
  args: [0, "aGVsbG8=", 5]
  arg_types: [int, bytes_b64, int]
  expected: 907060870
```

### Forgetting the `constants:` section for `constant_eq`

`constant_eq` looks up names from the spec's `constants:` section. If you write
a `constant_eq` table but omit the `constants:` block, the harness cannot resolve
the constant name and will error.

```yaml
# This will fail — no constants: block
table zlib.const:
  kind: constant_eq
  columns: [name, expected_value]
  rows:
    - [Z_OK, 0]

# Fix — add the constants: block
constants:
  return_codes:
    Z_OK: {value: 0, description: "Operation completed successfully"}

table zlib.const:
  kind: constant_eq
  id_from: name
  columns: [name, expected_value]
  rows:
    - [Z_OK, 0]
```

### YAML quoting: dict literals in `call:` expressions

When a `call:` expression contains a dict literal, YAML will try to parse the `{`
as a YAML flow mapping unless you quote the entire value:

```yaml
# Wrong — YAML parses the { as a flow mapping
call: dumps({"b": 2, "a": 1}, sort_keys=True)

# Correct — quote the whole call expression
call: 'dumps({"b": 2, "a": 1}, sort_keys=True)'
```

### YAML quoting: null/true/false as row IDs

In a table row, bare `null`, `true`, and `false` are YAML boolean/null literals,
not strings. If you need one of these words as a row ID, quote it:

```yaml
# Wrong — YAML parses null as null, not the string "null"
rows:
  - [null, ["not-a-version"], ~]

# Correct
rows:
  - ["null_input", ["not-a-version"], ~]
```

### Forgetting to quote reserved words in args

The same rule applies to function arguments in table rows. `true`, `false`, and
`null` are interpreted by YAML unless quoted. Use `~` for Python `None`, `true`/
`false` for booleans (these are fine as YAML values and map correctly), but be
careful when a string argument happens to be one of these words:

```yaml
# ~ (YAML null) correctly compiles to Python None — use this for isjunk=None
args: [null, "abc", "xyz"]   # null here is the first positional arg, becomes None ✓
```

### Writing specs that test implementation details

Specs describe public API contracts from documentation, not implementation behavior
observed by reading source code. If the only way to know an expected value is to
read the implementation, that value does not belong in a spec. Stick to values
documented in RFCs, official docs, or man pages.

---

## Quick-start template

Copy this skeleton and fill in the blanks:

```yaml
spec: mylib
version: ">=X.Y"
backend: python_module(mylib)      # or ctypes(name), cli(cmd), node(pkg)

docs: https://docs.example.com/mylib/

provenance:
  derived_from:
    - "mylib official documentation — https://docs.example.com/mylib/"
    - "Verified with mylib X.Y.Z on macOS/Darwin NN.N.N, YYYY-MM-DD"
  not_derived_from:
    - "mylib source: src/mylib.c"

error_model: python_exceptions     # omit or replace for ctypes/cli

table mylib.basic:
  kind: python_call_eq
  category: basic
  function: my_function
  id_prefix: my_function

  columns: [id, args, expected]
  rows:
    - [case1, ["input1"], "expected1"]
    - [case2, ["input2"], "expected2"]

invariant mylib.error.bad_input:
  call: my_function(None)
  raises: TypeError
```
