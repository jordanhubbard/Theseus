---
family: keyword
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - iskeyword
  - issoftkeyword
  - kwlist
  - softkwlist
public_oracle: zspecs/keyword.zspec.zsdl
blocks: keyword
cleanroom_oracle: zspecs/theseus_keyword_q.zspec.zsdl
held_out_oracle: gold/keyword/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_keyword_q
docs:
  - "https://docs.python.org/3/library/keyword.html"
rfcs:
  []
---

# keyword

Test whether a string is a Python hard keyword or soft keyword. kwlist is the interpreter's hard-keyword sequence. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/keyword.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

iskeyword for hard keywords (for, def, None, …) and non-keywords (print, match); kwlist contains 'for'; issoftkeyword for match/case/type on Python 3.12+.

## What is not in scope

Exact kwlist length (version-dependent); encoding of iskeyword on non-str types; '_' as a soft keyword on older 3.x.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
