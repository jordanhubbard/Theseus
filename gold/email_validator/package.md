---
family: email_validator
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - validate
public_oracle: zspecs/email_validator.zspec.zsdl
docs:
  - "https://github.com/manishsaraan/email-validator#readme"
rfcs:
  []
---

# email_validator

Lightweight email-syntax predicate. validate('a@b.com') is true; missing '@' is false. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/email_validator.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Documented boolean examples: simple valid, plus-tag, missing at, empty string.

## What is not in scope

SMTP mailbox existence; full RFC 5322.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
