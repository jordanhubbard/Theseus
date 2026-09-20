---
family: uu
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - encode
  - decode
  - Error
public_oracle: zspecs/uu.zspec.zsdl
docs:
  - "https://docs.python.org/3.11/library/uu.html"
rfcs:
  []
---

# uu

Unix-to-Unix encoding. Deprecated in 3.11 (PEP 594) and removed in 3.13. Characterization is for 3.9–3.12 only. Error subclasses Exception. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/uu.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Error class identity and encode/decode export names on Python < 3.13.

## What is not in scope

Round-trip file payloads; Python 3.13+ where the module does not exist.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
