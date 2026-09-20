---
family: copyreg
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - pickle
  - constructor
  - add_extension
  - remove_extension
  - clear_extension_cache
  - dispatch_table
public_oracle: zspecs/copyreg.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/copyreg.html"
rfcs:
  []
---

# copyreg

Pickle support registry: constructors, reduction functions, and opcode extension codes. dispatch_table maps types to reduce functions. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/copyreg.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Export names and that dispatch_table is a dict. clear_extension_cache() is a no-op when empty.

## What is not in scope

Registering custom reducers (process-global mutation); pickle opcode compacting.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
