---
family: html_parser
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - HTMLParser
public_oracle: zspecs/html_parser.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/html.parser.html"
rfcs:
  []
---

# html.parser

Event-driven HTML parser. HTMLParser.convert_charrefs defaults to True; getpos() is (1, 0) before feed. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/html_parser.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

HTMLParser class identity, convert_charrefs default, initial getpos.

## What is not in scope

Subclass callback sequences as a full tokenizer KAT; HTMLParseError (removed in 3.5).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
