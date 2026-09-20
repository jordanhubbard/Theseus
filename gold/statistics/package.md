---
family: statistics
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - mean
  - fmean
  - median
  - mode
  - variance
  - pvariance
  - StatisticsError
public_oracle: zspecs/statistics.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/statistics.html"
rfcs:
  []
---

# statistics

Numeric statistics. mean of [1,2,3,4,5] is 3; empty mean raises StatisticsError; geometric_mean([1,2,4]) is 2.0. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/statistics.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

mean/fmean/median/mode on small numeric lists; StatisticsError on empty mean and single-point sample variance.

## What is not in scope

NormalDist PDF tables; quantiles method variants; correlation.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
