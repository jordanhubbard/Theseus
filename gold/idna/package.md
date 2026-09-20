---
family: idna
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - encode
  - decode
public_oracle: zspecs/idna.zspec.zsdl
docs:
  - "https://github.com/kjd/idna"
rfcs:
  - "RFC 5891"
  - "RFC 5892"
  - "RFC 3492"
---

# idna

IDNA 2008. encode returns ACE bytes; ASCII labels pass through. decode inverts ACE. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/idna.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

encode/decode of ASCII python.org and documented non-ASCII vectors already in the Layer 2 oracle.

## What is not in scope

UTS #46 transitional processing flags; core.alabel on empty labels as a full error table.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
