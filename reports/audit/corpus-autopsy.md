# Theseus Corpus Autopsy

Generated: `2026-09-17T22:28:56Z`
Schema: `theseus-corpus-autopsy/0.1`
Decision: [`docs/decisions/0001-verification-ladder.md`](../../docs/decisions/0001-verification-ladder.md)

This report classifies the existing ZSDL corpus and clean-room registry.
It does **not** claim any package is qualified. See ADR 0001.

## Headline

- **2299** source specs classified (0 compile errors).
- **396** registry packages with `status=verified` are **withdrawn from qualification**.
- **0** packages are `qualified`.
- **1010** specs look like public-API oracles of moderate/deep depth (Layer 2 asset).
- **178** specs match the 3-invariant clean-room factory (`factory_shallow`).
- Median invariant count: clean-room **3.0**, public-API **6.0**.
- **269** duplicate-wave families (same subject, `_cr` / `_cr2` / `_rust` suffixes).
- Registry names with no matching spec: `theseus_cProfile_cr`.

## Verification ladder (as applied to this corpus)

| Value | Count |
|---|---:|
| `oracle_bound` | 1010 |
| `inventoried` | 479 |
| `characterized_draft` | 415 |
| `legacy_isolation` | 395 |

Rungs are defined in ADR 0001. `legacy_isolation` is the old `verified` bit:
the implementation passed its listed invariants with the original package blocked.
That is not regenerative qualification.

## By backend

| Value | Count |
|---|---:|
| `node` | 1091 |
| `rust_module` | 479 |
| `python_cleanroom` | 394 |
| `python_module` | 318 |
| `ctypes` | 12 |
| `cli` | 4 |
| `node_cleanroom` | 1 |

## By oracle quality

| Value | Count |
|---|---:|
| `moderate` | 824 |
| `shallow` | 413 |
| `presence` | 367 |
| `wrapper` | 325 |
| `deep` | 187 |
| `factory_shallow` | 178 |
| `self_test` | 4 |
| `empty` | 1 |

## By contract shape

| Value | Count |
|---|---:|
| `public_api` | 1424 |
| `wrapper` | 479 |
| `self_test_wrapper` | 393 |
| `cleanroom_public_api` | 2 |
| `presence` | 1 |

## By replacement feasibility

| Value | Count |
|---|---:|
| `needs_review` | 1265 |
| `wrapper` | 479 |
| `medium` | 191 |
| `high` | 175 |
| `os_binding` | 79 |
| `stdlib_interpreter` | 71 |
| `native_core` | 29 |
| `infeasible` | 10 |

## Exhibits

- `json`: backend `python_module`, 22 invariants, oracle `deep`, contract `public_api`, ladder `oracle_bound`
- `theseus_json`: backend `python_cleanroom`, 22 invariants, oracle `deep`, contract `cleanroom_public_api`, ladder `legacy_isolation`
- `theseus_antigravity_cr`: backend `python_cleanroom`, 3 invariants, oracle `presence`, contract `self_test_wrapper`, ladder `legacy_isolation`
- `hashlib`: backend `python_module`, 41 invariants, oracle `deep`, contract `public_api`, ladder `oracle_bound`
- `semver`: backend `node`, 24 invariants, oracle `deep`, contract `public_api`, ladder `oracle_bound`

`json` (Layer 2, public-API oracle) is the gold-set characterization exhibit.
`theseus_json` was the Phase 0 factory-wrapper exhibit; ADR 0002 re-grades it on
`dumps`/`loads` (`cleanroom_public_api`). Other `theseus_*` factory specs are unchanged.
`theseus_antigravity_cr` is the exhibit that `expected: true` plus isolation is not a package.

## Gold-set candidates (current Layer 2 oracles)

These are **not** qualified. They are public-API specs whose current oracle depth
and feasibility class make them the starting set for Phase 3, if Phase 1–2 succeed.
The intended gold-set families are: `base64, binascii, difflib, fnmatch, hashlib, hmac, json, libpcap, pcap, pcapng, semver, shlex, struct, tomli, tomllib, urllib_parse, uuid`.

