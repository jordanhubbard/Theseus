---
family: math
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - factorial
  - gcd
  - isqrt
public_oracle: zspecs/math.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_math_q.zspec.zsdl
held_out_oracle: gold/math/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_math_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

Integer helpers from the math module: factorial, Euclidean gcd, and integer square root. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

factorial of small non-negative integers, gcd of two integers, isqrt of a small non-negative integer.

## What is not in scope

Floating-point transcendental functions, fsum, and the C libm bindings.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter. Not derived from implementation source files.
