---
family: functools
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - WRAPPER_ASSIGNMENTS
public_oracle: zspecs/functools.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/functools.html"
rfcs:
  []
---

# functools

__annotations__ is NOT in WRAPPER_ASSIGNMENTS on Python 3.14; it was replaced by __annotate__ and __type_params__. WRAPPER_UPDATES on Python 3.14 is a 1-tuple: ('__dict__',). CRITICAL — singledispatch.register must support THREE calling patterns: (1) @func.register(SomeType) — explicit type argument; (2) @func.register — used as a bare decorator, reads the type from the first parameter's annotation (PEP 484 / PEP 563); (3) func.register(SomeType, impl) — two-argument form. Pattern (2) must handle BOTH the case where the annotation is a live type object (e.g. str, int) AND where it is a forward-reference string (e.g. 'str') — the latter occurs when the calling module uses 'from __future__ import annotations'. Use typing.get_type_hints() to resolve string annotations. NEVER raise TypeError for a live type object like str or int. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/functools.zspec.zsdl`.

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
