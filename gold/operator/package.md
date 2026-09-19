---
family: operator
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - add
  - sub
  - mul
  - truediv
  - floordiv
  - lt
  - eq
  - not_
  - truth
  - contains
  - getitem
  - itemgetter
  - countOf
  - is_
  - is_not
public_oracle: zspecs/operator.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/operator.html"
rfcs:
  []
---

# operator

Function equivalents of Python's intrinsic operators. add(a, b) is a+b; contains(a, b) is b in a (reversed operands); itemgetter returns a callable __getitem__ extractor. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/operator.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Arithmetic, comparison, bitwise, logical, and sequence helpers; itemgetter / countOf / identity tests documented in the stdlib page.

## What is not in scope

In-place operators (iadd, ...); attrgetter / methodcaller dotted paths; operator.call (3.11+); is_none / is_not_none (3.14+).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
