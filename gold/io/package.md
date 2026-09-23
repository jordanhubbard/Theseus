---
family: io
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - BytesIO
public_oracle: zspecs/theseus_io_q.zspec.zsdl
blocks: io
cleanroom_oracle: zspecs/theseus_io_q.zspec.zsdl
held_out_oracle: gold/io/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_io_q
docs:
  - "https://docs.python.org/3/library/io.html"
rfcs:
  []
---

# io

BytesIO(data) stores a bytes buffer. getvalue() returns the whole buffer. read() returns the unread bytes from the start when nothing has been read yet. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

BytesIO(data) stores a bytes buffer. getvalue() returns the whole buffer. read() returns the unread bytes from the start when nothing has been read yet.

## What is not in scope

Text IO, file wrappers, and incremental codecs.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
