---
family: markdown_it
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - markdown_it
public_oracle: zspecs/markdown_it.zspec.zsdl
docs:
  - "https://markdown-it.github.io/"
  - "https://github.com/markdown-it/markdown-it#readme"
  - "https://spec.commonmark.org/"
rfcs:
  []
---

# markdown_it

markdown-it is the dominant CommonMark parser for Node.js. Usage: const MarkdownIt = require('markdown-it'); MarkdownIt().render(md) -> html string. Default options: html=false (escapes raw HTML), breaks=false, typographer=false. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/markdown_it.zspec.zsdl`.

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
