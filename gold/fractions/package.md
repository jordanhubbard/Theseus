---
family: fractions
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Fraction
public_oracle: zspecs/fractions.zspec.zsdl
blocks: fractions
cleanroom_oracle: zspecs/theseus_fractions_q.zspec.zsdl
held_out_oracle: gold/fractions/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_fractions_q
docs:
  - "https://docs.python.org/3/library/fractions.html"
rfcs:
  []
---

# fractions

Rational numbers stored in lowest terms. Fraction(2, 4) is 1/2; Fraction(1, 0) raises ZeroDivisionError; invalid strings raise ValueError. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/fractions.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Constructor from ints/strings, auto-reduction, __str__, ZeroDivisionError and ValueError, limit_denominator on a documented example if already in the oracle.

## What is not in scope

Float conversion accidents besides exact binary 0.5; arithmetic method_args carrying Fraction objects through JSON.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
