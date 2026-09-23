---
family: fnmatchcase
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - fnmatch
  - fnmatchcase
public_oracle: zspecs/theseus_fnmatchcase_q.zspec.zsdl
blocks: fnmatch
cleanroom_oracle: zspecs/theseus_fnmatchcase_q.zspec.zsdl
held_out_oracle: gold/fnmatchcase/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_fnmatchcase_q
docs:
  - "https://docs.python.org/3/library/fnmatch.html"
rfcs:
  []
---

# fnmatch

fnmatch(name, pat) matches a filename against a shell pattern. fnmatchcase is the case-sensitive form. * matches any sequence. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

fnmatch(name, pat) matches a filename against a shell pattern. fnmatchcase is the case-sensitive form. * matches any sequence.

## What is not in scope

Filesystem listing.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
