---
family: tdelta
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - timedelta
public_oracle: zspecs/theseus_tdelta_q.zspec.zsdl
blocks: datetime
cleanroom_oracle: zspecs/theseus_tdelta_q.zspec.zsdl
held_out_oracle: gold/tdelta/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_tdelta_q
docs:
  - "https://docs.python.org/3/library/datetime.html"
rfcs:
  []
---

# datetime

timedelta stores a duration as days, seconds, and microseconds. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

The days attribute is the normalized day count. Hours, minutes, seconds, milliseconds, and microseconds are normalized into that triple. One hour is 3600 seconds. A duration shorter than a day stays in the seconds attribute.

## What is not in scope

total_seconds, addition, and datetime arithmetic.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
