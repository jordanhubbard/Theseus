# ZSDL — Z-Spec Definition Language: Design Document

**Status:** Design (pre-implementation)
**Replaces:** hand-authored `*.zspec.json` files
**Compile target:** existing `*.zspec.json` schema (unchanged, lossless)

---

## 1. Overview

ZSDL is a YAML-based authoring language that compiles to the existing Z-spec JSON format.
It is not a new runtime format — the harness (`verify_behavior.py`) continues to read JSON.
ZSDL is purely a write-time concern.

### Goals

- Reduce a typical 300-line spec to ~75 lines with zero information lost
- Make the common case (`call fn(args) → expected`) one readable line
- Group repeated test vectors into tables instead of one JSON object per row
- Omit boilerplate sections (empty `wire_formats`, `types`, `constants`) silently
- Auto-generate `description` and `id` where they are mechanical
- Keep unusual / one-off invariants in full structured form — no forced abstraction

### Non-goals

- A new runtime or harness change
- Changing what invariant kinds mean
- Removing any expressible invariant from the current format

### File extension and layout

```
zspecs/hashlib.zspec.zsdl     ← authoring source
zspecs/hashlib.zspec.json     ← compiled output (what the harness reads)
```

One `.zsdl` file per spec, one-to-one with the JSON. The JSON files are generated
artifacts; source of truth is ZSDL once migration is complete. The compiler is
`tools/zsdl_compile.py`. The Makefile adds a `make compile-zsdl` target that
regenerates all JSON from all ZSDL files.

---

## 2. File Structure

A ZSDL file has three parts, in order:

```
[HEADER]            spec identity + provenance + library (required)
[DOC SECTIONS]      constants, functions, wire_formats, error_model (all optional)
[INVARIANT SECTIONS] invariant blocks and tables (at least one required)
```

---

## 3. Header

### Required fields

```yaml
spec: hashlib                               # canonical_name
version: ">=3.6"                            # spec_for_versions
backend: python_module(hashlib)             # library section (see §3.1)
```

### Optional fields

```yaml
docs: https://docs.python.org/3/library/hashlib.html   # public_docs_url
api_header: zstd.h                          # for C libraries; default "N/A — Python stdlib"
rfcs:                                       # rfc_references list
  - "FIPS 180-4 — Secure Hash Standard"
  - "RFC 1321 — The MD5 Message-Digest Algorithm"
```

### Provenance block

```yaml
provenance:
  derived_from:
    - "Python 3 hashlib documentation"
    - "FIPS 180-4 Appendix B test vectors"
    - "Verified: Python 3.14.3 on macOS/Darwin 25.3.0, 2026-04-02"
  not_derived_from:
    - "CPython source: Modules/_hashopenssl.c"
    - "CPython source: Modules/_sha256module.c"
  notes:
    - "Cross-verified against openssl dgst -sha256 (see openssl.zspec.zsdl)"
    - "algorithms_guaranteed is a frozenset; membership checked via python_set_contains"
```

If `provenance:` is omitted entirely, the compiler emits an empty provenance object
with only `spec_authors: ["Theseus Z-layer"]` and `created_at` set to the current date.

### 3.1 Backend syntax

| ZSDL | Compiled `library` section |
|------|---------------------------|
| `python_module(hashlib)` | `{"backend": "python_module", "module_name": "hashlib"}` |
| `python_module(urllib.parse)` | `{"backend": "python_module", "module_name": "urllib.parse"}` |
| `ctypes(zstd)` | `{"backend": "ctypes", "soname_patterns": ["zstd"]}` |
| `ctypes(z)` | `{"backend": "ctypes", "soname_patterns": ["z"]}` |
| `cli(openssl)` | `{"backend": "cli", "command": "openssl"}` |
| `cli(curl)` | `{"backend": "cli", "command": "curl"}` |
| `node(semver)` | `{"backend": "cli", "command": "node", "module_name": "semver"}` |

For ctypes backends that need a version function or minimum version prefix, add fields after
the backend line:

```yaml
backend: ctypes(zstd)
version_function: ZSTD_versionString
min_version_prefix: "1."
```

These compile into the `library` section alongside `soname_patterns`.

---

## 4. Type System

ZSDL uses YAML's native type system for everything JSON can express, and adds four
YAML tags for Python types that JSON cannot represent:

