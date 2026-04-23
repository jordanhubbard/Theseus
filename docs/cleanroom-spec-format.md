# Clean-Room Spec Format and Authoring Guide

This document covers everything needed to write a `python_cleanroom` spec, synthesize an implementation, and get it registered. For the synthesis architecture, see `docs/architecture.md §Layer 3`. For the ZSDL language reference, see `docs/zsdl-design.md`.

---

## Overview

A clean-room spec describes what a package must do via behavioral invariants, then an LLM synthesizes a complete implementation in Python that satisfies all invariants — **without importing the original package**.

Three things make clean-room specs different from ordinary behavioral specs:

1. **Backend is `python_cleanroom` or `node_cleanroom`**, not `python_module`.
2. **Invariant functions must be zero-argument wrappers** returning a hardcoded expected value. The synthesis LLM frequently violates this rule — it is the most common failure mode.
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

## The Invariant Function Rule

**This is the most important rule, and the most commonly violated.**

Every invariant in a clean-room spec names a zero-argument function that returns a hardcoded value. The harness calls `fn()` with no arguments and compares the result to `expected`.

### Correct pattern

```python
# In the implementation __init__.py:
def json_loads_int():
    return loads('{"a": 1}')["a"]   # hardcoded input, hardcoded operation

def json_round_trip():
    return loads(dumps({"x": [1, 2, 3]}))["x"] == [1, 2, 3]

def json_dumps_has_key():
    return "a" in dumps({"a": 1})
```

```yaml
# In the spec:
invariant theseus_json.loads_int:
  kind: python_call_eq
  function: json_loads_int
  args: []
  expected: 1
```

### Wrong pattern (what the LLM often generates)

```python
# WRONG — parameterized; the harness calls fn() with no args and gets TypeError
def json_loads_int(s):
    return loads(s)["a"]

# ALSO WRONG — alias to parameterized function
json_loads_int = loads_dict   # loads_dict(s) has a parameter
```

When synthesis fails with `TypeError: fn() missing 1 required positional argument`, the fix is always the same: rewrite the invariant function as a zero-arg wrapper that hardcodes the input.

---

## Annotated Example Spec

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

### 1. Parameterized invariant functions

The most frequent failure. The LLM generates functions with parameters because `json_loads_int(s)` is more natural than `json_loads_int()`. The fix is always manual:

```python
# Generated (wrong)
def json_loads_int(s):
    return loads(s)["a"]

# Fix
def json_loads_int():
    return loads('{"a": 1}')["a"]
```

Check for this pattern whenever `cleanroom_verify.py` reports `TypeError: fn() missing N required positional argument(s)`.

### 2. Function aliased to parameterized version

```python
# Generated (wrong)
json_loads_int = loads   # loads(s) requires argument

# Fix
def json_loads_int():
    return loads('{"a": 1}')["a"]
```

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
5. **Zero-arg invariant functions.** Always. No exceptions.
6. **Isolation-verified.** All invariants must pass with `THESEUS_BLOCKED_PACKAGE` set to the original module name.
7. **Registry-gated.** Package is not usable as a dependency until `registry.py verify` succeeds.

---

## What NOT to do

```python
# WRONG: wrapper, not a clean-room rewrite
import json  # BLOCKED — THESEUS ISOLATION VIOLATION

def json_loads_int():
    return json.loads('{"a": 1}')["a"]
```

```python
# WRONG: parameterized invariant function
def json_loads_int(s):
    return loads(s)["a"]
```

```python
# WRONG: alias to a parameterized function
json_loads_int = loads
```

```python
# RIGHT: zero-arg wrapper, hardcoded input
def json_loads_int():
    # Hand-written recursive descent parser — no import of json
    return _parse_object('{"a": 1}')["a"]
```
