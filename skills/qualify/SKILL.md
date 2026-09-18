---
name: qualify
description: >
  Run the Theseus gold-set qualification protocol (ADR 0004). Use when attempting
  regenerative replacement against a held-out oracle. Never mark qualified after
  a single generation. Kill gate: fewer than half of ≥5 attempts means
  characterization stays the product (ADR 0005).
metadata:
  version: "1.0.0"
  pinned: true
  theseus_adrs:
    - docs/decisions/0001-verification-ladder.md
    - docs/decisions/0004-qualification-protocol.md
    - docs/decisions/0005-characterization-is-the-product.md
---

# Qualify a gold-set family

Qualification is a research protocol, not the shipping product.

## When to use

- A family already has characterized authority + public oracle + held-out oracle + implementation
- You are running `tools/qualify.py` or interpreting receipts under `reports/qualification/`

## Hard rules

1. **Never** set `qualified: true` unless `independent_generation` is true (two empty-workspace gens, different impl hashes, both pass public + held-out + isolation + held_out_guard).
2. Do not copy factory `theseus_*` zero-arg wrappers. Gold-set oracles call the public API with arguments (`theseus_json`, `theseus_*_q`).
3. Do not put held-out vectors in `zspecs/` public files or in synthesis prompts.
4. Keep `gold/<family>/package.md` `qualification: none` until dual-generation actually happens.
5. If ≥5 families are attempted and fewer than half qualify, do not advertise replacement. Characterization remains the product.

## Commands

```bash
python3 tools/qualify.py <family>
python3 tools/qualify.py --all
make qualify-check
python3 tools/lint_gold_wrappers.py
```

## Receipts

Each family writes `reports/qualification/<family>.json`. Summary and kill-gate bit: `reports/qualification/summary.json`.
