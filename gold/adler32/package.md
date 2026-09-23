---
family: adler32
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - adler32
public_oracle: zspecs/theseus_adler32_q.zspec.zsdl
blocks: zlib
cleanroom_oracle: zspecs/theseus_adler32_q.zspec.zsdl
held_out_oracle: gold/adler32/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_adler32_q
docs:
  - "https://docs.python.org/3/library/zlib.html"
rfcs:
  []
---

# adler32

adler32(data) is the Adler-32 checksum. s1 starts at 1 and s2 at 0. Each byte updates s1 and s2 modulo 65521. The result is (s2 << 16) | s1. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

adler32(data) is the Adler-32 checksum. s1 starts at 1 and s2 at 0. Each byte updates s1 and s2 modulo 65521. The result is (s2 << 16) | s1.

## What is not in scope

Compression.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
