---
family: posixpath
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - join
  - split
  - basename
  - dirname
  - splitext
  - isabs
  - normpath
public_oracle: zspecs/posixpath.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/os.path.html"
rfcs:
  []
---

# posixpath

POSIX path semantics: '/' separator, isabs iff the path starts with '/', join restarts at an absolute component. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/posixpath.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Pure string operations: join, split, basename, dirname, splitext, isabs, normpath.

## What is not in scope

Filesystem probes (exists, isfile, isdir, abspath, expanduser); Windows vs POSIX case folding.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
