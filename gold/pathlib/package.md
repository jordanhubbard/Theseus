---
family: pathlib
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - PurePosixPath
public_oracle: zspecs/theseus_pathlib_q.zspec.zsdl
blocks: pathlib
cleanroom_oracle: zspecs/theseus_pathlib_q.zspec.zsdl
held_out_oracle: gold/pathlib/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_pathlib_q
docs:
  - "https://docs.python.org/3/library/pathlib.html"
rfcs:
  []
---

# pathlib

PurePosixPath(text).name is the final path component. PurePosixPath(text).suffix is the final dotted extension, including the dot, or an empty string when there is none. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

PurePosixPath(text).name is the final path component. PurePosixPath(text).suffix is the final dotted extension, including the dot, or an empty string when there is none.

## What is not in scope

Filesystem I/O methods and PureWindowsPath.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
