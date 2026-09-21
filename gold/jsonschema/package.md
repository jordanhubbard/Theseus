---
family: jsonschema
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Validator
public_oracle: zspecs/jsonschema.zspec.zsdl
docs:
  - "https://github.com/tdegrunt/jsonschema#readme"
rfcs:
  - JSON Schema draft-07
---

# jsonschema

Pure-JS JSON Schema validator. new Validator().validate(42, {type:'integer'}) has an empty errors list. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/jsonschema.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

type: integer pass/fail; errors length when valid.

## What is not in scope

$ref remote loading; draft-2019-09/2020-12 exclusive features.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
