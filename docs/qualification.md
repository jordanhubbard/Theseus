# Qualification loop

Phase 3 of the verification-ladder refresh ([ADR 0004](decisions/0004-qualification-protocol.md)).
This is how Theseus *attempts* regenerative replacement. It is **not** the product
([ADR 0005](decisions/0005-characterization-is-the-product.md)).

## Gate

A family is `qualified` only if:

1. The public clean-room oracle passes in isolation.
2. The held-out oracle passes in isolation.
3. `held_out_guard.py` finds no prompt leaks.
4. Input-closure hashes are recorded.
5. Two independent empty-workspace generations with **different** impl hashes both pass.

One generation cannot qualify a package. `tools/qualify.py` will record
`independent_generation: false` and `qualified: false`.

## Commands

```bash
python3 tools/qualify.py json
python3 tools/qualify.py --all
make qualify-check
```

Receipts: `reports/qualification/<family>.json` and `summary.json`.

Kill gate: if ≥5 families are attempted and fewer than half qualify, replacement
is not the product claim. That gate is no longer fired (12 qualified of 12 attempts). Replacement is still not the advertised product until ADR 0005 is superseded. Pass both generations with `python3 tools/qualify.py <family> --run1 <pkg-a> --run2 <pkg-b>`.
