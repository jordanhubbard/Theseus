---
family: array
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - array
public_oracle: zspecs/array.zspec.zsdl
blocks: array
cleanroom_oracle: zspecs/theseus_array_q.zspec.zsdl
held_out_oracle: gold/array/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_array_q
docs:
  - "https://docs.python.org/3/library/array.html"
rfcs:
  []
---

# array

Compact typed sequences. array(typecode, initializer) stores the items, and tolist() returns them as a Python list. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Signed byte type code b and unsigned int type code I, constructed from a list, then tolist().

## What is not in scope

File I/O, buffer exports, and byteswap.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter. Not derived from implementation source files.
