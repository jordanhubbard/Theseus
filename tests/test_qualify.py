"""Qualification protocol (ADR 0004) and kill gate (ADR 0005)."""
from __future__ import annotations

import json
from pathlib import Path

import qualify
import registry

ROOT = Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / "reports" / "qualification"


def test_summarize_kill_gate_fires_when_none_qualify():
    receipts = [
        {"family": "a", "attempted": True, "skipped": False, "qualified": False},
        {"family": "b", "attempted": True, "skipped": False, "qualified": False},
        {"family": "c", "attempted": True, "skipped": False, "qualified": False},
        {"family": "d", "attempted": True, "skipped": False, "qualified": False},
        {"family": "e", "attempted": True, "skipped": False, "qualified": False},
        {"family": "skip", "attempted": False, "skipped": True, "reason": "native"},
    ]
    summary = qualify.summarize(receipts)
    assert summary["attempted"] == 5
    assert summary["qualified"] == 0
    assert summary["kill_gate"]["fired"] is True
    assert summary["kill_gate"]["product_claim"] == "characterization"
    assert qualify.check_receipts(summary, receipts) == []


def test_check_rejects_qualified_without_empty_workspace_pair():
    receipts = [
        {
            "family": "json",
            "attempted": True,
            "skipped": False,
            "qualified": True,
            "independent_generation": True,
            "empty_workspace_pair": False,
            "held_out_guard": {"pass": True},
        }
    ]
    summary = {
        "attempted": 1,
        "qualified": 1,
        "families_qualified": ["json"],
        "kill_gate": {"fired": False},
    }
    errors = qualify.check_receipts(summary, receipts)
    assert any("empty-workspace" in e for e in errors)


def test_check_rejects_qualified_without_independent_generation():
    receipts = [
        {
            "family": "json",
            "attempted": True,
            "skipped": False,
            "qualified": True,
            "independent_generation": False,
            "held_out_guard": {"pass": True},
        }
    ]
    summary = {
        "attempted": 1,
        "qualified": 1,
        "families_qualified": ["json"],
        "kill_gate": {"fired": False},
    }
    errors = qualify.check_receipts(summary, receipts)
    assert any("independent_generation" in e for e in errors)


# Families with two stored empty-workspace generations that both passed.
QUALIFIED_FAMILIES = {
    "base64",
    "binascii",
    "difflib",
    "fnmatch",
    "hashlib",
    "hmac",
    "json",
    "shlex",
    "struct",
    "urllib_parse",
    "bisect",
    "colorsys",
    "heapq",
    "html",
    "keyword",
    "operator",
    "quopri",
    "textwrap",
    "calendar",
    "string",
    "statistics",
    "pprint",
    "copy",
    "fractions",
    "glob",
    "reprlib",
    "getopt",
    "ipaddress",
    "mimetypes",
    "itertools",
    "posixpath",
    "ntpath",
    "contextlib",
    "collections",
    "datetime",
    "csv",
    "math",
    "email_utils",
    "decimal",
    "codecs",
    "array",
    "re",
    "io",
    "pyuuid",
    "pathlib",
    "stat",
    "http_cookies",
    "ast",
    "queue",
    "secrets",
    "types",
    "time",
    "deque",
    "zlib",
    "hexlify",
    "xml_etree",
    "wsgiref",
    "unicodedata",
    "cmath",
    "pickle",
    "adler32",
    "close_matches",
    "unhexlify",
    "cleandoc",
    "cmd",
    "gettext",
    "fnmatchcase",
    "shorten",
    "template",
    "ordereddict",
    "chainmap",
    "threadlock",
    "comb",
    "perm",
    "lcm",
    "prod",
    "hypot",
    "isqrt",
    "ceil",
    "floor",
    "indent",
    "unquote",
    "quoteplus",
    "semaphore",
    "stringio",
    "tdelta",
    "optionxform",
    "usagefmt",
    "b16encode",
    "category",
    "loggername",
    "ctxvar",
    "zipinfo",
    "tarinfo",
    "dist",
    "trunc",
    "fabs",
    "copysign",
    "medianlow",
    "datamode",
    "bisectleft",
    "nlargest",
}


