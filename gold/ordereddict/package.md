---
family: ordereddict
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - OrderedDict
public_oracle: zspecs/theseus_ordereddict_q.zspec.zsdl
blocks: collections
cleanroom_oracle: zspecs/theseus_ordereddict_q.zspec.zsdl
held_out_oracle: gold/ordereddict/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_ordereddict_q
docs:
  - "https://docs.python.org/3/library/collections.html"
rfcs:
  []
---

# OrderedDict

OrderedDict(pairs) stores keys in insertion order. Indexing returns the stored value. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

OrderedDict(pairs) stores keys in insertion order. Indexing returns the stored value.

## What is not in scope

Counter and deque, which are separate clean-room surfaces.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
