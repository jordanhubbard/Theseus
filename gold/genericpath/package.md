---
family: genericpath
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - commonprefix
  - exists
  - isfile
  - isdir
  - getsize
public_oracle: zspecs/genericpath.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/os.path.html"
rfcs:
  []
---

# genericpath

Shared os.path helpers. Public documentation lives on os.path; commonprefix is a string operation that does not consult the filesystem. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/genericpath.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

os.path.commonprefix examples (empty, identical, partial, no common, path character prefix).

## What is not in scope

exists/isfile/isdir against a live filesystem; treating genericpath as a documented public module name.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
