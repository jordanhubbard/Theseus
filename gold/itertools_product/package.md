---
family: itertools_product
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - product
public_oracle: zspecs/itertools_product.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/itertools.html#itertools.product"
  - "https://docs.python.org/3/library/itertools.html"
rfcs:
  []
---

# itertools_product

product([1,2],[3,4]) yields (1,3),(1,4),(2,3),(2,4) — Cartesian product in lexicographic order. product('AB', repeat=2) yields ('A','A'),('A','B'),('B','A'),('B','B'). combinations([1,2,3], 2) yields (1,2),(1,3),(2,3) — r-length subsequences, no repeated elements. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/itertools_product.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

The live probes in `probes.yaml`, confirmed against the installed library. The rest of the public contract stays in the Layer 2 oracle.

## What is not in scope

I/O, process-global configuration, and error paths that the probes do not call. No held-out oracle and no clean-room attempt.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