| ZSDL literal | JSON output | Python value |
|---|---|---|
| `"hello"` | `"hello"` | `str` |
| `42` | `42` | `int` |
| `3.14` | `3.14` | `float` |
| `true` / `false` | `true` / `false` | `bool` |
| `~` or `null` | `null` | `None` |
| `[1, 2, 3]` | `[1, 2, 3]` | `list` |
| `{a: 1}` | `{"a": 1}` | `dict` |
| `!b64 YWJj` | `{"type": "bytes_b64", "value": "YWJj"}` | `bytes` (decoded) |
| `!hex deadbeef` | `{"type": "bytes_hex", "value": "deadbeef"}` | `bytes` |
| `!ascii "hello"` | `{"type": "bytes_ascii", "value": "hello"}` | `bytes` |
| `!tuple [",", ":"]` | `{"type": "tuple", "value": [",", ":"]}` | `tuple` |

**The `_b64`, `_hex`, `_ascii` suffix convention** for dedicated binary fields (e.g.,
`data_b64`, `stdin_b64`, `bad_input_b64`, `expected_prefix_b64`) is preserved unchanged:
these fields take a plain string value in ZSDL and compile through to JSON identically.
No tag needed; the suffix encodes the type.

```yaml
# binary data in a dedicated field → plain string, suffix carries the type
data_b64: YWJj
stdin_b64: ""
expected_prefix_b64: MS4=    # base64("1.")

# binary data in a generic args/expected field → needs a tag
args: [!b64 YWJj]
expected: !b64 SGVsbG8=
```

---

## 5. Call Expression (for `python_call_eq` / `python_call_raises`)

The `call:` field takes a Python expression string that the compiler parses using
`ast.parse(expr, mode='eval')`. It handles the function call and optional method chain.
The `eq:` field is an alias for `expected:`.

### Syntax

```
call_expr  = primary chain*
primary    = dotted_name "(" arglist? ")"
chain      = "." NAME                         # attribute access (no call)
           | "." NAME "(" arglist? ")"         # method call
arglist    = arg ("," arg)*
arg        = NAME "=" literal                 # keyword arg
           | literal                           # positional arg
literal    = Python string/int/float/bool/None/list/dict literal
dotted_name = NAME ("." NAME)*
```

The harness checks `callable()` on the chained result, so `()` vs no `()` on the method
matters only when you need to pass arguments. `.ratio()` and `.ratio` both invoke the
method; `.year` accesses the attribute because the harness finds it non-callable.

### Chain depth

The harness supports exactly two chain levels: `fn().method` and `fn().method.chain`.
The compiler rejects expressions deeper than that with an explicit error message.

### Argument encoding

Arguments in the expression are Python literals; the compiler converts them:

| Python in expression | Compiled to JSON args element |
|---|---|
| `"hello"` | `"hello"` (plain string) |
| `42` | `42` (plain int) |
| `None` | `null` |
| `True` / `False` | `true` / `false` |
| `[1, 2]` | `[1, 2]` |
| `{"a": 1}` | `{"a": 1}` |

Binary data (bytes, hex) **cannot** appear in a call expression; use structured form.

### `kind:` inference

| Call expression + | Inferred kind |
|---|---|
| `call:` + `eq:` | `python_call_eq` |
| `call:` + `raises:` | `python_call_raises` |
| `call:` alone | compile error |

Explicit `kind:` overrides inference (rarely needed).

### Examples

```yaml
# Attribute access
call: date.fromisoformat("2024-03-15").year
eq: 2024

# Zero-arg method call
call: SequenceMatcher(None, "abc", "xyz").ratio()
eq: 0.0

# Method with args
call: PurePosixPath("report.txt").with_suffix(".md").__str__()
eq: "report.md"

# Double chain: method call → attribute on result
call: SequenceMatcher(None, "ABCDBDE", "BCDE").find_longest_match().size
eq: 3

# Dict arg
call: dumps({"b": 2, "a": 1}, sort_keys=True)
eq: '{"a": 1, "b": 2}'

# Error test
call: loads("not valid json")
raises: ValueError
```

---

## 6. `invariant` Block (single invariant)

For invariants that don't fit a table pattern or use a specialized kind.

### Structure

```yaml
invariant FULL.DOTTED.ID:
  description: "..."   # optional; auto-generated as "{kind}: {id}" if absent
  category: cat_name   # optional
  rfc: "RFC 3986 §3.1" # optional; compiles to rfc_reference
  skip_if: "..."       # optional; verbatim expression string
  
  # Either call-expression style:
  call: fn(args).method
  eq: expected_value

  # Or structured style (kind + kind-specific fields):
  kind: KIND_NAME
  field1: value1
  field2: value2
```

The full dotted ID in the `invariant` line IS the compiled `id` field. The spec's
canonical name is not automatically prepended — write the full path:

```yaml
# In hashlib.zspec.zsdl:
invariant hashlib.sha256.incremental:   # compiles to "id": "hashlib.sha256.incremental"
```

### Kind-specific fields for structured invariants

All field names are **identical to the JSON spec object field names** — no renaming.
Only the outer wrapper (`"spec": {...}`) is dropped; the interior is verbatim:

