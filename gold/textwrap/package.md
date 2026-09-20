---
family: textwrap
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - wrap
  - fill
  - dedent
  - indent
  - shorten
public_oracle: zspecs/textwrap.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/textwrap.html"
rfcs:
  []
---

# textwrap

Paragraph wrapping. wrap returns a list of lines; fill joins them; empty input yields no lines. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/textwrap.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

wrap width splits, empty string, short string that fits, fill/dedent/indent as already oracled.

## What is not in scope

TextWrapper.break_long_words edge cases; expand_tabs interaction with locale.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
