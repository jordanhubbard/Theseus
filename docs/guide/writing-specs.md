# Writing a Behavioral Spec

This guide walks you through writing your first Z-layer spec. It covers practical
decisions, common patterns, and mistakes to avoid. For the full ZSDL syntax
reference, see [Reference](reference.md) or `docs/zsdl-design.md`.

---

## The Authoring Workflow

```bash
# 1. Create the spec
$EDITOR zspecs/mylib.zspec.zsdl

# 2. Compile to JSON
make compile-zsdl ZSDL=zspecs/mylib.zspec.zsdl

# 3. Verify against the installed library
python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json

# 4. TDD loop — recompile + rerun on every save
make compile-zsdl ZSDL=zspecs/mylib.zspec.zsdl && \
  python3 tools/verify_behavior.py _build/zspecs/mylib.zspec.json --watch
```

Compiled JSON files go in `_build/zspecs/` and are **not committed** to git.
The `.zsdl` source is the canonical artifact — commit that.

---

## Step 1: Choose the Right Backend

| Decision | Backend |
|----------|---------|
| `python3 -c "import mylib"` works | `python_module` |
| Library exposes only a CLI binary | `cli` |
| Library is a C shared library (`.so`/`.dylib`) | `ctypes` |
| Library is an npm package | `node` |
| npm package uses ES modules | `node` + `esm: true` |

---

## Step 2: Write the Header

Every ZSDL file starts with a header block:

```yaml
spec: mylib                          # canonical_name; matches zspecs/mylib.zspec.zsdl
version: ">=1.0"                     # spec_for_versions: semver range this spec covers
backend: python_module(mylib)        # or: ctypes(name), cli(cmd), node(pkg)

docs: https://docs.example.com/mylib/  # public documentation URL

provenance:
  derived_from:
    - "mylib official documentation — https://docs.example.com/mylib/"
    - "Verified with mylib 1.2.3 on macOS/Darwin 25.4.0, 2026-04-06"
  not_derived_from:
    - "mylib source: src/mylib.c"    # list the files you did NOT read
```

The `provenance` block is not optional — it is the clean-room attestation. List
every source you consulted in `derived_from`. List every implementation file you
explicitly did not read in `not_derived_from`.

---

## Step 3: Write Invariants

### The inline `call:` shorthand (most common)

For simple function calls, use the one-line `call:` shorthand:

```yaml
invariant mylib.encode.hello:
  description: "encode('hello') returns expected bytes"
  category: encode
  call: encode("hello")
  eq: "aGVsbG8="
```

Supported shorthand forms:

| Shorthand | Meaning |
|-----------|---------|
| `call: fn(args)` | call `module.fn(*args)` |
| `eq: value` | compare result to `value` |
| `raises: ExcType` | verify exception is raised |
| `call: obj.method(args)` | attribute access then call |

### Tables (for repeated patterns)

When you're calling the same function with many different inputs, use a table:

```yaml
table mylib.encode.vectors:
  kind: python_call_eq
  category: encode
  function: encode
  id_prefix: encode

  columns: [id, args, expected]
  rows:
    - [empty,  [""],        ""]
    - [hello,  ["hello"],   "aGVsbG8="]
    - [world,  ["world"],   "d29ybGQ="]
```

Use a table when you have three or more rows sharing the same `kind` and most fields.
Two rows can still benefit from a table; one row is always a standalone invariant.

### Varying the function per row

Add `function` as a column when rows call different functions:

```yaml
table mylib.operations:
  kind: python_call_eq
  category: ops
  id_prefix: ~

  columns: [id, function, args, expected]
  rows:
    - [encode,   encode,   ["hello"], "aGVsbG8="]
    - [decode,   decode,   ["aGVsbG8="], "hello"]
```

### Error cases

```yaml
invariant mylib.error.bad_input:
  call: encode(None)
  raises: TypeError

invariant mylib.error.bad_format:
  description: "decode raises ValueError on invalid base64"
  category: errors
  kind: python_call_raises
  function: decode
  args: ["not-valid-base64!!!"]
  expected_exception: ValueError
```

---

## Step 4: Choose Categories

Group invariants into 3–6 logical categories. Each invariant has a `category` field
that appears in `--filter` output and the coverage report. Common patterns:

| Library type | Suggested categories |
|-------------|---------------------|
| Encoding/hashing | `encode`, `decode`, `roundtrip`, `known_vector`, `errors` |
| Pattern matching | `basic`, `flags`, `groups`, `errors` |
| Data structures | `construction`, `methods`, `predicates`, `errors` |
| CLI tools | `version`, `help`, `basic`, `flags`, `errors` |

---

## Step 5: Test Vectors

**All inputs must be fixed literals.** Never generate test data at runtime.

```yaml
# Bad — non-reproducible
args: [str(datetime.now())]

# Good
args: ["2024-03-15"]
```

**Use RFC test vectors when available.** If the algorithm has a standards document
(RFC, FIPS publication), use the published known-answer test vectors verbatim and
cite them in `rfc:`:

