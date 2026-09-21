---
family: jsonpointer
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - get
  - set
public_oracle: zspecs/jsonpointer.zspec.zsdl
docs:
  - "https://github.com/janl/node-jsonpointer#readme"
rfcs:
  - RFC 6901
---

# jsonpointer

RFC 6901 JSON Pointer. get({a:{b:1}}, '/a/b') is 1. '~1' unescapes '/'. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/jsonpointer.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Nested keys, array indexes, missing path (undefined), RFC 6901 escapes.

## What is not in scope

set() in-place mutation as a live probe (oracle covers get only).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
