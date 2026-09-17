# Clean-Room Spec Format and Authoring Guide

This document covers everything needed to write a `python_cleanroom` spec, synthesize an implementation, and get it registered. For the synthesis architecture, see `docs/architecture.md §Layer 3`. For the ZSDL language reference, see `docs/zsdl-design.md`.

---

## Overview

A clean-room spec describes what a package must do via behavioral invariants, then an LLM synthesizes a complete implementation in Python that satisfies all invariants — **without importing the original package**.

Three things make clean-room specs different from ordinary behavioral specs:

1. **Backend is `python_cleanroom` or `node_cleanroom`**, not `python_module`.
2. **Gold-set specs grade the public API** (`dumps`/`loads` with arguments). Legacy factory specs still use zero-arg wrappers; do not copy that pattern for new gold-set work (ADR 0002).
3. **The original module is actively blocked** during verification via `THESEUS_BLOCKED_PACKAGE`. Any import of the blocked name causes an immediate isolation failure.

---

## Backend Declarations

### Python packages

```yaml
spec: theseus_json
version: ">=3.9"
backend: python_cleanroom(theseus_json)
blocks: json
```

- `blocks:` names the original module that will be blocked during verification.
- Implementation lives at: `cleanroom/python/theseus_json/__init__.py`
- Only Python standard library imports and other `theseus_registry.json` verified packages allowed.

### Node.js packages

```yaml
spec: theseus_path_node
version: ">=18"
backend: node_cleanroom(theseus_path_node)
blocks: path
```

- Implementation lives at: `cleanroom/node/theseus_path_node/index.js`
- Only Node.js built-in modules allowed (except the target itself).

---

## Public-API oracles vs legacy wrappers

Gold-set work (JSON spike: [`gold/json/package.md`](../gold/json/package.md), [ADR 0002](decisions/0002-json-authority-format.md)) splits three artifacts:

1. **Authority** — Markdown with typed frontmatter. Not executable.
2. **Public oracle** — ZSDL that calls the real exports with arguments (`dumps`, `loads`, `python_call_raises`).
3. **Held-out oracle** — lives under `gold/<family>/`, **not** in `zspecs/`, so `make compile-zsdl --all` and wave synthesis do not ingest it. `tools/held_out_guard.py` fails if distinctive held-out tokens leak into a synthesis prompt.

`cleanroom_verify.py` calls `fn(*args, **kwargs)` and honors typed `!tuple` kwargs. Passing the public oracle is **not** qualification.

### Gold-set pattern (use this)

```python
# cleanroom/python/theseus_json/__init__.py
class JSONDecodeError(ValueError):
    pass

def dumps(obj, separators=None, ensure_ascii=True, **kwargs):
    ...

def loads(s):
    ...
```

```yaml
# zspecs/theseus_json.zspec.zsdl
function: dumps
args: [[1, 2, 3]]
kwargs: {separators: !tuple [",", ":"]}
expected: "[1,2,3]"
```

### Legacy factory pattern (do not copy for gold-set)

Older `theseus_*` specs name zero-argument wrappers. The harness still calls `fn(*args)`; empty `args` is what made wrappers look required. Leave those specs until their family is migrated.

```yaml
# Legacy — not the gold-set template
function: json_loads_int
args: []
expected: 1
```

---

## Annotated Example Spec

The hashlib example below is a **legacy factory** spec (zero-arg wrappers). For JSON-shaped gold-set work, copy `zspecs/theseus_json.zspec.zsdl` instead.

```yaml
spec: theseus_hashlib
version: ">=3.9"
backend: python_cleanroom(theseus_hashlib)
blocks: hashlib

docs: https://docs.python.org/3/library/hashlib.html

provenance:
  derived_from:
    - "FIPS 180-4 — Secure Hash Standard"
    - "https://docs.python.org/3/library/hashlib.html"
  notes:
    - "Clean-room SHA-256 from scratch. Do NOT import hashlib, hmac, or ssl."
    - "sha256_abc(): sha256(b'abc') == 'ba7816bf...'"
    - "sha256_empty(): sha256(b'') == 'e3b0c442...'"
    - "sha256_digest_length(): len(sha256(b'')) == 64 (hex digits)"
  created_at: "2026-04-19T00:00:00Z"

error_model: python_exceptions

invariant theseus_hashlib.sha256_empty:
  description: "sha256(b'') == 'e3b0c44298fc1c149afbf4c8996fb924...'"
  category: sha256
  kind: python_call_eq
  function: sha256_empty
  args: []
  expected: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

invariant theseus_hashlib.sha256_abc:
  description: "sha256(b'abc') == 'ba7816bf...'"
  category: sha256
  kind: python_call_eq
  function: sha256_abc
  args: []
  expected: "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

invariant theseus_hashlib.sha256_digest_length:
  description: "len(sha256(b'')) == 64"
  category: sha256
  kind: python_call_eq
  function: sha256_digest_length
  args: []
  expected: 64
```

Key points:
- `args: []` — always empty for clean-room specs.
- `expected:` — a hardcoded literal (string, number, bool, list, or dict).
- The `provenance.notes` block tells the synthesis LLM exactly what to implement and what not to import. Be specific — this is the implementation prompt.

---

## Provenance Notes as Implementation Prompts

