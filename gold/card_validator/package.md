---
family: card_validator
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - number
  - expirationDate
  - cvv
public_oracle: zspecs/card_validator.zspec.zsdl
docs:
  - "https://github.com/braintree/card-validator#readme"
rfcs:
  - ISO/IEC 7812-1
---

# card_validator

Braintree PAN/brand/expiry/CVV checks. Visa test PAN 4111111111111111 is brand visa (Luhn-valid). This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/card_validator.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Brand inference for published Visa/Mastercard/Amex/Discover test PANs; Luhn isValid.

## What is not in scope

Live card networks; 3-D Secure.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
