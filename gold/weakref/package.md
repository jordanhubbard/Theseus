---
family: weakref
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - ref
  - proxy
  - getweakrefcount
  - getweakrefs
  - WeakValueDictionary
public_oracle: zspecs/weakref.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/weakref.html"
rfcs:
  []
---

# weakref

Weak references. getweakrefcount(obj) is 0 when nothing weakly refers to obj; Weak* maps start empty. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/weakref.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Class names; empty WeakValueDictionary; getweakrefs/getweakrefcount on a fresh list.

## What is not in scope

Callback firing; proxy AttributeError vs ReferenceError on dead objects as a full table; finalize.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
