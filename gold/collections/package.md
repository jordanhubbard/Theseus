---
family: collections
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Counter
public_oracle: zspecs/collections.zspec.zsdl
blocks: collections
cleanroom_oracle: zspecs/theseus_collections_q.zspec.zsdl
held_out_oracle: gold/collections/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_collections_q
docs:
  - "https://docs.python.org/3/library/collections.html"
rfcs:
  []
---

# collections

Counter is a dict subclass for counting hashable objects. Missing keys return 0 rather than raising KeyError. Counter('aabbc') counts characters: a=2, b=2, c=1. total() (Python 3.10+) returns sum of all counts. Counter.most_common(n) returns a list of (element, count) tuples sorted by count descending. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/collections.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

The live probes in `probes.yaml`, confirmed against the installed library. The rest of the public contract stays in the Layer 2 oracle.

## What is not in scope

I/O, process-global configuration, and error paths that the probes do not call. No held-out oracle and no clean-room attempt.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