```yaml
# hash_known_vector
invariant hashlib.sha256.empty:
  kind: hash_known_vector
  category: known_vector
  algorithm: sha256
  data_b64: ""
  expected_hex: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# hash_incremental
invariant hashlib.sha256.incremental:
  kind: hash_incremental
  category: incremental
  algorithm: sha256
  chunks: [SGVs, bG8=]     # plain base64 strings (the _b64 convention is in the field name)
  full_data_b64: SGVsbG8=

# python_set_contains
invariant hashlib.algorithms_guaranteed.sha3:
  kind: python_set_contains
  category: properties
  attribute: algorithms_guaranteed
  must_contain: [sha3_256, sha3_512, blake2b, blake2s]

# python_encode_decode_roundtrip
invariant base64.roundtrip.standard:
  kind: python_encode_decode_roundtrip
  encode_fn: b64encode
  decode_fn: b64decode
  inputs_b64: ["", Zg==, Zm9v, Zm9vYg==, Zm9vYmFy]

# python_struct_roundtrip
invariant struct.roundtrip.uint16_be:
  kind: python_struct_roundtrip
  format: ">H"
  test_cases: [[0], [1], [256], [1000], [65535]]

# python_sqlite_roundtrip
invariant sqlite3.roundtrip.null_value:
  kind: python_sqlite_roundtrip
  setup_sql:
    - "CREATE TABLE t (a INTEGER, b TEXT)"
    - "INSERT INTO t VALUES (1, NULL)"
  query_sql: "SELECT a, b FROM t"
  expected_rows: [[1, ~]]    # ~ is null

# call_eq (ctypes)
invariant zstd.maxCLevel.eq_22:
  kind: call_eq
  function: ZSTD_maxCLevel
  args: []
  arg_types: []
  expected: 22

# version_prefix
invariant zstd.version.prefix:
  kind: version_prefix
  function: ZSTD_versionString
  expected_prefix_b64: MS4=

# constant_eq
invariant zlib.constant.Z_OK:
  kind: constant_eq
  name: Z_OK
  expected_value: 0

# call_returns
invariant zlib.compress2.valid_level:
  kind: call_returns
  function: compress2
  src_b64: SGVsbG8gV29ybGQ=
  level: -1
  dst_capacity: 100
  expected_return: Z_OK

# roundtrip (zlib)
invariant zlib.roundtrip.hello:
  kind: roundtrip
  inputs:
    - label: hello_world
      data_b64: SGVsbG8gV29ybGQ=
    - label: zeros_1mb
      data_b64: AA==
      repeat: 1000000

# wire_bytes
invariant zlib.wire.cm_field:
  kind: wire_bytes
  produce_via: compress2
  produce_args:
    data_b64: SGVsbG8gV29ybGQ=
    level: 6
  assertions:
    - description: "CM field == 8 (deflate)"
      offset: 0
      length: 1
      python_check: "b[0] & 0x0F == 8"

# error_on_bad_input
invariant zlib.error.bad_compressed_data:
  kind: error_on_bad_input
  function: uncompress
  bad_input_b64: bm90IHZhbGlkIHpsaWIgZGF0YQ==
  expected_return: Z_DATA_ERROR

# incremental_eq_oneshot
invariant zlib.incremental.crc32:
  kind: incremental_eq_oneshot
  function: crc32
  init_value: 0
  chunks: [SGVs, bG8=]
  full_data_b64: SGVsbG8=

# cli_exits_with (with timeout)
invariant curl.connection_refused.exit_7:
  kind: cli_exits_with
  args: [--silent, --max-time, "2", "http://localhost:19999"]
  expected_exit: 7
  timeout: 5

# node_constructor_call_eq
invariant ajv.validateSchema.valid_schema:
  kind: node_constructor_call_eq
  class: default
  ctor_args: [{}]
  method: validateSchema
  args: [{type: string}]
  then_call: false
  expected: true
```

### `python_call_raises` with kwargs (structured form)

```yaml
invariant base64.decode.invalid_validate:
  kind: python_call_raises
  function: b64decode
  args: ["+//+"]
  kwargs:
    validate: true
  expected_exception: binascii.Error
```

---

## 7. `table` Block (bulk invariants)

A table generates one invariant per row. It is the primary construct for reducing
repetition. The table name is a documentation label; it does not affect generated IDs.

### Structure

