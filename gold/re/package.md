---
family: re
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - escape
public_oracle: zspecs/theseus_re_q.zspec.zsdl
blocks: re
cleanroom_oracle: zspecs/theseus_re_q.zspec.zsdl
held_out_oracle: gold/re/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_re_q
docs:
  - "https://docs.python.org/3/library/re.html"
rfcs:
  []
---

# re

escape(pattern) backslash-escapes every character that is not an ASCII letter, digit, or underscore. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

escape(pattern) backslash-escapes every character that is not an ASCII letter, digit, or underscore.

## What is not in scope

Matching, compiling, and substitution.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
