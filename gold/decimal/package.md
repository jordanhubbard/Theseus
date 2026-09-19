---
family: decimal
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Decimal
  - getcontext
public_oracle: zspecs/decimal.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/decimal.html"
rfcs:
  - "IBM General Decimal Arithmetic Specification 1.72"
  - "IEEE 754-2019"
---

# decimal

Decimal floating-point with exact base-10 representation. Decimal('1.00') keeps trailing zeros; specials include Infinity and NaN; default context precision is 28. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/decimal.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Decimal from strings (including trailing zeros, Infinity, NaN, -0), predicates is_finite/is_nan/is_zero, default getcontext().prec == 28.

## What is not in scope

Signal traps, thread-local context mutation beyond reading default prec, comparison of NaN payloads, tuple constructor layout as a KAT.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
