---
family: html_entities
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - name2codepoint
  - codepoint2name
  - entitydefs
  - html5
public_oracle: zspecs/html_entities.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/html.entities.html"
  - "https://html.spec.whatwg.org/multipage/named-character-references.html"
rfcs:
  []
---

# html.entities

HTML entity name tables. name2codepoint['amp'] is 38. html5 keys include the trailing semicolon. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/html_entities.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

name2codepoint/codepoint2name/entitydefs/html5 for amp, lt, gt, quot.

## What is not in scope

The full HTML 5 named-character-reference table.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
