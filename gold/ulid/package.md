---
family: ulid
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ulid
  - encodeTime
  - decodeTime
  - monotonicFactory
public_oracle: zspecs/ulid.zspec.zsdl
docs:
  - "https://github.com/ulid/spec"
  - "https://github.com/ulid/javascript#readme"
rfcs:
  []
---

# ulid

Universally Unique Lexicographically Sortable Identifier: 26 Crockford base32 characters, 48-bit time prefix plus 80-bit randomness. encodeTime/decodeTime are the deterministic characterization surface. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/ulid.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

encodeTime(0) and a known millisecond timestamp; decodeTime inverse; ulid(t) length 26 and time-prefix consistency.

## What is not in scope

Random 80-bit suffix; monotonicFactory clock-regression behavior.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
