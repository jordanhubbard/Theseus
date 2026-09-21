---
family: punycode
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - toASCII
  - toUnicode
  - encode
  - decode
public_oracle: zspecs/punycode.zspec.zsdl
docs:
  - "https://www.npmjs.com/package/punycode"
rfcs:
  - RFC 3492
  - RFC 5891
---

# punycode

IDNA ASCII/Unicode conversion. toASCII('example.com') is unchanged; mañana.com becomes xn--maana-pta.com. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/punycode.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

toASCII/toUnicode of ASCII and two documented IDNA examples.

## What is not in scope

UTS #46 transitional mapping differences.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
