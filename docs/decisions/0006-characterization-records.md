# ADR 0006: Characterization Records Are Not Package Recipes

- Status: Accepted
- Date: 2026-09-18
- Decision owners: Theseus maintainers
- Depends on: [ADR 0001](0001-verification-ladder.md), [ADR 0003](0003-characterization-loop.md)

## Context

Layer 1 canonical records (`schema/package-recipe.schema.json`) describe how to **fetch and build** a package: identity, dependencies, provenance of the importer. Layer 2 gold-set work describes how a library **behaves**: authority Markdown, oracles, uncertainty. Stuffing behavioral fields into the recipe schema would mix two questions and force a recipe version bump for characterization.

## Decision

A **characterization record** is a separate JSON document, schema [`schema/characterization-record.schema.json`](../../schema/characterization-record.schema.json).

It is a projection of `gold/<family>/package.md` frontmatter plus ledger/probe paths. It does not replace ZSDL. It does not replace the recipe schema. `tools/characterize.py` builds one in memory via `characterization_record(family)`.

Required fields: `schema_version`, `kind` (`characterization_record`), `family`, `authority`, `public_oracle`, `ladder`, `qualification`, `uncertainty_ledger`.

Optional: `cleanroom_oracle`, `held_out_oracle`, `implementation`, `probes`, `blocks`, `exports`, `docs`, `rfcs`.

`qualification` on the record is the authority's claim (`none` today). Protocol results live in `reports/qualification/`, not in this record.

## Consequences

- Recipe `schema_version` stays `0.2`. Characterization evolution does not bump it.
- Agents should not invent recipe fields such as `behavioral_invariants` on Layer 1 records.
- Gold-set families can be listed and compared without compiling ZSDL.

## Rejected alternatives

- Extending `package-recipe.schema.json` with oracle paths.
- Treating compiled `_build/zspecs/*.json` as the characterization record (those are evidence, not authority).
