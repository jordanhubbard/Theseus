# ADR 0003: Characterization Loop With Uncertainty Review

- Status: Accepted
- Date: 2026-09-17
- Decision owners: Theseus maintainers
- Depends on: [ADR 0001](0001-verification-ladder.md), [ADR 0002](0002-json-authority-format.md)
- Loop: [`docs/characterization-loop.md`](../characterization-loop.md)

## Context

ADR 0001 split Theseus into two products: characterization of installed OSS (corpus-scale) and regenerative replacement (gold set of tens). ADR 0002 spiked the three-artifact format on JSON. Phase 2 has to make characterization a repeatable loop, not a one-off JSON folder.

The failure mode to avoid is treating a passing Layer 2 spec as a finished description. A spec can match the installed library and still be incomplete, underspecified, or silently encoding implementation accidents. Live confirmation of public-API values is evidence. It is not a license to read implementation source into a generation prompt.

## Decision

### 1. The loop is documentation-first

For each intended gold-set family the loop is:

1. Draft from **public documentation and RFCs** into `gold/<family>/package.md` (authority) and `zspecs/<name>.zspec.zsdl` (public oracle).
2. Confirm expected values with **live probes** against the installed library (`tools/live_probe.py`). Probes import the public API as a black box. They do not open the module's `__file__`.
3. Record every unresolved, out-of-scope, or held-out claim in `gold/<family>/uncertainty.yaml`.
4. A human sets `reviewed: true` only when every ledger item is `resolved`, `deferred`, or `held_out`. There is no `open` status on an accepted ledger.
5. `tools/characterize.py` compiles and runs the public oracle, optional live probes, and (when declared) the clean-room + held-out pair plus `held_out_guard`.

Passing this loop does **not** mark a package `qualified`. Qualification remains ADR 0001's empty-workspace + held-out protocol (Phase 3).

### 2. Uncertainty ledger statuses

| Status | Meaning |
|---|---|
| `resolved` | The claim was decided from public docs and/or a live probe. The oracle encodes the decision. |
| `deferred` | Known gap, explicitly out of scope for this family. Not an open question. |
| `held_out` | Vectors exist but must not enter a synthesis prompt (ADR 0002). |

`open` is a draft-only status. `characterize.py` refuses a family whose ledger is unreviewed or contains a status outside that set.

### 3. Live probes vs implementation source

Live probes **may** `import` / `require` the installed library and call documented functions.

Live probes **must not** read implementation source (the file behind `mod.__file__`, CPython `Lib/`, npm package `.js` sources) for the purpose of writing oracles or generation prompts.

Inventory of quarantined source for later human review is a separate, explicit act. It is not this loop.

### 4. Gold-set Layer 2 depth

Phase 2 deepens the intended gold-set **Layer 2** oracles toward RFC/KAT completeness. That is characterization of the original. It is not a held-out replacement oracle (except JSON, which already has one from ADR 0002).

Alias families share an oracle: `tomllib` → `zspecs/tomli.zspec.zsdl`; `pcap` → `zspecs/libpcap.zspec.zsdl`. Duplicate ZSDL files would split the gold set.

### 5. Ladder interaction

| Artifact | Rung after this ADR |
|---|---|
| Gold family with accepted ledger + public-API oracle of moderate/deep quality | `characterized` (human review) **and** `oracle_bound` (mechanical Layer 2) |
| Other Layer 2 specs | Unchanged: mechanical `oracle_bound` or `characterized_draft` |
| Registry `status=verified` | Still `legacy_isolation` |

The autopsy records characterization as a **gold-tree** scan (`gold/<family>/`), not by rewriting every spec's mechanical ladder bit.

## Consequences

- `make characterize-gold` is the Phase 2 gate.
- New gold-set families copy `gold/json/` (authority + ledger + probes) rather than a factory `theseus_*` spec.
- Phase 3 may add held-out oracles for non-JSON families. Phase 2 does not claim those exist.

## Rejected alternatives

**Treat passing `verify_behavior` as characterization.** Rejected. That is oracle binding, not review.

**Read CPython/npm sources to fill RFC gaps.** Rejected for this loop. Public docs + live probes only.

**Promote gold families to `qualified` because the ledger is accepted.** Rejected. No empty-workspace regeneration ran.

## Follow-up

- Phase 3 — gold-set regenerative qualification (held-out oracles beyond JSON, empty workspace, twice). **Done; 0 qualified** ([ADR 0004](0004-qualification-protocol.md), [ADR 0005](0005-characterization-is-the-product.md)).
- Phase 11 — expand `gold/<family>/` characterization to the next high-feasibility Layer 2 cohort. **Done.** Not qualification.
- 2026-09-20 — remaining high-feasibility `python_module` and `node` families through the same loop. Remaining product work is medium-feasibility public-API specs. Not qualification.
- 2026-09-21 — 59 medium public-API families whose Layer 2 oracles pass the installed library. Not qualification.
- 2026-09-21 — repaired the remaining 29 medium oracles against the installed library (call hops, live expected values) and added their `gold/<family>/` trees. Remaining high/medium public-API families without a gold tree: 0. Not qualification.
