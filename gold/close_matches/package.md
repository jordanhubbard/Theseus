---
family: close_matches
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - get_close_matches
public_oracle: zspecs/theseus_close_matches_q.zspec.zsdl
blocks: difflib
cleanroom_oracle: zspecs/theseus_close_matches_q.zspec.zsdl
held_out_oracle: gold/close_matches/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_close_matches_q
docs:
  - "https://docs.python.org/3/library/difflib.html"
rfcs:
  []
---

# difflib

get_close_matches(word, possibilities) returns close possibilities, best matches first. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

get_close_matches(word, possibilities) returns close possibilities, best matches first.

## What is not in scope

SequenceMatcher opcodes and HTML diffs.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
