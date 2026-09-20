---
family: enum
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Enum
  - IntEnum
  - Flag
  - IntFlag
  - auto
  - unique
public_oracle: zspecs/enum.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/enum.html"
rfcs:
  []
---

# enum

Enumerations. The functional API Enum('Color', 'RED GREEN BLUE') creates three members numbered from 1. StrEnum is 3.11+. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/enum.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Class names; functional Enum/Flag length and member names; StrEnum gated to Python 3.11+.

## What is not in scope

EnumCheck, verify, _proto_member internals; unique() decorator failure messages as KATs.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
