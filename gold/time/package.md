---
family: time
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - gmtime
public_oracle: zspecs/theseus_time_q.zspec.zsdl
blocks: time
cleanroom_oracle: zspecs/theseus_time_q.zspec.zsdl
held_out_oracle: gold/time/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_time_q
docs:
  - "https://docs.python.org/3/library/time.html"
rfcs:
  []
---

# time

gmtime(0) is the UTC epoch broken-down time. tm_year is the year. tm_mon is the 1-based month. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

gmtime(0) is the UTC epoch broken-down time. tm_year is the year. tm_mon is the 1-based month.

## What is not in scope

Local time, sleeping, and clocks that read the host.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
