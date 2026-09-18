# ADR 0005: Characterization Is the Product

- Status: Accepted
- Date: 2026-09-18
- Decision owners: Theseus maintainers
- Depends on: [ADR 0001](0001-verification-ladder.md), [ADR 0004](0004-qualification-protocol.md)
- Evidence: [`reports/qualification/summary.json`](../../reports/qualification/summary.json)

## Context

ADR 0001 said: if fewer than half of an attempted gold set reach `qualified` after a held-out oracle protocol, replacement stops being the product claim. Phase 3 ran that protocol.

Ten Python families were attempted (`json`, `base64`, `binascii`, `difflib`, `fnmatch`, `hashlib`, `hmac`, `shlex`, `struct`, `urllib_parse`). Public and held-out oracles passed in isolation for those families. **Zero** packages had two independent empty-workspace generations. `independent_generation` is false on every receipt. `qualified` count is 0. The kill gate fired.

Native/Node/TOML families were skipped, not failed. Skips do not count as attempts.

## Decision

Theseus's **product** is Layer 2 characterization: reviewed authorities, uncertainty ledgers, live probes, and public-API oracles checked against the installed library.

Regenerative replacement remains a **research protocol** (`tools/qualify.py`, ADR 0004). It is not advertised as a shipping capability. `ladder.product` in `theseus_registry.json` is `characterization`. `ladder.qualification_claim` stays `withdrawn`. `ladder.qualified` stays empty until dual-generation is real.

Layer 3 artifacts (factory wrappers, `theseus_*_q` attempts, isolation harness) stay in tree as evidence. They are not replacements.

## Consequences

- README, AGENTS.md, PLAN.md, and the user guide describe characterization first. Synthesis is historical / experimental.
- No package may be listed as `qualified` without ADR 0004 dual-generation.
- A later reversal requires new receipts with `independent_generation: true` for at least half of a ≥5 attempt set, plus a superseding ADR.

## Rejected alternatives

- Quietly treating "public + held-out passed once" as qualification.
- Dropping Layer 3 code; it is still useful isolation evidence.
- Continuing to market "verified rewrite ecosystem" language.
