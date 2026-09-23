---
family: template
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Template
public_oracle: zspecs/theseus_template_q.zspec.zsdl
blocks: string
cleanroom_oracle: zspecs/theseus_template_q.zspec.zsdl
held_out_oracle: gold/template/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_template_q
docs:
  - "https://docs.python.org/3/library/string.html"
rfcs:
  []
---

# string.Template

Template(template).substitute(mapping) replaces $identifiers from the mapping. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Template(template).substitute(mapping) replaces $identifiers from the mapping.

## What is not in scope

capwords, which is a separate clean-room surface, and safe_substitute.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
