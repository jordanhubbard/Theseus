---
family: shlex
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - split
  - quote
  - join
public_oracle: zspecs/shlex.zspec.zsdl
blocks: shlex
cleanroom_oracle: zspecs/theseus_shlex_q.zspec.zsdl
held_out_oracle: gold/shlex/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_shlex_q
docs:
  - https://docs.python.org/3/library/shlex.html
rfcs:
  []
---

# shlex

Simple lexical analysis for UNIX shell-like strings. split tokenizes; quote produces a safe token; join is the inverse of split for a list of words. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/shlex.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Quoted phrases, empty input, comments=True stripping, quote of spaces.

## What is not in scope

Full POSIX shell grammar, punctuation operators, Windows cmd escaping.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
