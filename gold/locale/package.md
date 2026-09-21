---
family: locale
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - getpreferredencoding
  - LC_ALL
public_oracle: zspecs/locale.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/locale.html"
rfcs:
  []
---

# locale

locale.LC_ALL, LC_CTYPE, LC_NUMERIC, LC_TIME, LC_COLLATE, LC_MONETARY are integer constants whose exact values are platform-specific. All LC_* constants are plain Python int objects regardless of platform. locale.setlocale(locale.LC_ALL, '') resets to the environment locale; setlocale(locale.LC_ALL, 'C') uses the POSIX C locale. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/locale.zspec.zsdl`.

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
