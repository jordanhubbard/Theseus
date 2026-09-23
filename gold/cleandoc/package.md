---
family: cleandoc
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - cleandoc
public_oracle: zspecs/theseus_cleandoc_q.zspec.zsdl
blocks: inspect
cleanroom_oracle: zspecs/theseus_cleandoc_q.zspec.zsdl
held_out_oracle: gold/cleandoc/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_cleandoc_q
docs:
  - "https://docs.python.org/3/library/inspect.html"
rfcs:
  []
---

# inspect

cleandoc(text) removes the common leading whitespace from every line after the first, and removes the first line's leading whitespace. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

cleandoc(text) removes the common leading whitespace from every line after the first, and removes the first line's leading whitespace.

## What is not in scope

Signatures, stacks, and source retrieval.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