- `struct` *(intended)* — 45 invariants, `deep`, feasibility `high`, backend `python_module`
- `hashlib` *(intended)* — 41 invariants, `deep`, feasibility `high`, backend `python_module`
- `fnmatch` *(intended)* — 37 invariants, `deep`, feasibility `high`, backend `python_module`
- `semver` *(intended)* — 24 invariants, `deep`, feasibility `high`, backend `node`
- `difflib` *(intended)* — 23 invariants, `deep`, feasibility `high`, backend `python_module`
- `shlex` *(intended)* — 23 invariants, `deep`, feasibility `high`, backend `python_module`
- `json` *(intended)* — 22 invariants, `deep`, feasibility `high`, backend `python_module`
- `libpcap` *(intended)* — 22 invariants, `deep`, feasibility `high`, backend `ctypes`
- `tomli` *(intended)* — 22 invariants, `deep`, feasibility `high`, backend `python_module`
- `base64` *(intended)* — 20 invariants, `deep`, feasibility `high`, backend `python_module`
- `hmac` *(intended)* — 20 invariants, `deep`, feasibility `high`, backend `python_module`
- `urllib_parse` *(intended)* — 18 invariants, `deep`, feasibility `high`, backend `python_module`
- `uuid` *(intended)* — 18 invariants, `deep`, feasibility `high`, backend `node`
- `binascii` *(intended)* — 16 invariants, `deep`, feasibility `high`, backend `python_module`
- `pcapng` *(intended)* — 13 invariants, `moderate`, feasibility `high`, backend `ctypes`
- `logging` — 39 invariants, `deep`, feasibility `medium`, backend `python_module`
- `mimetypes` — 37 invariants, `deep`, feasibility `medium`, backend `python_module`
- `operator` — 37 invariants, `deep`, feasibility `high`, backend `python_module`
- `pprint` — 37 invariants, `deep`, feasibility `high`, backend `python_module`
- `html` — 32 invariants, `deep`, feasibility `high`, backend `python_module`
- `msgpack` — 32 invariants, `deep`, feasibility `high`, backend `python_module`
- `ntpath` — 32 invariants, `deep`, feasibility `high`, backend `python_module`
- `bisect` — 31 invariants, `deep`, feasibility `high`, backend `python_module`
- `codecs` — 31 invariants, `deep`, feasibility `medium`, backend `python_module`
- `logging_handlers` — 31 invariants, `deep`, feasibility `medium`, backend `python_module`
- `collections_abc` — 30 invariants, `deep`, feasibility `medium`, backend `python_module`
- `datetime` — 30 invariants, `deep`, feasibility `medium`, backend `python_module`
- `ipaddress` — 30 invariants, `deep`, feasibility `high`, backend `python_module`
- `posixpath` — 30 invariants, `deep`, feasibility `high`, backend `python_module`
- `collections` — 29 invariants, `deep`, feasibility `medium`, backend `python_module`
- `decimal` — 29 invariants, `deep`, feasibility `high`, backend `python_module`
- `xml_dom` — 29 invariants, `deep`, feasibility `medium`, backend `python_module`
- `keyword` — 28 invariants, `deep`, feasibility `high`, backend `python_module`
- `string` — 28 invariants, `deep`, feasibility `high`, backend `python_module`
- `calendar` — 27 invariants, `deep`, feasibility `high`, backend `python_module`
- `http_client` — 27 invariants, `deep`, feasibility `medium`, backend `python_module`
- `fractions` — 26 invariants, `deep`, feasibility `high`, backend `python_module`
- `io` — 26 invariants, `deep`, feasibility `medium`, backend `python_module`
- `csv` — 25 invariants, `deep`, feasibility `high`, backend `python_module`
- `elementtree` — 25 invariants, `deep`, feasibility `high`, backend `python_module`
- … 109 more in `corpus-autopsy.json`

## Largest duplicate-wave families

