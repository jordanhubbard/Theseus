---
family: fabs
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - fabs
public_oracle: zspecs/theseus_fabs_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_fabs_q.zspec.zsdl
held_out_oracle: gold/fabs/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_fabs_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

fabs(x) is the absolute value as a float. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

fabs returns a float. A negative input becomes the same magnitude with a positive sign.

## What is not in scope

Complex values.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
