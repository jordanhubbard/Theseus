---
name: characterize
description: >
  Run the Theseus gold-set characterization loop (ADR 0003): authority Markdown,
  uncertainty ledger, live probes, public oracle vs the installed library.
  Use when adding or reviewing gold/<family>/ artifacts. Does not qualify replacements.
metadata:
  version: "1.0.0"
  pinned: true
  theseus_adrs:
    - docs/decisions/0001-verification-ladder.md
    - docs/decisions/0003-characterization-loop.md
    - docs/decisions/0006-characterization-records.md
---

# Characterize a gold-set family

Theseus product work is **characterization**, not replacement ([ADR 0005](../../docs/decisions/0005-characterization-is-the-product.md)).

## When to use

- Adding `gold/<family>/package.md`, `uncertainty.yaml`, or `probes.yaml`
- Deepening `zspecs/<name>.zspec.zsdl` from public docs / RFCs
- Checking a family with `tools/characterize.py`

## Rules

1. Derive expected values from public docs and `tools/live_probe.py` against the **installed** library. Do not open implementation source (`mod.__file__`, CPython `Lib/`).
2. Frontmatter must include `family`, `public_oracle`, `ladder`, `qualification: none`.
3. Ledger items are `resolved`, `deferred`, or `held_out` only. `reviewed: true`.
4. Distinctive held-out tokens must not appear in the public Layer 2 oracle or in `package.md`.
5. Passing the public oracle is `oracle_bound`, not `qualified`.

## Commands

```bash
python3 tools/live_probe.py --from gold/<family>/probes.yaml
python3 tools/characterize.py <family>
make characterize-gold
```

## Record shape

`characterize.characterization_record(family)` projects frontmatter onto
`schema/characterization-record.schema.json` (not the Layer 1 recipe schema).
