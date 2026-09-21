---
family: base_x
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - default
public_oracle: zspecs/base_x.zspec.zsdl
docs:
  - "https://github.com/cryptocoinjs/base-x#readme"
rfcs:
  []
---

# base_x

Arbitrary-alphabet base encoding. A factory `default(alphabet)` returns `{encode, decode}`. Base16 of `[255]` is `ff`. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/base_x.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Base16 encode of a single 0xFF byte; Bitcoin Base58 alphabet encode of [1,2,3,4] as documented by the Layer 2 oracle.

## What is not in scope

Streaming codecs; alphabet validation error strings.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
