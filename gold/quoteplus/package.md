---
family: quoteplus
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - quote_plus
public_oracle: zspecs/theseus_quoteplus_q.zspec.zsdl
blocks: urllib
cleanroom_oracle: zspecs/theseus_quoteplus_q.zspec.zsdl
held_out_oracle: gold/quoteplus/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_quoteplus_q
docs:
  - "https://docs.python.org/3/library/urllib.parse.html"
rfcs:
  []
---

# urllib.parse

quote_plus(string) percent-encodes a query component and turns spaces into plus signs. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Spaces become +. Letters and digits stay as themselves. A slash is percent-encoded as %2F. The result is a string.

## What is not in scope

a safe set other than the default, and bytes input.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
