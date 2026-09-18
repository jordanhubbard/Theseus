# ADR 0004: Gold-Set Qualification Protocol

- Status: Accepted
- Date: 2026-09-18
- Decision owners: Theseus maintainers
- Depends on: [ADR 0001](0001-verification-ladder.md), [ADR 0002](0002-json-authority-format.md), [ADR 0003](0003-characterization-loop.md)

## Context

ADR 0001 split characterization from regenerative replacement and defined `qualified` as: held-out oracle passed, isolation held, protocol ran at least twice, original source not in the generator context. Phase 3 needed an executable protocol, not a slogan.

The factory `theseus_*` wrappers remain isolation evidence. They are not qualification oracles. New gold-set attempts use `theseus_<family>_q` packages (except JSON, which already grades `dumps`/`loads` on `theseus_json`) so the freeze of factory specs stays intact.

## Decision

### Attempt set

Attempt qualification for high-feasibility **Python** gold-set families that have:

- a reviewed `gold/<family>/` authority + ledger (ADR 0003)
- a public-API clean-room oracle (`zspecs/theseus_json.zspec.zsdl` or `zspecs/theseus_*_q.zspec.zsdl`)
- a held-out oracle under `gold/<family>/held_out.zspec.zsdl`
- a clean-room implementation path declared in frontmatter

Skip native/OS families (`pcap`, `libpcap`, `pcapng`) and Node families (`uuid`, `semver`) in this protocol. Skip `tomli`/`tomllib` until a public-API clean-room codec exists.

### Gate (all required)

`tools/qualify.py` writes `reports/qualification/<family>.json`. A family is `qualified` only if every item holds:

1. Public clean-room oracle passes under `cleanroom_verify.py` (original package blocked).
2. Held-out oracle passes under the same isolation.
3. `held_out_guard.py` finds no distinctive held-out tokens in the public-oracle synthesis prompt.
4. Input-closure hashes of authority, oracles, ledger, probes, and implementation are recorded.
5. **Two independent empty-workspace generations** produce different implementation hashes, and both pass (1)–(3).

A single generation — including an implementation written in the same session that authored the held-out file — sets `independent_generation: false` and **must not** set `qualified: true`.

### Kill gate

If at least five families are attempted and fewer than half reach `qualified`, regenerative replacement stops being the product claim. Characterization remains. That kill gate is [ADR 0005](0005-characterization-is-the-product.md).

### Commands

```bash
python3 tools/qualify.py json
python3 tools/qualify.py --all
make qualify-check
```

`gold/<family>/package.md` keeps `qualification: none` until dual-generation actually succeeds. Receipts carry the protocol bits; frontmatter does not launder a single pass into `qualified`.

## Consequences

- `theseus_*_q` specs are gold-set public-API oracles. Factory wrappers are frozen ([`reports/audit/factory-wrapper-freeze.json`](../../reports/audit/factory-wrapper-freeze.json)).
- Registry `status=verified` is still legacy isolation. `registry.is_qualified(name)` reads `ladder.qualified`.
- Held-out files stay outside `zspecs/` so `compile-zsdl --all` never feeds them to synthesis waves.

## Rejected alternatives

- Marking `qualified` after one isolated pass (repeats the factory mistake).
- Reusing factory wrapper specs as qualification oracles.
- Claiming Node/native families were attempted when no Python clean-room codec exists.
