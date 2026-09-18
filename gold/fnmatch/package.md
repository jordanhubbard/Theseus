---
family: fnmatch
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - fnmatch
  - fnmatchcase
  - filter
  - translate
public_oracle: zspecs/fnmatch.zspec.zsdl
blocks: fnmatch
cleanroom_oracle: zspecs/theseus_fnmatch_q.zspec.zsdl
held_out_oracle: gold/fnmatch/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_fnmatch_q
docs:
  - https://docs.python.org/3/library/fnmatch.html
rfcs:
  []
---

# fnmatch

UNIX shell-style pattern matching against filenames. fnmatch follows OS case folding; fnmatchcase does not. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/fnmatch.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

*, ?, [seq], [!seq], empty names, filter, translate producing a regex string.

## What is not in scope

Windows vs POSIX case-folding of fnmatch() (use fnmatchcase in gold-set tests).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
