---
family: unicodedata
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - name
public_oracle: zspecs/theseus_unicodedata_q.zspec.zsdl
blocks: unicodedata
cleanroom_oracle: zspecs/theseus_unicodedata_q.zspec.zsdl
held_out_oracle: gold/unicodedata/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_unicodedata_q
docs:
  - "https://docs.python.org/3/library/unicodedata.html"
rfcs:
  []
---

# unicodedata

name(character) returns the Unicode character name. Latin capital letters use the form LATIN CAPITAL LETTER followed by the English letter name. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

name(character) returns the Unicode character name. Latin capital letters use the form LATIN CAPITAL LETTER followed by the English letter name.

## What is not in scope

Normalization, numeric values, and bidirectional categories.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