```yaml
table LABEL:
  # Shared fields — applied to every row's spec object
  kind: KIND_NAME
  category: cat_name
  rfc: "optional RFC reference, applied to every row"
  describe: "template; {column_name} is substituted per row"   # optional
  
  function: fn_name      # any spec field can be shared here
  args: [fixed, args]    # shared args (prepended / used when no args column)
  method: attr_name      # shared method chain
  
  # ID generation (choose one):
  id_prefix: path.prefix    # canonical_name.id_prefix.row_id → full id
                            # omit to use row id values directly as the full suffix
  
  # Column schema
  columns: [id, col2, col3, ...]     # first column named 'id' is required unless id_from: set
  # OR:
  id_from: column_name               # use this column's value as the id suffix instead of 'id'
  columns: [col1, col2, ...]         # id_from column must be in this list
  
  rows:
    - [row_id, val2, val3]
    - [row_id, val2, val3, {override_key: override_val}]  # optional trailing dict for per-row overrides
```

### ID generation

```
full_invariant_id = spec.canonical_name
                  + (id_prefix ? "." + id_prefix : "")
                  + "." + row_id_value
```

Examples:

```yaml
# spec canonical_name = hashlib
# id_prefix = sha256
# row id column value = "empty"
# → id = "hashlib.sha256.empty"  ✓

# spec canonical_name = zlib
# no id_prefix
# row id column value = "Z_OK"
# → id = "zlib.Z_OK"  ✗  (want "zlib.constant.Z_OK")

# Fix: add id_prefix: constant
# → id = "zlib.constant.Z_OK"  ✓
```

### Column semantics

Reserved column names:

| Column name | Meaning |
|---|---|
| `id` | Row ID suffix (required unless `id_from:` used) |
| `description` | Per-row description override |
| `rfc` | Per-row `rfc_reference` override |
| `skip_if` | Per-row skip condition |

All other column names map directly to spec object field names. For `python_call_eq`
the column name `expected` maps to `spec.expected`; `method` maps to `spec.method`; etc.

### Per-row overrides

Any row can have a trailing YAML dict as its last element. The dict's keys are spec field
names that override (or add to) the shared table fields for that row only:

```yaml
rows:
  - [match_found, "appel", ["apple","peach","puppy"], ["apple"]]
  - [no_match,    "xyz",   ["apple","peach"],          []      ]
  - [n_limits,    "orange",["apple","orange","grape"], ["orange"], {kwargs: {n: 1}}]
  - [exact_match, "apple", ["apple","peach","puppy"],  ["apple"]]
```

The override dict supports any spec field: `{kwargs: {...}}`, `{description: "..."}`,
`{skip_if: "..."}`, `{timeout: 5}`, `{rfc: "RFC 3986 §3.1"}`, etc.

### `id_from:` for tables where id = another column

When the row ID should be taken from a data column (avoiding a redundant `id` column):

```yaml
table zlib.constants:
  kind: constant_eq
  category: constants
  id_prefix: constant
  id_from: name            # use the 'name' column as the id suffix
  describe: "Library constant {name} == {expected_value}"
  
  columns: [name, expected_value]
  rows:
    - [Z_OK,           0]
    - [Z_STREAM_END,   1]
    - [Z_NEED_DICT,    2]
    - [Z_ERRNO,        -1]
    - [Z_STREAM_ERROR, -2]
    - [Z_DATA_ERROR,   -3]
    - [Z_MEM_ERROR,    -4]
    - [Z_BUF_ERROR,    -5]
    - [Z_VERSION_ERROR,-6]
# → ids: zlib.constant.Z_OK, zlib.constant.Z_STREAM_END, ...
```

### Tables with `call:` expression (python_call_eq shorthand in tables)

For tables where all rows use python_call_eq with varying call expressions, the `call:`
shorthand works at the row level using a template:

```yaml
table urlparse.components:
  kind: python_call_eq
  category: urlparse
  function: urlparse
  args: ["https://example.com:8080/path?q=1&r=2#frag"]
  
  columns: [id, method, expected]
  rows:
    - [scheme,   scheme,   "https"           ]
    - [netloc,   netloc,   "example.com:8080"]
    - [path,     path,     "/path"           ]
    - [query,    query,    "q=1&r=2"         ]
    - [fragment, fragment, "frag"            ]
    - [port,     port,     8080              ]
```

Here `method` and `expected` are column names that map directly to the spec fields.
No special `call:` syntax needed — just standard column names.

### Tables with varying functions per row

```yaml
table urllib_parse.quoting:
  kind: python_call_eq
  category: quoting
  
  columns: [id, function, args, kwargs, expected]
  rows:
    - [spaces,      quote,       ["/path with spaces"], {safe: "/"},  "/path%20with%20spaces"]
    - [empty_safe,  quote,       ["/path"],             {safe: ""},   "%2Fpath"]
    - [quote_plus,  quote_plus,  ["hello world"],       ~,            "hello+world"]
    - [unquote,     unquote,     ["%2Fpath%20spaces"],  ~,            "/path with spaces"]
    - [unquote_plus,unquote_plus,["a=hello+world"],     ~,            "a=hello world"]
```

