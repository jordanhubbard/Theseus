---
family: pathspec
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - PathSpec
  - lookup_pattern
public_oracle: zspecs/pathspec.zspec.zsdl
docs:
  - "https://python-path-specification.readthedocs.io/en/latest/"
rfcs:
  []
---

# pathspec

Gitignore-style path matching. PathSpec.from_lines(pattern_type, lines).match_file(path) is the characterization surface. gitignore pattern language: https://git-scm.com/docs/gitignore This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/pathspec.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

*.py / *.txt match_file; negation; src/ directory prefix; unknown pattern type raises KeyError.

## What is not in scope

GitWildMatchPattern.regex.pattern exact string (implementation regex); deprecated gitwildmatch vs gitignore naming beyond both working.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
