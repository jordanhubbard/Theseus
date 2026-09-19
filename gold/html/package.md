---
family: html
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - escape
  - unescape
public_oracle: zspecs/html.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/html.html"
rfcs:
  []
---

# html

HTML escaping and unescaping. escape converts &, <, > (and quotes when quote=True). unescape applies HTML 5 named and numeric character references. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/html.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

escape of &<>"'; quote=False leaving quotes; unescape of named entities, decimal/hex numeric refs, and &nbsp;.

## What is not in scope

html.parser and html.entities as separate modules; full HTML 5 named-entity table; invalid-reference recovery beyond leftover '&'.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