`~` (null) in a kwargs column means "no kwargs for this row" — equivalent to `{}`.

### Hash known-vector tables

```yaml
table hashlib.sha256:
  kind: hash_known_vector
  category: known_vector
  algorithm: sha256
  rfc: FIPS 180-4 §B.1
  id_prefix: sha256
  
  columns: [id, data_b64, expected_hex]
  rows:
    - [empty,      "",       e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855]
    - [abc,        YWJj,     ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad]
    - [fips_msg2,  WUJDREJD...,248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c]
```

### Node constructor tables (ajv pattern)

```yaml
table ajv.validate:
  kind: node_constructor_call_eq
  class: default
  ctor_args: [{}]
  method: compile
  then_call: true
  
  columns: [id, args, then_args, expected]
  rows:
    - [string_pass,  [{type: string}],  ["hello"], true ]
    - [string_fail,  [{type: string}],  [42],      false]
    - [number_pass,  [{type: number}],  [42],      true ]
    - [number_fail,  [{type: number}],  ["x"],     false]
    - [object_pass,  [{type: object, properties: {name: {type: string}}}], [{name: "Alice"}], true]
```

### CLI tables

```yaml
table openssl.dgst.sha256:
  kind: cli_stdout_contains
  category: known_vector
  args: [dgst, -sha256]
  
  columns: [id, stdin_b64, expected_substring]
  rows:
    - [empty, "",       e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855]
    - [abc,   YWJj,     ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad]
    - [long,  WUJDREJ...,248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c]

table openssl.exits:
  kind: cli_exits_with
  
  columns: [id, args, expected_exit]
  rows:
    - [version, [version],            0]
    - [help,    [help],               0]
    - [bad_cmd, [nosuchcommand_xyz],  1]
```

---

## 8. Documentation Sections

These sections compile to their JSON equivalents unchanged, just in more concise YAML.
None are required. If absent, the compiler emits empty objects / standard defaults.

### `constants:`

The JSON format uses arrays of `{name, value, description}` objects keyed by category.
ZSDL uses a dict-of-dicts keyed by category then name:

```yaml
constants:
  compression_levels:
    ZSTD_CLEVEL_DEFAULT: {value: 3,  description: "Default compression level"}
    ZSTD_minCLevel:      {value: 1,  description: "Minimum standard level (fastest)"}
    ZSTD_maxCLevel:      {value: 22, description: "Maximum level (--ultra mode)"}
  magic_numbers:
    ZSTD_MAGICNUMBER: {value: "0xFD2FB528", description: "Frame magic (LE: 28 B5 2F FD)"}
```

Compiles to:
```json
"constants": {
  "compression_levels": [
    {"name": "ZSTD_CLEVEL_DEFAULT", "value": 3, "description": "Default compression level"},
    ...
  ]
}
```

### `functions:`

```yaml
functions:
  ZSTD_compressBound:
    description: "Returns upper bound on compressed output size for srcSize input bytes"
    params:
      srcSize: {ctype: c_size_t, direction: in, description: "Expected input size in bytes"}
    returns: c_size_t
    return_values:
      positive: "Upper bound in bytes; never an error code"
    post:
      - "return > srcSize for any srcSize > 0"
      - "ZSTD_isError(return) == 0 always"

  urlparse:
    description: "Parse a URL into a ParseResult named-tuple"
    params:
      urlstring: {type: str, direction: in}
    returns: ParseResult
```

The `params` dict-of-dicts compiles to the JSON array-of-objects with `name` taken from
the key. All other fields pass through verbatim.

### `wire_formats:`

```yaml
wire_formats:
  zstd_frame:
    description: "Standard zstd compressed frame"
    rfc_section: RFC 8878 §3.1
    endianness: little
    fields:
      - name: Magic_Number
        offset: 0
        size_bits: 32
        constraint: "value == 0xFD2FB528"
        description: "Bytes on wire: 28 B5 2F FD"
      - name: Frame_Header_Descriptor
        offset: 4
        size_bits: 8
        description: "FCS_Field_Size (bits 7-6), Single_Segment_Flag (bit 5), flags"
      - name: Frame_Content_Size
        offset: variable
        size_bits: variable
        description: "1/2/4/8 bytes per FCS_Field_Size; ZSTD_compress stores this by default"
```

The `fields` list compiles to the JSON `fields` array verbatim.

### `error_model:`

