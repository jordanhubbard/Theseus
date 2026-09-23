---
family: optionxform
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ConfigParser
public_oracle: zspecs/theseus_optionxform_q.zspec.zsdl
blocks: configparser
cleanroom_oracle: zspecs/theseus_optionxform_q.zspec.zsdl
held_out_oracle: gold/optionxform/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_optionxform_q
docs:
  - "https://docs.python.org/3/library/configparser.html"
rfcs:
  []
---

# configparser

ConfigParser.optionxform(name) transforms an option name before lookup. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

The default transform lowercases the name.

## What is not in scope

Reading files and interpolation.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
