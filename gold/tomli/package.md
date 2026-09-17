---
family: tomli
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
  - https://toml.io/en/v1.0.0
  - https://docs.python.org/3/library/tomllib.html
rfcs:
  []
---

# tomli

TOML 1.0.0 decoder. The Layer 2 spec is named tomli (the backport) but probes stdlib tomllib on Python 3.11+. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/tomli.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

scalars, arrays, tables, array-of-tables, TOMLDecodeError on invalid syntax.

## What is not in scope

dump/write (tomllib is read-only), dates/times timezone variants, inline nested dotted keys beyond the oracle.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
