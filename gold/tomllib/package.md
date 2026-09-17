---
family: tomllib
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - loads
  - load
  - TOMLDecodeError
public_oracle: zspecs/tomli.zspec.zsdl
docs:
  - https://docs.python.org/3/library/tomllib.html
rfcs:
  []
---

# tomllib

Alias family: Python 3.11+ tomllib is the stdlib packaging of tomli. The executable oracle is zspecs/tomli.zspec.zsdl. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/tomli.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Same as the tomli family.

## What is not in scope

A second duplicate ZSDL named tomllib would split the gold set; do not add one.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
