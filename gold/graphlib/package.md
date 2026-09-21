---
family: graphlib
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Graph
public_oracle: zspecs/graphlib.zspec.zsdl
docs:
  - "https://github.com/dagrejs/graphlib#readme"
rfcs:
  []
---

# graphlib

Directed graph data structure used by Dagre. A fresh Graph has nodeCount 0; setNode/setEdge are chainable. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/graphlib.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Fresh counts; nodeCount after two setNode; default directed hasEdge.

## What is not in scope

Layout algorithms (those live in dagre); compound/multigraph options matrix.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