```yaml
error_model:
  semantics: "zstd encodes errors as size_t values near SIZE_MAX (> SIZE_MAX/2); use ZSTD_isError to test"
  stickiness: "Streaming contexts must be reset after error; single-call functions are stateless"
  stderr: "ZSTD_getErrorName(code)"     # or "null" / "stderr"
  codes:
    ZSTD_error_no_error:            {value: 0,  meaning: "Operation completed successfully"}
    ZSTD_error_GENERIC:             {value: 1,  meaning: "Unspecified generic error"}
    ZSTD_error_dstSize_tooSmall:    {value: 70, meaning: "Destination buffer is too small"}
    ZSTD_error_srcSize_wrong:       {value: 72, meaning: "Content size in header does not match actual"}
```

For Python specs with no error codes:

```yaml
error_model:
  semantics: "Raises ValueError/TypeError on bad inputs; each call is stateless"
  stickiness: "N/A"
  stderr: "null"
  codes: {}
```

Or more concisely, use the `python_exceptions` shorthand that the compiler expands:

```yaml
error_model: python_exceptions   # shorthand for stateless Python stdlib error model
```

Compiles to:
```json
"error_model": {
  "return_code_semantics": "Python exceptions; raises on bad inputs; each call is stateless",
  "stream_error_field": "null",
  "error_stickiness": "N/A — each call is stateless",
  "error_codes": []
}
```

---

## 9. Compiler Defaults

When a section is absent from a ZSDL file, the compiler emits:

| Section absent | JSON output |
|---|---|
| `constants:` | `"constants": {}` |
| `types:` | `"types": {}` |
| `wire_formats:` | `"wire_formats": {}` |
| `functions:` | `"functions": {}` |
| `error_model:` | standard empty error model |
| `provenance:` | `spec_authors`, `created_at` only |
| `api_header:` | `"N/A — Python stdlib"` for python_module; `""` otherwise |
| invariant `description:` | `"{kind}: {full_id}"` |
| invariant `category:` | `""` (empty string) |
| `schema_version:` in output | always `"0.1"` |

---

## 10. Complete Examples

### Python module spec (urllib_parse) — 18 invariants, ~75 lines

```yaml
spec: urllib_parse
version: ">=3.4"
backend: python_module(urllib.parse)

docs: https://docs.python.org/3/library/urllib.parse.html
rfcs:
  - "RFC 3986 — Uniform Resource Identifier (URI): Generic Syntax"
  - "RFC 1808 — Relative Uniform Resource Locators"

provenance:
  derived_from:
    - "Python 3 urllib.parse docs"
    - "RFC 3986 — URI Generic Syntax"
    - "Verified: Python 3.14.3 on macOS/Darwin 25.3.0, 2026-04-02"
  not_derived_from:
    - "CPython source: Lib/urllib/parse.py"
  notes:
    - "urlparse returns a ParseResult named-tuple; attributes accessed via method chaining"
    - "urlencode uses insertion-order dict (Python 3.7+); use fixed-order dicts in specs"
    - "quote() does not encode '/' by default (safe='/')"
    - "parse_qs returns lists for each key (multi-value aware)"

error_model: python_exceptions

table urlparse.components:
  kind: python_call_eq
  category: urlparse
  function: urlparse
  args: ["https://example.com:8080/path?q=1&r=2#frag"]
  
  columns: [id, method, expected]
  rows:
    - [scheme,   scheme,   "https"           ]
    - [netloc,   netloc,   "example.com:8080"]
    - [path,     path,     "/path"           ]
    - [query,    query,    "q=1&r=2"         ]
    - [fragment, fragment, "frag"            ]
    - [port,     port,     8080              ]

invariant urllib_parse.urlparse.userinfo:
  category: urlparse
  call: urlparse("https://user:pass@host.example.com/resource").username
  eq: "user"

table urllib_parse.quoting:
  kind: python_call_eq
  category: quoting
  
  columns: [id, function, args, kwargs, expected]
  rows:
    - [spaces,      quote,        ["/path with spaces"],   {safe: "/"},  "/path%20with%20spaces"]
    - [empty_safe,  quote,        ["/path"],               {safe: ""},   "%2Fpath"]
    - [quote_plus,  quote_plus,   ["hello world"],         ~,            "hello+world"]
    - [unquote,     unquote,      ["%2Fpath%20with%20spaces"], ~,        "/path with spaces"]
    - [unquote_plus,unquote_plus, ["a=1&b=hello+world"],   ~,            "a=1&b=hello world"]

invariant urllib_parse.quote_unquote_roundtrip:
  category: roundtrip
  call: unquote("%2Fpath%20with%20spaces")
  eq: "/path with spaces"

table urllib_parse.joining:
  kind: python_call_eq
  category: joining
  function: urljoin
  
  columns: [id, args, expected]
  rows:
    - [relative,         ["https://example.com/base/", "../other"],           "https://example.com/other"     ]
    - [absolute_overrides,["https://example.com/base/","https://other.com/page"],"https://other.com/page"]

invariant urllib_parse.urlencode.simple:
  category: encoding
  call: urlencode({"a": "1", "b": "2"})
  eq: "a=1&b=2"

table urllib_parse.parse_qs:
  kind: python_call_eq
  category: parsing
  function: parse_qs
  
  columns: [id, args, expected]
  rows:
    - [multi_value,  ["a=1&b=2&a=3"], {a: ["1", "3"], b: ["2"]}]
    - [single_value, ["key=value"],   {key: ["value"]}          ]
```