- `pathlib` (11) — `pathlib`, `pathlib_extra2_rust`, `pathlib_extra_rust`, `pathlib_rust`, `theseus_pathlib`, `theseus_pathlib_cr`, `theseus_pathlib_cr2`, `theseus_pathlib_cr3`, `theseus_pathlib_cr4`, `theseus_pathlib_cr5`, `theseus_pathlib_extra_cr`
- `json` (10) — `json`, `json_extra2_rust`, `json_extra_rust`, `json_rust`, `theseus_json`, `theseus_json_cr`, `theseus_json_cr2`, `theseus_json_cr3`, `theseus_json_cr4`, `theseus_json_cr5`
- `math` (9) — `math`, `math_extra_rust`, `math_rust`, `theseus_math`, `theseus_math_cr`, `theseus_math_cr2`, `theseus_math_cr3`, `theseus_math_cr4`, `theseus_math_cr5`
- `re` (9) — `re`, `re_extra_rust`, `re_rust`, `theseus_re`, `theseus_re_cr`, `theseus_re_cr2`, `theseus_re_cr3`, `theseus_re_cr4`, `theseus_re_cr5`
- `collections` (8) — `collections`, `collections_extra_rust`, `collections_rust`, `theseus_collections_cr`, `theseus_collections_cr2`, `theseus_collections_cr3`, `theseus_collections_cr4`, `theseus_collections_cr5`
- `contextlib` (8) — `contextlib`, `contextlib_extra_rust`, `contextlib_rust`, `theseus_contextlib`, `theseus_contextlib_cr`, `theseus_contextlib_cr2`, `theseus_contextlib_cr3`, `theseus_contextlib_cr4`
- `functools` (8) — `functools`, `functools_extra_rust`, `functools_rust`, `theseus_functools_cr`, `theseus_functools_cr2`, `theseus_functools_cr3`, `theseus_functools_cr4`, `theseus_functools_cr5`
- `io` (8) — `io`, `io_extra2_rust`, `io_extra_rust`, `io_rust`, `theseus_io_cr`, `theseus_io_cr2`, `theseus_io_cr3`, `theseus_io_cr4`
- `statistics` (8) — `statistics`, `statistics_extra2_rust`, `statistics_extra_rust`, `statistics_rust`, `theseus_statistics`, `theseus_statistics_cr`, `theseus_statistics_cr2`, `theseus_statistics_cr3`
- `struct` (8) — `struct`, `struct_rust`, `theseus_struct`, `theseus_struct_cr`, `theseus_struct_cr2`, `theseus_struct_cr3`, `theseus_struct_cr4`, `theseus_struct_extra_cr`
- `urllib_parse` (8) — `theseus_urllib_parse`, `theseus_urllib_parse_cr`, `theseus_urllib_parse_cr2`, `theseus_urllib_parse_cr3`, `theseus_urllib_parse_cr4`, `urllib_parse`, `urllib_parse_extra_rust`, `urllib_parse_rust`
- `base64` (7) — `base64`, `base64_rust`, `theseus_base64`, `theseus_base64_cr`, `theseus_base64_cr2`, `theseus_base64_cr3`, `theseus_base64_cr4`
- `csv` (7) — `csv`, `csv_extra_rust`, `csv_rust`, `theseus_csv`, `theseus_csv_cr`, `theseus_csv_cr2`, `theseus_csv_cr3`
- `decimal` (7) — `decimal`, `decimal_rust`, `theseus_decimal`, `theseus_decimal_cr`, `theseus_decimal_cr2`, `theseus_decimal_cr3`, `theseus_decimal_cr4`
- `enum` (7) — `enum`, `enum_extra_rust`, `enum_rust`, `theseus_enum_cr`, `theseus_enum_cr2`, `theseus_enum_cr3`, `theseus_enum_cr4`
- `itertools` (7) — `itertools`, `itertools_extra_rust`, `itertools_rust`, `theseus_itertools_cr`, `theseus_itertools_cr2`, `theseus_itertools_cr3`, `theseus_itertools_cr4`
- `operator` (7) — `operator`, `operator_extra_rust`, `operator_rust`, `theseus_operator`, `theseus_operator_cr`, `theseus_operator_cr2`, `theseus_operator_cr3`
- `textwrap` (7) — `textwrap`, `textwrap_extra_rust`, `textwrap_rust`, `theseus_textwrap`, `theseus_textwrap_cr`, `theseus_textwrap_cr2`, `theseus_textwrap_cr3`
- `weakref` (7) — `theseus_weakref`, `theseus_weakref_cr`, `theseus_weakref_cr2`, `theseus_weakref_extra_cr`, `weakref`, `weakref_extra_rust`, `weakref_rust`
- `array` (6) — `array`, `array_extra_rust`, `array_rust`, `theseus_array_cr`, `theseus_array_cr2`, `theseus_array_cr3`
- `bisect` (6) — `bisect`, `bisect_extra_rust`, `bisect_rust`, `theseus_bisect`, `theseus_bisect_cr`, `theseus_bisect_cr2`
- `calendar` (6) — `calendar`, `calendar_extra_rust`, `calendar_rust`, `theseus_calendar`, `theseus_calendar_cr`, `theseus_calendar_cr2`
- `dataclasses` (6) — `dataclasses`, `dataclasses_extra_rust`, `dataclasses_rust`, `theseus_dataclasses_cr`, `theseus_dataclasses_cr2`, `theseus_dataclasses_cr3`
- `difflib` (6) — `difflib`, `difflib_extra_rust`, `difflib_rust`, `theseus_difflib`, `theseus_difflib_cr`, `theseus_difflib_cr2`
- `fnmatch` (6) — `fnmatch`, `fnmatch_extra_rust`, `fnmatch_rust`, `theseus_fnmatch`, `theseus_fnmatch_cr`, `theseus_fnmatch_cr2`

## Withdrawn qualification list

Machine-readable file: [`withdrawn-verified.json`](withdrawn-verified.json).
Every registry package whose `status` is `verified` is listed there as `legacy_isolation`.
Count: **396**.

## Compile errors

- none

## Regenerating

```bash
make corpus-autopsy
```

