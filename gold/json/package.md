---
family: json
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
blocks: json
exports:
  - dumps
  - loads
  - JSONDecodeError
public_oracle: zspecs/json.zspec.zsdl
cleanroom_oracle: zspecs/theseus_json.zspec.zsdl
held_out_oracle: gold/json/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_json
docs:
  - https://www.json.org/json-en.html
  - https://docs.python.org/3/library/json.html
rfcs:
  - "RFC 8259"
  - "ECMA-404"
---

# JSON

A JSON codec is a pair of functions: `dumps` turns a Python value into a JSON
text, and `loads` turns a JSON text into a Python value. This document is the
**authority** for the Theseus JSON gold-set spike. It is not an implementation
and it is not an oracle. Oracles live in the files named in the frontmatter.

## Public surface

- `dumps(obj, *, separators=None, ensure_ascii=True, **kwargs) -> str`
- `loads(s: str) -> object`
- `JSONDecodeError` — a `ValueError` subclass raised when `loads` is given
  text that is not a single JSON value (empty input, truncated text, trailing
  junk, non-JSON literals such as `nan`).

Default `dumps` separators are `", "` between items and `": "` between keys
and values, matching Python's `json` module. Passing
`separators=(",", ":")` produces compact text with no extra spaces.
`ensure_ascii=True` encodes non-ASCII characters as `\\uXXXX` escapes.

Python values map as: `None` ↔ `null`, `True`/`False` ↔ `true`/`false`,
`int`/`str`/`list`/`dict` as RFC 8259 numbers, strings, arrays, and objects.
Object keys must be strings. This spike does not claim `NaN` / `Infinity`
support; those are not JSON (RFC 8259 §6).

## What is in scope

RFC-shaped encode/decode of the types above, the default and compact
separator styles, and decode errors. Version target: Python 3.9+.

## What is not in scope

- `dump` / `load` file objects, `cls` hooks, `object_hook`, `parse_float`
- `indent`, `sort_keys`, `skipkeys`, `allow_nan=True`
- `JSONEncoder` / `JSONDecoder` classes
- `bytes` input to `loads` (stdlib accepts UTF-8 bytes; this spike is `str`)
- Live capture of CPython's C accelerator (`_json`)

## Authority vs oracles vs generation

| Artifact | Role | Visible to a synthesizer? |
|---|---|---|
| This file | Human-reviewable intent | Yes |
| `zspecs/json.zspec.zsdl` | Public oracle vs the **installed** `json` module | Yes (characterization) |
| `zspecs/theseus_json.zspec.zsdl` | Public-API oracle vs the clean-room impl (`dumps`/`loads` with arguments) | Yes |
| `gold/json/held_out.zspec.zsdl` | Independent acceptance oracle | **No** |

The held-out file must never appear in a synthesis prompt. `tools/held_out_guard.py`
enforces that. Passing the public oracle is not qualification. Qualification
(ADR 0001) additionally requires empty-workspace regeneration against the
held-out oracle, twice. This spike does not claim `qualified`.

## Uncertainty

- Trailing-comma and comment rejection are RFC-required but easy to get wrong;
  those cases live in the held-out oracle, not the public spec.
- Unicode `ensure_ascii` escaping is specified here; the exact BMP test vector
  is held out.
- Duplicate object keys: RFC 8259 allows implementations to use the last value.
  This spike does not test duplicate keys.

## Provenance

Derived from RFC 8259, ECMA-404, json.org, and the Python `json` documentation.
Not derived from CPython `Lib/json/` or `Modules/_json.c`.