### ctypes spec (zstd) — 15 invariants, ~90 lines

```yaml
spec: zstd
version: ">=1.4.0"
backend: ctypes(zstd)
version_function: ZSTD_versionString

api_header: zstd.h
docs: https://facebook.github.io/zstd/zstd_manual.html
rfcs:
  - "RFC 8878 — Zstandard Compression and the application/zstd Media Type"

provenance:
  derived_from:
    - "RFC 8878 — Zstandard Compression and application/zstd (February 2021)"
    - "https://facebook.github.io/zstd/zstd_manual.html — public API manual"
    - "https://github.com/facebook/zstd/blob/dev/lib/zstd.h — public header (API declarations only)"
  not_derived_from:
    - "zstd/lib/compress/zstd_compress.c"
    - "zstd/lib/decompress/zstd_decompress.c"
    - "Any other zstd C implementation source file"
  notes:
    - "Clean-room boundary: spec team read only public documentation listed above"
    - "zstd errors are size_t values near SIZE_MAX; use ZSTD_isError(code) to test"

constants:
  compression_levels:
    ZSTD_CLEVEL_DEFAULT: {value: 3,  description: "Default compression level"}
    ZSTD_minCLevel:      {value: 1,  description: "Minimum standard level (fastest)"}
    ZSTD_maxCLevel:      {value: 22, description: "Maximum level (--ultra)"}
  magic_numbers:
    ZSTD_MAGICNUMBER:           {value: "0xFD2FB528", description: "Frame magic (LE: 28 B5 2F FD)"}
    ZSTD_MAGIC_SKIPPABLE_START: {value: "0x184D2A50", description: "Skippable frame range start"}
    ZSTD_MAGIC_DICTIONARY:      {value: "0xEC30A437", description: "Dictionary file magic"}
  error_sentinels:
    ZSTD_CONTENTSIZE_UNKNOWN: {value: -1, description: "Content size not stored in frame header"}
    ZSTD_CONTENTSIZE_ERROR:   {value: -2, description: "Input is not a valid zstd frame"}

error_model:
  semantics: "zstd encodes errors as size_t values near SIZE_MAX (> SIZE_MAX/2); use ZSTD_isError"
  stickiness: "Streaming contexts must be reset after error; single-call functions are stateless"
  stderr: "ZSTD_getErrorName(code)"
  codes:
    ZSTD_error_no_error:         {value: 0,  meaning: "Success"}
    ZSTD_error_GENERIC:          {value: 1,  meaning: "Unspecified generic error"}
    ZSTD_error_prefix_unknown:   {value: 10, meaning: "Not a valid zstd frame magic"}
    ZSTD_error_dstSize_tooSmall: {value: 70, meaning: "Destination buffer is too small"}
    ZSTD_error_srcSize_wrong:    {value: 72, meaning: "Content size in header does not match"}

invariant zstd.version.prefix:
  kind: version_prefix
  function: ZSTD_versionString
  expected_prefix_b64: MS4=

table zstd.api.eq:
  kind: call_eq
  id_prefix: ""         # rows are e.g. "maxCLevel.eq_22" → id "zstd.maxCLevel.eq_22"
  
  columns: [id, function, args, arg_types, expected]
  rows:
    - [maxCLevel.eq_22,         ZSTD_maxCLevel,    [],     [],        22   ]
    - [isError.zero,            ZSTD_isError,      [0],    [size_t],  0    ]
    - [isError.small,           ZSTD_isError,      [1],    [size_t],  0    ]
    - [compressBound.known,     ZSTD_compressBound,[35],   [size_t],  98   ]
    - [compressBound.not_error, ZSTD_isError,      [98],   [size_t],  0    ]
    - [maxCLevel.not_error,     ZSTD_isError,      [22],   [size_t],  0    ]
    - [versionNumber.not_error, ZSTD_isError,      [10507],[size_t],  0    ]
    - [isError.near_max,        ZSTD_isError,      [18446744073709551614],[size_t],1]

table zstd.api.ge:
  kind: call_ge
  id_prefix: ""
  
  columns: [id, function, args, arg_types, expected_min]
  rows:
    - [compressBound.nonzero, ZSTD_compressBound, [35],      [size_t], 36      ]
    - [compressBound.zero,    ZSTD_compressBound, [0],       [size_t], 1       ]
    - [compressBound.large,   ZSTD_compressBound, [1048576], [size_t], 1048577 ]
    - [compressBound.256,     ZSTD_compressBound, [256],     [size_t], 257     ]
    - [compressBound.monotone,ZSTD_compressBound, [1024],    [size_t], 98      ]
    - [versionNumber.range,   ZSTD_versionNumber, [],        [],       10400   ]
```

