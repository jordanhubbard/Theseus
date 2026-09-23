---
family: ceil
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ceil
public_oracle: zspecs/theseus_ceil_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_ceil_q.zspec.zsdl
held_out_oracle: gold/ceil/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_ceil_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

ceil(x) is the smallest integer greater than or equal to x. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

ceil rounds toward positive infinity and returns an int. A positive non-integer increases. A negative non-integer moves toward zero.

## What is not in scope

Integral-valued inputs other than the public example, and complex values.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
