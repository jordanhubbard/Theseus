---
family: cmd
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Cmd
public_oracle: zspecs/theseus_cmd_q.zspec.zsdl
blocks: cmd
cleanroom_oracle: zspecs/theseus_cmd_q.zspec.zsdl
held_out_oracle: gold/cmd/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_cmd_q
docs:
  - "https://docs.python.org/3/library/cmd.html"
rfcs:
  []
---

# cmd

Cmd() starts with prompt '(Cmd) ' and intro None. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Cmd() starts with prompt '(Cmd) ' and intro None.

## What is not in scope

Command dispatch and the input loop.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
