---
family: unhexlify
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - unhexlify
public_oracle: zspecs/theseus_unhexlify_q.zspec.zsdl
blocks: binascii
cleanroom_oracle: zspecs/theseus_unhexlify_q.zspec.zsdl
held_out_oracle: gold/unhexlify/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_unhexlify_q
docs:
  - "https://docs.python.org/3/library/binascii.html"
rfcs:
  []
---

# unhexlify

unhexlify(hex) turns a pair of hex digits into one byte. Digits are ASCII 0-9 and a-f. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

unhexlify(hex) turns a pair of hex digits into one byte. Digits are ASCII 0-9 and a-f.

## What is not in scope

Base64 and CRC helpers.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