---

## 11. Design Constraints and Invariants

These are things the DSL deliberately does NOT change:

1. **Spec fields are not renamed.** `data_b64`, `expected_hex`, `src_b64`, `method_args`,
   `then_call`, `test_cases`, `setup_sql`, etc. all appear verbatim. The DSL only removes
   the outer JSON wrapper; it does not impose a new vocabulary on the spec object interior.

2. **The JSON output is the authoritative format.** The harness never reads ZSDL. The compiler
   is a pure write-time tool and can be removed or replaced without touching the harness.

3. **All 27 existing invariant kinds are expressible.** There are no kinds that require
   the current JSON format and cannot be expressed in ZSDL.

4. **No new runtime semantics.** ZSDL introduces no new kinds, no new spec fields, no new
   harness behavior. New kinds go in the JSON schema and harness first, then gain ZSDL sugar.

5. **The `call:` expression is Python syntax, not YAML.** The compiler parses it with
   `ast.parse`. Binary data and tuples cannot appear in call expressions — use structured form.

6. **Per-row overrides are the escape hatch.** Any invariant that doesn't fit a table pattern
   cleanly can be expressed as a single `invariant` block. Tables exist for repetition reduction,
   not for forced conformity.

---

## 12. Open Questions

Before implementation, these need a decision:

**Q1: `id_prefix: ""` for top-level IDs**
When a zstd table row has id `maxCLevel.eq_22`, the full id should be `zstd.maxCLevel.eq_22`,
not `zstd..maxCLevel.eq_22`. The rule when `id_prefix` is absent (or `""`): just
`canonical_name + "." + row_id`. When `id_prefix` is set to `"X"`: `canonical_name + ".X." + row_id`.
The empty string case means "no prefix, use row id directly".
→ **Proposed resolution:** Omit `id_prefix:` entirely for top-level IDs; an absent `id_prefix`
means `canonical_name.row_id` with no extra component.

**Q2: Description auto-generation quality**
`"{kind}: {full_id}"` is mechanical and not very informative. The alternative is requiring
an explicit `description:` on every row (adds a column to every table) or a per-table
`describe:` template. The template approach is the right answer for specs that will be
read by humans. But for the compiler v1, the mechanical fallback is fine — descriptions
can be improved later without changing the ZSDL spec structure.
→ **Proposed resolution:** Implement `describe: "template with {col_name} interpolation"` 
on tables and make it optional. Fallback is `"{kind}: {id}"`.

**Q3: `hash_object_attr` table for multiple algorithms**
The cleanest ZSDL for `hashlib.sha256.digest_size`, `hashlib.sha1.digest_size`, etc. would be
a single table:
```yaml
table hashlib.algorithm_attrs:
  kind: hash_object_attr
  id_from: id
  columns: [id, algorithm, attr, expected]
  rows:
    - [sha256.digest_size, sha256, digest_size, 32]
    - [sha256.block_size,  sha256, block_size,  64]
    - [sha1.digest_size,   sha1,   digest_size, 20]
```
This generates `hashlib.sha256.digest_size` etc. correctly.
→ **Resolved:** Yes, this is the right approach.

**Q4: `python_struct_roundtrip` field name inconsistency**
The current JSON has both `test_cases` and `values` as field names for the same semantic concept
(the inputs to pack/unpack). This is a bug in the existing specs.
→ **Proposed resolution:** ZSDL normalizes to `test_cases` for all struct roundtrip invariants.
The compiler always emits `"test_cases"`. The existing `struct.zspec.json` with `values` is
fixed as part of migration.

**Q5: Wire format `offset: variable` vs `offset: "variable"`**
In the current JSON, `offset` is sometimes an integer, sometimes the string `"variable"`,
and sometimes negative (`-4`). ZSDL should preserve this as-is (pass-through).
→ **Resolved:** The `fields` list in `wire_formats` passes through to JSON verbatim.

**Q6: Spec generator integration**
The spec generator (not yet built) will produce ZSDL, not JSON. The spec generator's output
format should target ZSDL tables for bulk invariants. This is strictly cleaner than generating
JSON directly.
→ **Proposed resolution:** Yes, the generator targets ZSDL. The compile step is in the
pipeline: `generate → zsdl → compile → json → harness`.
