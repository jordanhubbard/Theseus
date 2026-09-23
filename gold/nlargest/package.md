---
family: nlargest
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - nlargest
public_oracle: zspecs/theseus_nlargest_q.zspec.zsdl
blocks: heapq
cleanroom_oracle: zspecs/theseus_nlargest_q.zspec.zsdl
held_out_oracle: gold/nlargest/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_nlargest_q
docs:
  - "https://docs.python.org/3/library/heapq.html"
rfcs:
  []
---

# heapq

nlargest(n, iterable) returns the n largest values, largest first. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

The result is a list of length n, in descending order.

## What is not in scope

A key function and nsmallest.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
