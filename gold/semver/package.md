---
family: semver
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - valid
  - gt
  - lt
  - eq
  - compare
  - satisfies
  - inc
public_oracle: zspecs/semver.zspec.zsdl
docs:
  - https://semver.org/spec/v2.0.0.html
rfcs:
  []
---

# semver

Semantic Versioning 2.0.0 as implemented by npm's semver package. Invalid strings yield null, not throws. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/semver.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

valid/clean, compare/gt/lt/eq, caret ranges, prerelease precedence (1.0.0-alpha < 1.0.0), field extractors.

## What is not in scope

npm build-metadata (+) ordering quirks beyond SemVer 2.0.0, coerce().

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
