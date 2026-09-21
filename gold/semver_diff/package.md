---
family: semver_diff
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - default
public_oracle: zspecs/semver_diff.zspec.zsdl
docs:
  - "https://github.com/sindresorhus/semver-diff#readme"
  - "https://semver.org/spec/v2.0.0.html"
rfcs:
  []
---

# semver_diff

Classifies the SemVer delta between two versions. default('1.0.0','2.0.0') is major; equal versions yield undefined. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/semver_diff.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

major/minor/patch/pre* classification; undefined when equal or older.

## What is not in scope

Build-metadata (+) ordering beyond SemVer 2.0.0.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
