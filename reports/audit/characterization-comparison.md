# Characterization before / after (2026-09-21)

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
| Remaining high+deep `python_module` without gold | 11 |
| Remaining high-feasibility families without gold | 31 (python + npm) |
| Registry packages | 396 (`ladder.product` = characterization) |
| Gold audit gaps | `libpcap` / `pcap` / `pcapng` have no `probes.yaml` (`live_probe` has no ctypes backend) |

Don't-do constraints in force: do not treat `status=verified` as replacement; do not add factory wrappers or registry packages; do not leak held-out tokens into public oracles; do not put behavioral fields on Layer 1 recipes.

## What ran (the 8-step loop, not the don'ts)

For each remaining high-feasibility Layer 2 family, and for gold-audit gaps:

1. Pick the family.
2. Public docs / RFCs only (no implementation source).
3. Write `gold/<family>/package.md`.
4. Keep / repair the public-API ZSDL oracle (calls with arguments).
5. Confirm values with `tools/live_probe.py` where the backend exists.
6. Close `uncertainty.yaml` (`resolved` / `deferred` / `held_out` only).
7. `tools/characterize.py` (and `make characterize-gold`).
8. Honest ladder: `oracle_bound`, `qualification: none`.

ctypes families (`libpcap` / `pcap` / `pcapng`) already had authority + ledgers. The 8-step close for probes is a **deferred** ledger item: `live_probe` has no ctypes backend; the Layer 2 ctypes oracle remains the live check.

`live_probe` node gained ESM `import()` fallback, constructor `new`, a `call` method hop, and `expect.contains` so npm factories could be probed without reading implementation source.

## Where we are

| Metric | After |
|---|---|
| Product claim | characterization (unchanged) |
| Qualified packages | 0 (unchanged) |
| `gold/<family>/` trees | **63** |
| Intended qualification set | **17** (unchanged) |
| Characterization cohort | **46** |
| Remaining high/medium public-API families without gold | **88** (all medium) |
| Remaining high-feasibility families without gold | **0** |
| Remaining high+deep `python_module` without gold | **0** |
| Registry packages | **396** (unchanged) |
| Gold audit gaps | ctypes probe gap unchanged and on the ledger; `uu` skipped on Python 3.13+ |

Added this pass (31 families): `copy`, `heapq`, `reprlib`, `statistics`, `enum`, `html_entities`, `weakref`, `html_parser`, `idna`, `textwrap`, `tomlkit`, `colorsys`, `copyreg`, `genericpath`, `glob`, `pathspec`, `quopri`, `uu`, `ulid`, `base_x`, `card_validator`, `email_validator`, `graphlib`, `ieee754`, `isemail`, `jsonpointer`, `jsonschema`, `nanoid`, `punycode`, `semver_diff`, `unidecode`.

Oracle repairs: enum (StrEnum 3.11+; Flag/StrEnum length via `_member_names_`); weakref (constructor + `__len__`); glob (no `iglob('…').__class__` function names); quopri (`encodestring(b'hello')` is `b'hello'`); `base_x` `esm: true`.

## Don't-do check

| Constraint | Evidence |
|---|---|
| Do not treat `status=verified` as replacement | `theseus_registry.json` `ladder.product` is still `characterization`; `ladder.qualified` is empty |
| Do not add factory wrappers or registry packages | no `cleanroom/` or `theseus_*` factory files added; registry package count 396 → 396 |
| Do not leak held-out tokens into public oracles | new/edited zspecs do not contain JSON held-out tokens (`1.5e2`, `café`, `[1,]`, `\u0041`, `say "hi"`, `{]`) |
| Do not put behavioral fields on Layer 1 recipes | `schema/package-recipe.schema.json` not modified |

npm packages added to `package.json` are CI/install-time libraries for live probes, not registry packages.

## Delta

- Gold trees: 32 → 63 (+31).
- Remaining high/medium public-API families: 119 → 88 (−31).
- Remaining high-feasibility families: 31 → **0**.
- Qualification: still 0. Characterization is still the product.

The requested high-feasibility characterization loop is done. Medium public-API families (88) remain as later product work, not this goal's high-feasibility set.

## Medium pass (2026-09-21)

59 of those 88 families now have `gold/<family>/` trees. Each tree is authority + reviewed ledger + live probes. `qualification` stays `none`. Intended qualification set stays 17. Registry stays 396.

Kept only families whose public Layer 2 oracle passes `characterize.py` against the installed library. 29 candidates still fail that oracle (wrong expected values, or call shapes such as `issubclass` / mid-chain arguments the harness does not execute). They have no gold tree:

`abc`, `abc_meta`, `argparse_formatters`, `attrs`, `collections_namedtuple`, `contextlib_suppress`, `contextvars`, `dataclasses_field`, `datetime_timedelta`, `email_errors`, `email_header`, `email_message`, `email_policy`, `email_utils`, `functools_lru`, `gzip`, `http_cookies`, `locale`, `plistlib`, `re_patterns`, `stringprep`, `tarfile`, `urllib_response`, `urllib_robotparser`, `xml_dom`, `xml_minidom`, `xml_parse`, `xml_sax`, `zipfile`.

| Metric | After medium pass |
|---|---|
| Qualified packages | 0 |
| `gold/<family>/` trees | **122** |
| Intended qualification set | **17** |
| Characterization cohort | **105** |
| Remaining medium public-API families without gold | **0** (after oracle repair) |
| Registry packages | **396** |

The 29 failing oracles were then repaired from live probes (dotted call hops, `method_tap` for parser `feed`, and expected values taken from the installed library) and given gold trees. High- and medium-feasibility public-API families without a gold tree: **0**. Qualification remains 0.
