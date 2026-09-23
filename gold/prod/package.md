---
family: prod
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - prod
public_oracle: zspecs/theseus_prod_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_prod_q.zspec.zsdl
held_out_oracle: gold/prod/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_prod_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

prod(numbers) multiplies the values in a sequence. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

prod(numbers) returns the product of the numbers as an int when every item is an int. The public example multiplies 2, 3, and 4.

## What is not in scope

A start value and floating-point products.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
