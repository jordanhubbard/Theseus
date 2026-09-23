---
family: bisectleft
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - bisect_left
public_oracle: zspecs/theseus_bisectleft_q.zspec.zsdl
blocks: bisect
cleanroom_oracle: zspecs/theseus_bisectleft_q.zspec.zsdl
held_out_oracle: gold/bisectleft/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_bisectleft_q
docs:
  - "https://docs.python.org/3/library/bisect.html"
rfcs:
  []
---

# bisect

bisect_left(a, x) is the insertion point that keeps a sorted. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Return the index where x would be inserted, before any existing equal items.

## What is not in scope

bisect_right, key functions, and lo/hi bounds.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
