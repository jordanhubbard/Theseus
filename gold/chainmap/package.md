---
family: chainmap
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ChainMap
public_oracle: zspecs/theseus_chainmap_q.zspec.zsdl
blocks: collections
cleanroom_oracle: zspecs/theseus_chainmap_q.zspec.zsdl
held_out_oracle: gold/chainmap/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_chainmap_q
docs:
  - "https://docs.python.org/3/library/collections.html"
rfcs:
  []
---

# ChainMap

ChainMap(*maps) looks up a key in the maps from left to right and returns the first hit. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

ChainMap(*maps) looks up a key in the maps from left to right and returns the first hit.

## What is not in scope

Counter and deque.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
