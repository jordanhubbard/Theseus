---
family: glob
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - glob
  - iglob
  - escape
public_oracle: zspecs/glob.zspec.zsdl
blocks: glob
cleanroom_oracle: zspecs/theseus_glob_q.zspec.zsdl
held_out_oracle: gold/glob/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_glob_q
docs:
  - "https://docs.python.org/3/library/glob.html"
rfcs:
  []
---

# glob

Unix-style pathname expansion. escape() quotes *, ?, and [ so they match literally. glob() of a nonexistent tree is []. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/glob.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

escape() of wildcard characters; glob() empty match on a path that cannot exist; literal /etc/hosts when present (POSIX CI).

## What is not in scope

iglob iterator concrete type (generator vs _GlobIter); recursive ** across filesystems; Windows drive globs.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
