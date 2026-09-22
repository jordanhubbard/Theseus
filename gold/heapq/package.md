---
family: heapq
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - nlargest
  - nsmallest
  - heapify
  - heappush
  - heappop
public_oracle: zspecs/heapq.zspec.zsdl
blocks: heapq
cleanroom_oracle: zspecs/theseus_heapq_q.zspec.zsdl
held_out_oracle: gold/heapq/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_heapq_q
docs:
  - "https://docs.python.org/3/library/heapq.html"
rfcs:
  []
---

# heapq

Min-heap algorithms over lists. nlargest/nsmallest are the stateless public helpers; heappush/heappop mutate in place. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/heapq.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

nlargest and nsmallest including n=0, n>len, duplicates.

## What is not in scope

In-place heapify/heappush/heappop mutation as a single-shot oracle; merge generators.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
