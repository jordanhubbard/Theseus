---
family: isqrt
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - isqrt
public_oracle: zspecs/theseus_isqrt_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_isqrt_q.zspec.zsdl
held_out_oracle: gold/isqrt/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_isqrt_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

isqrt(n) is the integer square root of a nonnegative integer. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

isqrt(n) is the greatest integer m such that m*m <= n. The result is an int.

## What is not in scope

Negative inputs and floating-point square roots.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
