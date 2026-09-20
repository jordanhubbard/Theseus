# Characterization before / after (2026-09-20)

Authoritative snapshots: [`characterization-baseline.json`](characterization-baseline.json) and [`characterization-after.json`](characterization-after.json).

## Where we were

| Metric | Baseline (`ca026dea`) |
|---|---|
| Product claim | characterization |
| Qualified packages | 0 |
| `gold/<family>/` trees | 32 |
| Intended qualification set | 17 |
| Characterization cohort | 15 (Phase 11) |
| Remaining high/medium public-API families without gold | 119 |
| Remaining high+deep `python_module` without gold | 11 (`copy`, `heapq`, `reprlib`, `statistics`, `enum`, `html_entities`, `weakref`, `html_parser`, `idna`, `textwrap`, `tomlkit`) |
| Registry packages | 396 (`ladder.product` = characterization) |
| Gold audit gaps | `libpcap` / `pcap` / `pcapng` have no `probes.yaml` (`live_probe` has no ctypes backend) |

Don't-do constraints in force: do not treat `status=verified` as replacement; do not add factory wrappers or registry packages; do not leak held-out tokens into public oracles; do not put behavioral fields on Layer 1 recipes.

## What ran (the 8-step loop, not the don'ts)

For each remaining high-feasibility `python_module` family, and for gold-audit gaps:

1. Pick the family.
2. Public docs / RFCs only (no implementation source).
3. Write `gold/<family>/package.md`.
4. Keep / repair the public-API ZSDL oracle (calls with arguments).
5. Confirm values with `tools/live_probe.py` where the backend exists.
6. Close `uncertainty.yaml` (`resolved` / `deferred` / `held_out` only).
7. `tools/characterize.py` (and `make characterize-gold`).
8. Honest ladder: `oracle_bound`, `qualification: none`.

ctypes families (`libpcap` / `pcap` / `pcapng`) already had authority + ledgers. The 8-step close for probes is a **deferred** ledger item: `live_probe` has no ctypes backend; the Layer 2 ctypes oracle remains the live check.

## Where we are

| Metric | After this pass |
|---|---|
| Product claim | characterization (unchanged) |
| Qualified packages | 0 (unchanged) |
| `gold/<family>/` trees | **51** |
| Intended qualification set | **17** (unchanged) |
| Characterization cohort | **34** |
| Remaining high/medium public-API families without gold | **100** |
| Remaining high-feasibility families without gold | **12**, all `node` and not in this repo's `package.json` |
| Remaining high+deep `python_module` without gold | **0** |
| Registry packages | **396** (unchanged) |
| Gold audit gaps | ctypes probe gap unchanged and now on the ledger; `uu` skipped on Python 3.13+ |

Added this pass (19 families): `copy`, `heapq`, `reprlib`, `statistics`, `enum`, `html_entities`, `weakref`, `html_parser`, `idna`, `textwrap`, `tomlkit`, `colorsys`, `copyreg`, `genericpath`, `glob`, `pathspec`, `quopri`, `uu`, `ulid`.

Oracle repairs required so step 7 could pass: enum (StrEnum 3.11+; Flag/StrEnum length via `_member_names_`); weakref (constructor + `__len__`, no `Foo().__len__` function names); glob (no `iglob('…').__class__` function names); quopri (`encodestring(b'hello')` is `b'hello'` — public docs do not require a trailing newline).

## Don't-do check

| Constraint | Evidence |
|---|---|
| Do not treat `status=verified` as replacement | `theseus_registry.json` `ladder.product` is still `characterization`; `ladder.qualified` is empty; README/ADR 0005 unchanged in claim |
| Do not add factory wrappers or registry packages | no `cleanroom/` or `theseus_*` factory files added; registry package count 396 → 396 |
| Do not leak held-out tokens into public oracles | new/edited zspecs do not contain JSON held-out tokens (`1.5e2`, `café`, `[1,]`, `\u0041`, `say "hi"`, `{]`) |
| Do not put behavioral fields on Layer 1 recipes | `schema/package-recipe.schema.json` not modified |

## Delta

- Gold trees: 32 → 51 (+19).
- Remaining high/medium public-API families: 119 → 100 (−19).
- Remaining high-feasibility Python: 11 high+deep + 7 high/moderate → 0.
- Remaining high-feasibility overall: 31 → 12 (npm only, and not listed in `package.json`: `base_x`, `card_validator`, `email_validator`, `graphlib`, `ieee754`, `isemail`, `jsonpointer`, `jsonschema`, `nanoid`, `punycode`, `semver_diff`, `unidecode`). `ulid` was already a repo dependency and is now characterized.
- Qualification: still 0. Characterization is still the product.

The 8-step loop is **not** finished for the corpus: 100 high/medium public-API families remain, including those 12 high-feasibility npm packages. This comparison is the checkpoint after remaining high-feasibility Python work plus installed `ulid`.
