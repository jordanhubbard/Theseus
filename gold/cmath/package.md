---
family: cmath
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - phase
public_oracle: zspecs/theseus_cmath_q.zspec.zsdl
blocks: cmath
cleanroom_oracle: zspecs/theseus_cmath_q.zspec.zsdl
held_out_oracle: gold/cmath/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_cmath_q
docs:
  - "https://docs.python.org/3/library/cmath.html"
rfcs:
  []
---

# cmath

phase(x) is the argument of a complex number in radians. The phase of a positive real is 0. The phase of a negative real is pi. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

phase(x) is the argument of a complex number in radians. The phase of a positive real is 0. The phase of a negative real is pi.

## What is not in scope

Polar conversion, exponential, and square root.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
