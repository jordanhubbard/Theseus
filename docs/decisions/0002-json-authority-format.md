# ADR 0002: JSON Gold-Set Authority / Oracle / Held-Out Split

- Status: Accepted
- Date: 2026-09-17
- Decision owners: Theseus maintainers
- Depends on: [ADR 0001](0001-verification-ladder.md)
- Spike: [`gold/json/package.md`](../../gold/json/package.md)

## Context

ADR 0001 withdrew qualification claims and retired zero-argument invariant
wrappers as a product rule. Phase 1 needs one package in the new shape so later
phases are not inventing the format while also deepening oracles.

`cleanroom_verify.py` already calls `fn(*args)`. The zero-arg wrappers were an
authoring convention, not a harness limit. `theseus_json` still exported
`json_loads_int` so the spec could avoid calling `loads`.

## Decision

For the JSON gold-set spike, Theseus keeps three artifact classes:

1. **Authority** — `gold/json/package.md`. Markdown with typed frontmatter.
   Reviewable intent. Not executable.
2. **Public oracle** — `zspecs/json.zspec.zsdl` against installed `json`, and
   `zspecs/theseus_json.zspec.zsdl` against the clean-room implementation.
   Both call `dumps` / `loads` with arguments. The clean-room spec is allowed
   to use `JSONDecodeError` as the implementation's exception name.
3. **Held-out oracle** — `gold/json/held_out.zspec.zsdl`. Lives outside
   `zspecs/` so wave synthesis and `make compile-zsdl --all` do not ingest it.
   `tools/held_out_guard.py` fails if distinctive held-out tokens appear in a
   synthesis prompt built from the public clean-room spec.

The clean-room implementation exports the public API (`dumps`, `loads`,
`JSONDecodeError`) and must not export zero-arg self-test wrappers.

This spike does **not** mark JSON `qualified`. Isolation plus the public oracle
is still `legacy_isolation` while the registry `status` remains `verified`.
The held-out oracle is the missing piece for a later qualification run, not
qualification itself.

Zero-arg wrappers remain in other `theseus_*` factory specs until those
families are migrated. They are legacy, not the template for new gold-set work.

## Consequences

- `tools/cleanroom_verify.py` must honor `kwargs` and `python_call_raises`.
- AGENTS.md / `docs/cleanroom-spec-format.md` must stop teaching zero-arg
  wrappers as the only legal invariant shape.
- Regenerating `make corpus-autopsy` reclassifies `theseus_json` as
  `cleanroom_public_api` rather than `factory_shallow`.

## Rejected alternatives

**Keep wrappers and add a parallel public-API spec.** Rejected: the point of
the spike is that the implementation is graded on the API a user would call.

**Put held-out vectors in `zspecs/` with `skip_if: true`.** Rejected: anything
in `zspecs/` is compiled into wave synthesis by default.
