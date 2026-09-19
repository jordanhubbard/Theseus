---
family: msgpack
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - packb
  - unpackb
public_oracle: zspecs/msgpack.zspec.zsdl
docs:
  - "https://msgpack-python.readthedocs.io/"
  - "https://github.com/msgpack/msgpack/blob/master/spec.md"
rfcs:
  []
---

# msgpack

MessagePack binary serialization. packb/unpackb implement the spec type system (nil, bool, ints, strings, arrays). This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/msgpack.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Spec-mandated packb wire bytes for None/False/True/0/1 and unpackb of those bytes; lossless roundtrip for scalars and short lists.

## What is not in scope

Timestamp ext types, raw=True Py2 bytes mode, streaming Unpacker, C vs fallback implementation choice.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
