---
family: stat
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - filemode
public_oracle: zspecs/theseus_stat_q.zspec.zsdl
blocks: stat
cleanroom_oracle: zspecs/theseus_stat_q.zspec.zsdl
held_out_oracle: gold/stat/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_stat_q
docs:
  - "https://docs.python.org/3/library/stat.html"
rfcs:
  []
---

# stat

filemode(mode) returns the 10-character ls-style string for a st_mode integer: one type character and nine rwx permission characters. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

filemode(mode) returns the 10-character ls-style string for a st_mode integer: one type character and nine rwx permission characters.

## What is not in scope

S_IS* predicates on platform-specific stat results, and file-system queries.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
