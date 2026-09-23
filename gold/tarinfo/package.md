---
family: tarinfo
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - TarInfo
public_oracle: zspecs/theseus_tarinfo_q.zspec.zsdl
blocks: tarfile
cleanroom_oracle: zspecs/theseus_tarinfo_q.zspec.zsdl
held_out_oracle: gold/tarinfo/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_tarinfo_q
docs:
  - "https://docs.python.org/3/library/tarfile.html"
rfcs:
  []
---

# tarfile

TarInfo(name) stores that member name. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

The name attribute is the name passed to the constructor.

## What is not in scope

Headers, archives, and extraction.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
