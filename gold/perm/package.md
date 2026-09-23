---
family: perm
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - perm
public_oracle: zspecs/theseus_perm_q.zspec.zsdl
blocks: math
cleanroom_oracle: zspecs/theseus_perm_q.zspec.zsdl
held_out_oracle: gold/perm/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_perm_q
docs:
  - "https://docs.python.org/3/library/math.html"
rfcs:
  []
---

# math

perm(n, k) is the number of ways to choose k ordered items from n. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

perm(n, k) equals n! / (n - k)! when 0 <= k <= n. The result is an int.

## What is not in scope

Binomial coefficients and floating-point specials.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
