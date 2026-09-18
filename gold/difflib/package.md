---
family: difflib
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - SequenceMatcher
  - get_close_matches
  - IS_CHARACTER_JUNK
  - IS_LINE_JUNK
public_oracle: zspecs/difflib.zspec.zsdl
blocks: difflib
cleanroom_oracle: zspecs/theseus_difflib_q.zspec.zsdl
held_out_oracle: gold/difflib/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_difflib_q
docs:
  - https://docs.python.org/3/library/difflib.html
rfcs:
  []
---

# difflib

Sequence comparison helpers. Only exact ratios 0.0 and 1.0 are oracled so floating-point noise cannot masquerade as a spec. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/difflib.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

identical/disjoint/empty ratios, longest match indices, get_close_matches, junk predicates.

## What is not in scope

unified_diff/ndiff generators, HtmlDiff rendering, inexact mid-range ratios.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
