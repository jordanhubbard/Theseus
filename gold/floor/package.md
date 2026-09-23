---
family: floor
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - floor
public_oracle: zspecs/theseus_floor_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_floor_q.zspec.zsdl
held_out_oracle: gold/floor/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_floor_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

floor(x) is the greatest integer less than or equal to x. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

floor rounds toward negative infinity and returns an int. A positive non-integer decreases. A negative non-integer moves away from zero.

## What is not in scope

Integral-valued inputs other than the public example, and complex values.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
