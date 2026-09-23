---
family: csv
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - reader
  - excel
  - excel_tab
  - QUOTE_MINIMAL
  - list_dialects
public_oracle: zspecs/csv.zspec.zsdl
blocks: csv
cleanroom_oracle: zspecs/theseus_csv_q.zspec.zsdl
held_out_oracle: gold/csv/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_csv_q
docs:
  - "https://docs.python.org/3/library/csv.html"
rfcs:
  - "RFC 4180"
---

# csv

RFC 4180-shaped delimited text. reader parses rows from an iterable of strings; excel is the default dialect (comma, CRLF, QUOTE_MINIMAL). This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/csv.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

reader of simple/quoted/empty fields, excel delimiter/quotechar/lineterminator, QUOTE_MINIMAL==0, list_dialects contains 'excel'.

## What is not in scope

writer to real files; unix dialect lineterminator details; field_size_limit as a process-global mutation.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
