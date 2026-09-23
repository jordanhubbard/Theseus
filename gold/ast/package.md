---
family: ast
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - literal_eval
public_oracle: zspecs/theseus_ast_q.zspec.zsdl
blocks: ast
cleanroom_oracle: zspecs/theseus_ast_q.zspec.zsdl
held_out_oracle: gold/ast/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_ast_q
docs:
  - "https://docs.python.org/3/library/ast.html"
rfcs:
  []
---

# ast

literal_eval(text) parses one Python literal: string, bytes, number, tuple, list, dict, set, True, False, or None. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

literal_eval(text) parses one Python literal: string, bytes, number, tuple, list, dict, set, True, False, or None.

## What is not in scope

Parsing arbitrary statements, compiling, and walking trees.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
