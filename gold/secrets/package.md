---
family: secrets
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - compare_digest
public_oracle: zspecs/theseus_secrets_q.zspec.zsdl
blocks: secrets
cleanroom_oracle: zspecs/theseus_secrets_q.zspec.zsdl
held_out_oracle: gold/secrets/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_secrets_q
docs:
  - "https://docs.python.org/3/library/secrets.html"
rfcs:
  []
---

# secrets

compare_digest(a, b) returns true when the two strings or byte strings are equal and false when they differ. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

compare_digest(a, b) returns true when the two strings or byte strings are equal and false when they differ.

## What is not in scope

Token generation.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
