---
family: b16encode
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - b16encode
public_oracle: zspecs/theseus_b16encode_q.zspec.zsdl
blocks: base64
cleanroom_oracle: zspecs/theseus_b16encode_q.zspec.zsdl
held_out_oracle: gold/b16encode/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_b16encode_q
docs:
  - "https://docs.python.org/3/library/base64.html"
rfcs:
  []
---

# base64

b16encode(data) turns bytes into uppercase hexadecimal. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Each input byte becomes two uppercase hex digits. The result is bytes.

## What is not in scope

Decoding and the other base64 alphabets.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
