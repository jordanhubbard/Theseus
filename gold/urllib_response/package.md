---
family: urllib_response
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - addinfourl
  - addbase
public_oracle: zspecs/urllib_response.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/urllib.response.html"
rfcs:
  []
---

# urllib_response

urllib.response is a small internal module exposing response wrapper classes used by urllib.request. addbase is the base wrapper class that wraps a file-like object and delegates read/readline/readlines. addinfourl wraps an underlying response with headers (info) and a URL; it inherits from addbase. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/urllib_response.zspec.zsdl`.

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
