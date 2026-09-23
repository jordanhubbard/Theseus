---
family: loggername
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - getLogger
public_oracle: zspecs/theseus_loggername_q.zspec.zsdl
blocks: logging
cleanroom_oracle: zspecs/theseus_loggername_q.zspec.zsdl
held_out_oracle: gold/loggername/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_loggername_q
docs:
  - "https://docs.python.org/3/library/logging.html"
rfcs:
  []
---

# logging

getLogger(name) returns a logger whose name attribute is that name. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

The name attribute equals the string passed to getLogger.

## What is not in scope

Levels, handlers, and propagation.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
