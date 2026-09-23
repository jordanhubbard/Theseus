---
family: ctxvar
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ContextVar
public_oracle: zspecs/theseus_ctxvar_q.zspec.zsdl
blocks: contextvars
cleanroom_oracle: zspecs/theseus_ctxvar_q.zspec.zsdl
held_out_oracle: gold/ctxvar/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_ctxvar_q
docs:
  - "https://docs.python.org/3/library/contextvars.html"
rfcs:
  []
---

# contextvars

ContextVar(name, default=value).get() returns the default when unset. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

get() with no argument returns the default passed at construction.

## What is not in scope

set, reset, and Context objects.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
