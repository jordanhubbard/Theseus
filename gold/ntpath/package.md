---
family: ntpath
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - join
  - split
  - basename
  - dirname
  - splitdrive
  - splitext
  - isabs
  - normpath
public_oracle: zspecs/ntpath.zspec.zsdl
blocks: ntpath
cleanroom_oracle: zspecs/theseus_ntpath_q.zspec.zsdl
held_out_oracle: gold/ntpath/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_ntpath_q
docs:
  - "https://docs.python.org/3/library/os.path.html"
rfcs:
  []
---

# ntpath

Windows path semantics on every platform: backslash separator, drive letters, join that restarts at a rooted segment. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/ntpath.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Pure string operations: join, basename, dirname, splitdrive, splitext, isabs, normpath. Available on POSIX hosts.

## What is not in scope

Filesystem probes (exists, isfile, isdir, abspath, realpath); UNC share parsing edge cases.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
