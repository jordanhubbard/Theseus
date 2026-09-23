---
family: datamode
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - mode
public_oracle: zspecs/theseus_datamode_q.zspec.zsdl
blocks: statistics
cleanroom_oracle: zspecs/theseus_datamode_q.zspec.zsdl
held_out_oracle: gold/datamode/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_datamode_q
docs:
  - "https://docs.python.org/3/library/statistics.html"
rfcs:
  []
---

# statistics

mode(data) is the most common value. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

mode returns the value that appears most often. The public sample has a single most common value.

## What is not in scope

Ties and multimodal data.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
