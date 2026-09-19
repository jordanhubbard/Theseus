---
family: bisect
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - bisect_left
  - bisect_right
  - bisect
  - insort_left
  - insort_right
  - insort
public_oracle: zspecs/bisect.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/bisect.html"
rfcs:
  []
---

# bisect

Array bisection: locate insertion points in a sorted sequence. bisect_left inserts before existing equal values; bisect_right (alias bisect) inserts after them. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/bisect.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

bisect_left / bisect_right / bisect on sorted lists, including duplicates, empty lists, and lo/hi subranges.

## What is not in scope

key= (Python 3.10+) search over derived keys; in-place insort mutation as a single-shot oracle; thread safety.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
