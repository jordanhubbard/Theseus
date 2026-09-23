---
family: types
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - SimpleNamespace
public_oracle: zspecs/theseus_types_q.zspec.zsdl
blocks: types
cleanroom_oracle: zspecs/theseus_types_q.zspec.zsdl
held_out_oracle: gold/types/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_types_q
docs:
  - "https://docs.python.org/3/library/types.html"
rfcs:
  []
---

# types

SimpleNamespace stores keyword attributes and exposes them as attributes. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

SimpleNamespace stores keyword attributes and exposes them as attributes.

## What is not in scope

Dynamic type construction, coroutine flags, and MappingProxyType.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
