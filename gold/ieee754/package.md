---
family: ieee754
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - read
  - write
public_oracle: zspecs/ieee754.zspec.zsdl
docs:
  - "https://github.com/feross/ieee754#readme"
rfcs:
  - IEEE 754
---

# ieee754

IEEE 754 binary float read/write over arrays. Big-endian single 0x3f800000 is 1.0. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/ieee754.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Known single/double byte patterns from the Layer 2 oracle (1, 1.5, 0, -2).

## What is not in scope

Decimal floating point; signaling NaN payload bits.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
