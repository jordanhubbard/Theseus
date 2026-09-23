---
family: hexlify
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - hexlify
public_oracle: zspecs/theseus_hexlify_q.zspec.zsdl
blocks: binascii
cleanroom_oracle: zspecs/theseus_hexlify_q.zspec.zsdl
held_out_oracle: gold/hexlify/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_hexlify_q
docs:
  - "https://docs.python.org/3/library/binascii.html"
rfcs:
  []
---

# hexlify

hexlify(data) returns lowercase hexadecimal digits for each input byte, as a bytes object. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

hexlify(data) returns lowercase hexadecimal digits for each input byte, as a bytes object.

## What is not in scope

Base64, CRC, and quoted-printable helpers in the same module.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
