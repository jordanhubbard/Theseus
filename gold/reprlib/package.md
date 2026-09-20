---
family: reprlib
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - repr
  - Repr
public_oracle: zspecs/reprlib.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/reprlib.html"
rfcs:
  []
---

# reprlib

Size-limited repr. Default Repr.maxlist is 6; a 7-element list truncates with '...'. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/reprlib.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

repr of short primitives; 6- vs 7-element list truncation; Repr default maxlist/maxstring if already in the oracle.

## What is not in scope

Recursive objects; custom Repr subclasses; aRepr mutation.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
