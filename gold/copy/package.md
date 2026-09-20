---
family: copy
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - copy
  - deepcopy
  - Error
public_oracle: zspecs/copy.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/copy.html"
rfcs:
  []
---

# copy

Shallow and deep copying. copy(x) duplicates the container but shares nested objects; deepcopy(x) copies recursively. Immutable scalars may be returned unchanged. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/copy.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

copy/deepcopy of JSON-serializable primitives and nested lists/dicts; Error class identity.

## What is not in scope

copy.replace (3.13+); custom __copy__/__deepcopy__; un-copyable objects (module, file).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