The `provenance.notes` list is read by `synthesize_waves.py` and passed to the LLM as context. Write it as a precise description of what the implementation must do:

```yaml
provenance:
  notes:
    - "Clean-room CSV reader. Do NOT import csv."
    - "reader(iterable, delimiter=','): yield lists of strings from each row."
    - "Handle quoted fields with embedded commas."
    - "csv_reader_basic(): list(reader(['a,b,c']))[0] == ['a','b','c']."
    - "csv_reader_quoted(): list(reader(['\"a,b\",c']))[0] == ['a,b','c']."
    - "csv_writer_roundtrip(): write then read recovers original rows."
    - "Export: reader, writer, DictReader, DictWriter."
```

Rules for effective notes:
1. Start with what NOT to import.
2. Describe each exported function/class in one line.
3. Include the invariant function signatures exactly — prevents the LLM from generating parameterized wrappers.
4. List the `Export:` set explicitly — the LLM uses this for `__all__`.

---

## Complete Authoring Workflow

```bash
# 1. Write the spec
$EDITOR zspecs/theseus_mylib.zspec.zsdl

# 2. Compile to JSON (build artifact — not committed)
python3 tools/zsdl_compile.py zspecs/theseus_mylib.zspec.zsdl
# Output: _build/zspecs/theseus_mylib.zspec.json  (N invariants)

# 3. Clear cr1 from waves_completed so the runner picks up new specs
python3 -c "
import json
with open('reports/synthesis/wave_state.json') as f: s=json.load(f)
s['waves_completed']=[w for w in s['waves_completed'] if w!='cr1']
with open('reports/synthesis/wave_state.json','w') as f: json.dump(s,f,indent=2)
"

# 4. Synthesize
python3 tools/synthesize_waves.py --wave cr1

# 5. Check results — fix any failures (see below)
python3 tools/cleanroom_verify.py _build/zspecs/theseus_mylib.zspec.json

# 6. Register
python3 tools/registry.py register theseus_mylib \
    cleanroom/python/theseus_mylib \
    _build/zspecs/theseus_mylib.zspec.json
python3 tools/registry.py verify theseus_mylib

# 7. Commit
git add cleanroom/python/theseus_mylib/ zspecs/theseus_mylib.zspec.zsdl \
    theseus_registry.json reports/synthesis/wave_state.json
git commit -m "feat: add theseus_mylib clean-room package"
```

---

## Common Failure Modes and Fixes

### 1. Spec grades a wrapper instead of the public API

Gold-set packages must export and test the real names. If the spec still calls `json_loads_int` with `args: []`, rewrite it to call `loads` / `dumps` with arguments (see `zspecs/theseus_json.zspec.zsdl`).

Legacy factory specs may still fail with `TypeError: fn() missing N required positional argument(s)` when synthesis emits parameterized helpers. Those packages have not been migrated.

### 2. Held-out tokens leaked into the synthesis prompt

`tools/held_out_guard.py` must stay green. Distinctive held-out vectors (`1.5e2`, trailing commas, BMP `ensure_ascii` examples) must not appear in `zspecs/theseus_json.zspec.zsdl` or `gold/json/package.md`.

### 3. Wrong expected value in spec

Some values are non-obvious. Example: `statistics.stdev([2,4,4,4,5,5,7,9])` returns `2.138...` (sample, Bessel's correction), not `2.0` (population). If the spec expected value was wrong, update the spec and recompile — do not fudge the implementation.

```bash
# After fixing the spec:
python3 tools/zsdl_compile.py zspecs/theseus_mylib.zspec.zsdl
python3 tools/cleanroom_verify.py _build/zspecs/theseus_mylib.zspec.json
```

### 4. Python 3.14 lazy annotations

In Python 3.14, `cls.__dict__.get('__annotations__', {})` may return an empty dict because annotations are lazily computed. Use `getattr(cls, '__annotations__', {}) or {}` instead.

### 5. Synthesis timeout / empty directory

If the synthesis runner times out mid-batch, some package directories may be created but empty (`__init__.py` missing). In this case, write the implementation manually — it is usually straightforward given the spec's provenance notes.

---

## Rules Summary

1. **No importing the original.** `import json` inside `theseus_json` is an isolation violation.
2. **No third-party deps.** Only Python stdlib + verified Theseus packages from `theseus_registry.json`.
3. **No subprocess delegation.** Cannot shell out to the original tool.
4. **Spec-first.** Spec written and compiled before synthesis begins.
5. **Gold-set invariants call the public API with arguments.** Do not add zero-arg self-test wrappers on gold-set packages. Legacy factory specs still use wrappers until migrated.
6. **Isolation-verified.** All invariants must pass with `THESEUS_BLOCKED_PACKAGE` set to the original module name.
7. **Registry-gated.** Package is not usable as a dependency until `registry.py verify` succeeds.

---

## What NOT to do

```python
# WRONG: wrapper, not a clean-room rewrite
import json  # BLOCKED — THESEUS ISOLATION VIOLATION

def dumps(obj, **kwargs):
    return json.dumps(obj, **kwargs)
```

```python
# WRONG on a gold-set package: self-test wrapper instead of the public API
def json_loads_int():
    return loads('{"a": 1}')["a"]
```

```python
# RIGHT: export dumps/loads; the oracle supplies arguments
def dumps(obj, separators=None, ensure_ascii=True, **kwargs):
    ...
```
