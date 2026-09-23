---
family: stringio
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - StringIO
public_oracle: zspecs/theseus_stringio_q.zspec.zsdl
blocks: io
cleanroom_oracle: zspecs/theseus_stringio_q.zspec.zsdl
held_out_oracle: gold/stringio/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_stringio_q
docs:
  - "https://docs.python.org/3/library/io.html"
rfcs:
  []
---

# io

StringIO(text) is an in-memory text buffer. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

getvalue() returns the whole buffer. read() returns the text from the current position, which starts at the beginning.

## What is not in scope

seek, write, and binary buffers.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