```yaml
table hashlib.sha256.known_vectors:
  kind: hash_known_vector
  algorithm: sha256

  columns: [id, data_b64, expected_hex, rfc]
  rows:
    - [empty, "", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "FIPS 180-4"]
    - [abc,   "YWJj", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "FIPS 180-4 Appendix B"]
```

When no RFC vector exists, document the tool/version you used to verify the expected
value in `provenance.derived_from` (e.g. `"Verified with Python 3.14.3 + sha256sum on
macOS/Darwin 25.4.0, 2026-04-06"`).

---

## Step 6: Add `skip_if` for Platform or Version Differences

Gate invariants that only apply to specific versions or platforms:

```yaml
invariant mylib.feature.new_in_1_3:
  description: "new feature added in 1.3"
  category: features
  skip_if: 'not semver_satisfies(lib_version, ">=1.3")'
  call: new_feature()
  eq: True

invariant mylib.behavior.linux_only:
  description: "Linux-specific path behavior"
  category: platform
  skip_if: 'platform != "linux"'
  call: get_linux_path()
  eq: "/proc/self"
```

---

## Step 7: Write the Test

Every new spec should have a corresponding test file in `tests/`:

```python
# tests/test_verify_behavior_mylib.py
import pytest
import subprocess
import sys

# Skip if the library is not installed
pytest.importorskip("mylib")

def _run(args, **kwargs):
    return subprocess.run(
        [sys.executable, "tools/verify_behavior.py"] + args,
        capture_output=True, text=True, **kwargs
    )

class TestMyLibSpec:
    def test_all_pass(self, tmp_path):
        result = _run(["_build/zspecs/mylib.zspec.json"])
        assert result.returncode == 0

    def test_invariant_count(self, tmp_path):
        result = _run(["_build/zspecs/mylib.zspec.json", "--list"])
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        assert len(lines) == 12  # update to match actual count
```

---

## Common Mistakes

### 1. `method_chain` with dunders that require arguments

`method_chain` calls the chained attribute as a **zero-argument method**. It fails
for dunders that need an argument:

```yaml
# Wrong — __contains__ requires an argument
method: __contains__
method_chain: "hello"    # NOT how method_chain works

# Correct
method: __contains__
method_args: ["hello"]
```

Also avoid `method_chain: __bool__` and `method: __class__` + `method_chain: __name__` —
these produce incorrect results or exceptions on Python 3.14+.

### 2. Wrong arg types in ctypes specs

Always set `arg_types` for ctypes invariants:

```yaml
# Wrong — missing arg_types
kind: call_eq
function: crc32
args: [0, "aGVsbG8=", 5]

# Correct
kind: call_eq
function: crc32
args: [0, "aGVsbG8=", 5]
arg_types: [int, bytes_b64, int]
expected: 907060870
```

### 3. YAML dict literals in `call:` expressions

Quote the entire expression when it contains `{`:

```yaml
# Wrong — YAML tries to parse { as a mapping
call: dumps({"b": 2, "a": 1}, sort_keys=True)

# Correct
call: 'dumps({"b": 2, "a": 1}, sort_keys=True)'
```

### 4. Bare `null`/`true`/`false` in table row IDs

```yaml
# Wrong — YAML parses null as null, not the string "null"
rows:
  - [null, ["not-a-version"], ~]

# Correct
rows:
  - ["null_input", ["not-a-version"], ~]
```

### 5. Testing implementation details

Specs must be derived from public documentation only. If the only way to know an
expected value is to read the source code, that value does not belong in a spec.

---

## Quick-Start Template

Copy and fill in this skeleton:

```yaml
spec: mylib
version: ">=X.Y"
backend: python_module(mylib)      # or: ctypes(name), cli(cmd), node(pkg)

docs: https://docs.example.com/mylib/

provenance:
  derived_from:
    - "mylib official documentation — https://docs.example.com/mylib/"
    - "Verified with mylib X.Y.Z on macOS/Darwin NN.N.N, YYYY-MM-DD"
  not_derived_from:
    - "mylib source: src/mylib.c"

error_model: python_exceptions     # omit for ctypes/cli

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

---

## Adding a Submodule Preload

Some packages don't expose submodules on bare `import`. For example, `dns.name` is
not accessible after `import dns` — you must `import dns.name` first.

Add entries to `_SUBMODULE_PRELOADS` in `tools/verify_behavior.py`:

```python
_SUBMODULE_PRELOADS = {
    # ...existing entries...
    "mylib": ["mylib.submodule1", "mylib.submodule2"],
}
```

Then use `mylib.submodule1.SomeClass` in your spec as if it were already imported.

---

## Adding a Package Name Alias

If the PyPI package name differs from the spec file stem, add an entry to
`_PACKAGE_ALIASES` in `tools/spec_coverage.py`:

```python
_PACKAGE_ALIASES: dict[str, str] = {
    # ...existing entries...
    "my-package":  "mylib",  # PyPI: my-package; spec: mylib.zspec.zsdl
    "my_package":  "mylib",  # underscore variant
}
```
