---
family: pprint
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - pformat
  - saferepr
  - isreadable
  - isrecursive
public_oracle: zspecs/pprint.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/pprint.html"
rfcs:
  []
---

# pprint

Pretty-print Python objects as eval-able text when the values are fundamental types. pformat returns the string; sort_dicts defaults to True for pformat. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/pprint.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

pformat of ints/strs/None/bools/lists/dicts; isreadable; isrecursive of acyclic values; sort_dicts True vs False on a two-key dict.

## What is not in scope

Recursive structures (saferepr id text is not stable); PrettyPrinter stream writes; underscore_numbers (3.10+); dataclass / SimpleNamespace formatting.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
