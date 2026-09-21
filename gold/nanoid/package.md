---
family: nanoid
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - nanoid
  - customAlphabet
public_oracle: zspecs/nanoid.zspec.zsdl
docs:
  - "https://github.com/ai/nanoid#readme"
rfcs:
  []
---

# nanoid

URL-safe ID generator. Default length is 21. customAlphabet('a', 5)() is aaaaa (deterministic single-char alphabet). This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/nanoid.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Default length 21; customAlphabet single-character determinism.

## What is not in scope

Cryptographic RNG quality; collision probability estimates.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
