---
family: uuid
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - validate
  - version
  - v3
  - v5
public_oracle: zspecs/uuid.zspec.zsdl
docs:
  - https://github.com/uuidjs/uuid#readme
rfcs:
  - "RFC 9562"
---

# uuid

RFC 9562 UUID helpers in the uuid npm package. v4 is non-deterministic and is not equality-oracled. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/uuid.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

validate, version digits, RFC 9562 v3/v5 DNS name vectors as produced by uuid@13.

## What is not in scope

v1/v6/v7 generation (time), RFC Appendix C v5 vector that disagrees with this library (documented).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