def test_committed_receipts_are_honest():
    summary = json.loads((RECEIPTS / "summary.json").read_text(encoding="utf-8"))
    assert summary["qualified"] == len(QUALIFIED_FAMILIES)
    assert summary["attempted"] >= 5
    assert set(summary["families_qualified"]) == QUALIFIED_FAMILIES
    assert summary["kill_gate"]["fired"] is False
    assert summary["kill_gate"]["product_claim"] == "replacement_still_open"
    for family in summary["families_attempted"]:
        rec = json.loads((RECEIPTS / "{}.json".format(family)).read_text(encoding="utf-8"))
        assert rec["attempted"] is True
        if family in QUALIFIED_FAMILIES:
            assert rec["public_oracle"]["ok"] is True
            assert rec["held_out_oracle"]["ok"] is True
            assert rec["held_out_guard"]["pass"] is True
            assert rec["isolation"] is True
            assert rec["qualified"] is True
            assert rec["independent_generation"] is True
            assert rec["empty_workspace_pair"] is True
            assert rec["impl_hash_run1"] != rec["impl_hash_run2"]
        else:
            assert rec["qualified"] is False


def test_registry_is_qualified_tracks_dual_generation_not_legacy_status():
    assert registry.is_allowed("theseus_json") is True
    assert registry.is_qualified("theseus_re") is False
    assert registry.is_qualified("theseus_base64") is False
    data = json.loads((ROOT / "theseus_registry.json").read_text(encoding="utf-8"))
    assert data["ladder"]["is_qualified"] is False
    assert data["ladder"]["qualified"] == [
        "theseus_base64_q",
        "theseus_fnmatch_q",
        "theseus_json",
        "theseus_shlex_q",
        "theseus_binascii_q",
        "theseus_difflib_q",
        "theseus_hashlib_q",
        "theseus_hmac_q",
        "theseus_struct_q",
        "theseus_urllib_parse_q",
        "theseus_bisect_q",
        "theseus_colorsys_q",
        "theseus_heapq_q",
        "theseus_html_q",
        "theseus_keyword_q",
        "theseus_operator_q",
        "theseus_quopri_q",
        "theseus_textwrap_q",
        "theseus_calendar_q",
        "theseus_string_q",
        "theseus_statistics_q",
        "theseus_pprint_q",
        "theseus_copy_q",
        "theseus_fractions_q",
        "theseus_glob_q",
        "theseus_reprlib_q",
        "theseus_getopt_q",
        "theseus_ipaddress_q",
        "theseus_mimetypes_q",
        "theseus_itertools_q",
        "theseus_posixpath_q",
        "theseus_ntpath_q",
        "theseus_contextlib_q",
        "theseus_collections_q",
        "theseus_datetime_q",
        "theseus_csv_q",
        "theseus_math_q",
        "theseus_email_utils_q",
        "theseus_decimal_q",
        "theseus_codecs_q",
        "theseus_array_q",
        "theseus_re_q",
        "theseus_io_q",
        "theseus_pyuuid_q",
        "theseus_pathlib_q",
        "theseus_stat_q",
        "theseus_http_cookies_q",
        "theseus_ast_q",
        "theseus_queue_q",
        "theseus_secrets_q",
        "theseus_types_q",
        "theseus_time_q",
        "theseus_deque_q",
        "theseus_zlib_q",
        "theseus_hexlify_q",
        "theseus_xml_etree_q",
        "theseus_wsgiref_q",
        "theseus_unicodedata_q",
        "theseus_cmath_q",
        "theseus_pickle_q",
        "theseus_adler32_q",
        "theseus_close_matches_q",
        "theseus_unhexlify_q",
        "theseus_cleandoc_q",
        "theseus_cmd_q",
        "theseus_gettext_q",
        "theseus_fnmatchcase_q",
        "theseus_shorten_q",
        "theseus_template_q",
        "theseus_ordereddict_q",
        "theseus_chainmap_q",
        "theseus_threadlock_q",
        "theseus_comb_q",
        "theseus_perm_q",
        "theseus_lcm_q",
        "theseus_prod_q",
        "theseus_hypot_q",
        "theseus_isqrt_q",
        "theseus_ceil_q",
        "theseus_floor_q",
        "theseus_indent_q",
        "theseus_unquote_q",
        "theseus_quoteplus_q",
        "theseus_semaphore_q",
        "theseus_stringio_q",
        "theseus_tdelta_q",
        "theseus_optionxform_q",
        "theseus_usagefmt_q",
        "theseus_b16encode_q",
        "theseus_category_q",
        "theseus_loggername_q",
        "theseus_ctxvar_q",
        "theseus_zipinfo_q",
        "theseus_tarinfo_q",
        "theseus_dist_q",
        "theseus_trunc_q",
        "theseus_fabs_q",
        "theseus_copysign_q",
        "theseus_medianlow_q",
        "theseus_datamode_q",
        "theseus_bisectleft_q",
        "theseus_nlargest_q",
    ]
    assert data["ladder"]["product"] == "characterization"
    assert registry.is_qualified("theseus_base64_q") is True
    assert registry.is_qualified("theseus_fnmatch_q") is True
    assert registry.is_qualified("theseus_json") is True
    assert registry.is_qualified("theseus_shlex_q") is True
    assert registry.is_qualified("theseus_binascii_q") is True
    assert registry.is_qualified("theseus_difflib_q") is True
    assert registry.is_qualified("theseus_hashlib_q") is True
    assert registry.is_qualified("theseus_hmac_q") is True
    assert registry.is_qualified("theseus_struct_q") is True
    assert registry.is_qualified("theseus_urllib_parse_q") is True
    assert registry.is_qualified("theseus_bisect_q") is True
    assert registry.is_qualified("theseus_colorsys_q") is True
    assert registry.is_qualified("theseus_heapq_q") is True
    assert registry.is_qualified("theseus_html_q") is True
    assert registry.is_qualified("theseus_keyword_q") is True
    assert registry.is_qualified("theseus_operator_q") is True
    assert registry.is_qualified("theseus_quopri_q") is True
    assert registry.is_qualified("theseus_textwrap_q") is True
    assert registry.is_qualified("theseus_calendar_q") is True
    assert registry.is_qualified("theseus_string_q") is True
    assert registry.is_qualified("theseus_statistics_q") is True
    assert registry.is_qualified("theseus_pprint_q") is True
    assert registry.is_qualified("theseus_copy_q") is True
    assert registry.is_qualified("theseus_fractions_q") is True
    assert registry.is_qualified("theseus_glob_q") is True
    assert registry.is_qualified("theseus_reprlib_q") is True
    assert registry.is_qualified("theseus_getopt_q") is True
    assert registry.is_qualified("theseus_ipaddress_q") is True
    assert registry.is_qualified("theseus_mimetypes_q") is True
    assert registry.is_qualified("theseus_itertools_q") is True
    assert registry.is_qualified("theseus_posixpath_q") is True
    assert registry.is_qualified("theseus_ntpath_q") is True
    assert registry.is_qualified("theseus_contextlib_q") is True
    assert registry.is_qualified("theseus_collections_q") is True
    assert registry.is_qualified("theseus_datetime_q") is True
    assert registry.is_qualified("theseus_csv_q") is True
    assert registry.is_qualified("theseus_math_q") is True
    assert registry.is_qualified("theseus_email_utils_q") is True
    assert registry.is_qualified("theseus_decimal_q") is True
    assert registry.is_qualified("theseus_codecs_q") is True
    assert registry.is_qualified("theseus_array_q") is True
    assert registry.is_qualified("theseus_re_q") is True
    assert registry.is_qualified("theseus_io_q") is True
    assert registry.is_qualified("theseus_pyuuid_q") is True
    assert registry.is_qualified("theseus_pathlib_q") is True
    assert registry.is_qualified("theseus_stat_q") is True
    assert registry.is_qualified("theseus_http_cookies_q") is True
    assert registry.is_qualified("theseus_ast_q") is True
    assert registry.is_qualified("theseus_queue_q") is True
    assert registry.is_qualified("theseus_pickle_q") is True
    assert registry.is_qualified("theseus_adler32_q") is True
    assert registry.is_qualified("theseus_threadlock_q") is True
    assert registry.is_qualified("theseus_prod_q") is True
    assert registry.is_qualified("theseus_usagefmt_q") is True
    assert registry.is_qualified("theseus_b16encode_q") is True
    assert registry.is_qualified("theseus_nlargest_q") is True
