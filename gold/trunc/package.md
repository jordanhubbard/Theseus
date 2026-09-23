---
family: trunc
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - trunc
public_oracle: zspecs/theseus_trunc_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_trunc_q.zspec.zsdl
held_out_oracle: gold/trunc/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_trunc_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

trunc(x) drops the fractional part toward zero. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

trunc returns an int. A positive non-integer decreases. A negative non-integer moves toward zero.

## What is not in scope

Rounding modes other than toward zero.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
