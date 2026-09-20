---
family: colorsys
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - rgb_to_hsv
  - hsv_to_rgb
  - rgb_to_hls
  - hls_to_rgb
  - rgb_to_yiq
  - yiq_to_rgb
public_oracle: zspecs/colorsys.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/colorsys.html"
rfcs:
  []
---

# colorsys

Conversions among RGB, YIQ, HLS, and HSV. Components are floats in [0.0, 1.0] except YIQ I/Q which may be negative. Python's Y coefficient for red is 0.30, not ITU-R BT.601 0.299. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/colorsys.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Primary-color conversions documented on docs.python.org (red HSV, red/white HLS, red YIQ luma).

## What is not in scope

ICC profiles; display-referred color; round-trip float fuzz beyond the documented primaries.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
