---
family: struct
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - pack
  - unpack
  - calcsize
  - error
public_oracle: zspecs/struct.zspec.zsdl
docs:
  - https://docs.python.org/3/library/struct.html
rfcs:
  - "IEEE 754-2019"
---

# struct

Pack/unpack Python values to C-struct layouts. This gold set uses explicit endian prefixes and does not test native alignment (@). This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/struct.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

> < ! integer/bool/pad formats, calcsize, round-trip, struct.error on size mismatch and uint8 overflow.

## What is not in scope

Native @ alignment, pack_into buffers, half-float non-zero values (IEEE bit patterns vary by rounding).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
