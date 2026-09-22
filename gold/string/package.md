---
family: string
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ascii_lowercase
  - ascii_uppercase
  - ascii_letters
  - digits
  - hexdigits
  - octdigits
  - punctuation
  - whitespace
  - printable
  - capwords
public_oracle: zspecs/string.zspec.zsdl
blocks: string
cleanroom_oracle: zspecs/theseus_string_q.zspec.zsdl
held_out_oracle: gold/string/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_string_q
docs:
  - "https://docs.python.org/3/library/string.html"
rfcs:
  []
---

# string

ASCII character-class constants and capwords. Template substitution is a separate constructor and is out of scope here. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/string.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Lengths and membership of ascii_lowercase/uppercase/letters, digits, hexdigits, octdigits, punctuation, whitespace, printable; capwords including a custom separator.

## What is not in scope

string.Template / safe_substitute; Formatter; locale-dependent whitespace beyond the six ASCII characters named in the docs.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
