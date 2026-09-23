---
family: pickle
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - dumps
public_oracle: zspecs/theseus_pickle_q.zspec.zsdl
blocks: pickle
cleanroom_oracle: zspecs/theseus_pickle_q.zspec.zsdl
held_out_oracle: gold/pickle/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_pickle_q
docs:
  - "https://docs.python.org/3/library/pickle.html"
rfcs:
  []
---

# pickle

dumps(obj, protocol=0) returns a protocol-0 pickle. A one-element list of an int uses the protocol-0 list and integer opcodes. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

dumps(obj, protocol=0) returns a protocol-0 pickle. A one-element list of an int uses the protocol-0 list and integer opcodes.

## What is not in scope

Protocol 2 and later, persistent ids, and unpickling arbitrary classes.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
