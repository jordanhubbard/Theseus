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

Regenerative replacement remains a **research protocol** (`tools/qualify.py`, ADR 0004). It is not advertised as a shipping capability. `ladder.product` in `theseus_registry.json` is `characterization`. `ladder.qualification_claim` stays `withdrawn`. `ladder.qualified` lists only packages with real dual-generation receipts. As of 2026-09-21 that is `theseus_base64_q`, `theseus_fnmatch_q`, `theseus_json`, `theseus_shlex_q`, `theseus_binascii_q`, `theseus_difflib_q`, `theseus_hashlib_q`, `theseus_hmac_q`, `theseus_struct_q`, `theseus_urllib_parse_q`, `theseus_bisect_q`, `theseus_colorsys_q`, `theseus_heapq_q`, `theseus_html_q`, `theseus_keyword_q`, `theseus_operator_q`, `theseus_quopri_q`, `theseus_textwrap_q`, `theseus_calendar_q`, `theseus_string_q`, `theseus_statistics_q`, `theseus_pprint_q`, `theseus_copy_q`, `theseus_fractions_q`, `theseus_glob_q`, `theseus_reprlib_q`, `theseus_getopt_q`, `theseus_ipaddress_q`, `theseus_mimetypes_q`, `theseus_itertools_q`, `theseus_posixpath_q`, `theseus_ntpath_q`, `theseus_contextlib_q`, `theseus_collections_q`, `theseus_datetime_q`, `theseus_csv_q`, `theseus_math_q`, `theseus_email_utils_q`, `theseus_decimal_q`, `theseus_codecs_q`, `theseus_array_q`, `theseus_re_q`, `theseus_io_q`, `theseus_pyuuid_q`, `theseus_pathlib_q`, `theseus_stat_q`, `theseus_http_cookies_q`, `theseus_ast_q`, `theseus_queue_q`, `theseus_secrets_q`, `theseus_types_q`, `theseus_time_q`, `theseus_deque_q`, `theseus_zlib_q`, `theseus_hexlify_q`, `theseus_xml_etree_q`, `theseus_wsgiref_q`, `theseus_unicodedata_q`, `theseus_cmath_q`, `theseus_pickle_q`, `theseus_adler32_q`, `theseus_close_matches_q`, `theseus_unhexlify_q`, `theseus_cleandoc_q`, `theseus_cmd_q`, `theseus_gettext_q`, `theseus_fnmatchcase_q`, `theseus_shorten_q`, `theseus_template_q`, `theseus_ordereddict_q`, `theseus_chainmap_q`, `theseus_threadlock_q`, `theseus_comb_q`, `theseus_perm_q`, `theseus_lcm_q`, `theseus_prod_q`, `theseus_hypot_q`, `theseus_isqrt_q`, `theseus_ceil_q`, `theseus_floor_q`, `theseus_indent_q`, `theseus_unquote_q`, `theseus_quoteplus_q`, `theseus_semaphore_q`, `theseus_stringio_q`, `theseus_tdelta_q`, `theseus_optionxform_q`, `theseus_usagefmt_q`, `theseus_b16encode_q`, `theseus_category_q`, `theseus_loggername_q`, `theseus_ctxvar_q`, `theseus_zipinfo_q`, `theseus_tarinfo_q`, `theseus_dist_q`, `theseus_trunc_q`, `theseus_fabs_q`, `theseus_copysign_q`, `theseus_medianlow_q`, `theseus_datamode_q`, `theseus_bisectleft_q`, and `theseus_nlargest_q` (102 of 102 attempts). The numeric kill gate is no longer fired. This decision still stands until a superseding ADR.

Layer 3 artifacts (factory wrappers, `theseus_*_q` attempts, isolation harness) stay in tree as evidence. They are not replacements.

## Consequences

- README, AGENTS.md, PLAN.md, and the user guide describe characterization first. Synthesis is historical / experimental.
- No package may be listed as `qualified` without ADR 0004 dual-generation.
- A later reversal requires new receipts with `independent_generation: true` for at least half of a ≥5 attempt set, plus a superseding ADR.

## Rejected alternatives

- Quietly treating "public + held-out passed once" as qualification.
- Dropping Layer 3 code; it is still useful isolation evidence.
- Continuing to market "verified rewrite ecosystem" language.
