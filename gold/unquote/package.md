---
family: unquote
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - unquote
public_oracle: zspecs/theseus_unquote_q.zspec.zsdl
blocks: urllib
cleanroom_oracle: zspecs/theseus_unquote_q.zspec.zsdl
held_out_oracle: gold/unquote/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_unquote_q
docs:
  - "https://docs.python.org/3/library/urllib.parse.html"
rfcs:
  []
---

# urllib.parse

unquote(string) percent-decodes a URL component. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

A percent sign followed by two hex digits becomes the corresponding byte, decoded as ASCII for these oracles. %20 is a space. Other encoded octets follow the same rule.

## What is not in scope

encoding and errors arguments, and plus-to-space translation.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
