---
family: tomlkit
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - loads
  - dumps
  - parse
  - document
public_oracle: zspecs/tomlkit.zspec.zsdl
docs:
  - "https://tomlkit.readthedocs.io/en/latest/"
  - "https://toml.io/en/v1.0.0"
rfcs:
  []
---

# tomlkit

TOML 1.0 codec that preserves formatting. loads('a = 42')['a'] is 42. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/tomlkit.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

loads of TOML 1.0 scalars and empty document; dumps roundtrip of simple keys as already oracled.

## What is not in scope

Comment/whitespace preservation KATs beyond simple roundtrip; datetime offsets.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
