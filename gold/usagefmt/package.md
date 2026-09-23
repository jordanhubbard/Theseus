---
family: usagefmt
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ArgumentParser
public_oracle: zspecs/theseus_usagefmt_q.zspec.zsdl
blocks: argparse
cleanroom_oracle: zspecs/theseus_usagefmt_q.zspec.zsdl
held_out_oracle: gold/usagefmt/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_usagefmt_q
docs:
  - "https://docs.python.org/3/library/argparse.html"
rfcs:
  []
---

# argparse

ArgumentParser(prog).format_usage() renders the usage line. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

With no arguments added, the line is usage, a colon, a space, the program name, a space, [-h], and a newline.

## What is not in scope

Custom formatters, arguments, and help text.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
