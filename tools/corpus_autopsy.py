#!/usr/bin/env python3
"""
corpus_autopsy.py — Classify the Theseus spec and clean-room corpus.

Phase 0 of the verification-ladder refresh. Regenerates:

  reports/audit/corpus-autopsy.json
  reports/audit/corpus-autopsy.md
  reports/audit/withdrawn-verified.json

This is a reporting tool. It does not add packages or synthesize implementations.

Usage:
  python3 tools/corpus_autopsy.py
  python3 tools/corpus_autopsy.py --out-dir reports/audit
  python3 tools/corpus_autopsy.py --check
  python3 tools/corpus_autopsy.py --json   # autopsy JSON to stdout
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools"))

import zsdl_compile  # noqa: E402

SCHEMA = "theseus-corpus-autopsy/0.1"
LADDER_DECISION = "docs/decisions/0001-verification-ladder.md"
REGISTRY_PATH = _REPO_ROOT / "theseus_registry.json"
ZSPECS_DIR = _REPO_ROOT / "zspecs"
DEFAULT_OUT_DIR = _REPO_ROOT / "reports" / "audit"

# Intended gold-set families for regenerative qualification (Phase 3).
# Membership here is a research target, not a claim that the current spec is sufficient.
INTENDED_GOLD_SET = frozenset({
    "json",
    "base64",
    "hashlib",
    "uuid",
    "semver",
    "tomllib",
    "tomli",
    "struct",
    "binascii",
    "urllib_parse",
    "difflib",
    "pcap",
    "libpcap",
    "pcapng",
    "fnmatch",
    "shlex",
    "hmac",
})

# High-feasibility Layer 2 families characterized after the qualification
# gold set (Phase 11 + 2026-09-20 pass). Not qualification targets (ADR 0005).
CHARACTERIZATION_COHORT = frozenset({
    "bisect",
    "operator",
    "pprint",
    "html",
    "msgpack",
    "ntpath",
    "ipaddress",
    "posixpath",
    "decimal",
    "keyword",
    "string",
    "calendar",
    "fractions",
    "csv",
    "elementtree",
    "copy",
    "heapq",
    "reprlib",
    "statistics",
    "enum",
    "html_entities",
    "weakref",
    "html_parser",
    "idna",
    "textwrap",
    "tomlkit",
    "colorsys",
    "copyreg",
    "genericpath",
    "glob",
    "pathspec",
    "quopri",
    "uu",
    "ulid",
    "base_x",
    "card_validator",
    "email_validator",
    "graphlib",
    "ieee754",
    "isemail",
    "jsonpointer",
    "jsonschema",
    "nanoid",
    "punycode",
    "semver_diff",
    "unidecode",
})

LEDGER_STATUSES = frozenset({"resolved", "deferred", "held_out"})

# Replacement of the original is plausible from a public spec + held-out oracle.
_HIGH_PURE = frozenset({
    "json", "base64", "binascii", "struct", "csv", "uuid", "hashlib", "hmac",
    "semver", "fnmatch", "shlex", "textwrap", "html_escape", "html", "colorsys",
    "ipaddress", "idna", "difflib", "bisect", "heapq", "urllib_parse",
    "tomllib", "tomli", "tomlkit", "toml", "msgpack", "pcap", "libpcap", "pcapng",
    "crc32", "base32", "nanoid", "ulid", "punycode", "ieee754", "card_validator",
    "email_validator", "isemail", "unidecode", "base_x", "ascii85", "quopri",
    "uu", "encodings", "string", "textwrap", "calendar", "fractions",
    "statistics", "decimal", "graphlib", "enum", "operator", "keyword",
    "reprlib", "pprint", "copy", "copyreg", "weakref", "types_utils",
    "html_entities", "html_parser", "xml_etree", "elementtree",
    "jsonpointer", "jsonschema", "semver_diff", "pathspec", "glob",
    "fnmatch", "posixpath", "genericpath", "ntpath", "purepath",
})

# Specified, but large, stateful, or only a subset is realistic.
_MEDIUM = frozenset({
    "pathlib", "re", "datetime", "collections", "itertools", "functools",
    "email", "email_policy", "email_header", "email_utils", "email_mime_text",
    "http", "urllib", "urllib_error", "urllib_request", "urllib_robotparser",
    "logging", "argparse", "getopt", "configparser", "tempfile", "io",
    "codecs", "locale", "unicodedata", "stringprep", "difflib",
    "packaging", "pyparsing", "lark", "yaml", "pyyaml", "tomlkit",
    "markdown", "docutils", "pygments", "jinja2", "mako",
    "attrs", "cattrs", "dataclasses", "typing", "typing_extensions",
    "contextlib", "contextvars", "abc", "numbers", "fractions",
    "csv", "plistlib", "netrc", "mailbox", "mimetypes", "base64",
    "gzip", "bz2", "lzma", "zlib", "zstd", "zipfile", "tarfile",
    "pathlib_extra", "re_extra", "collections_utils",
})

# C / native core: characterize, do not claim clean-room drop-in replacement.
_NATIVE_CORE = frozenset({
    "numpy", "lxml", "sqlite3", "pillow", "pil", "cryptography", "pydantic",
    "orjson", "uvloop", "psutil", "protobuf", "grpc", "pandas", "scipy",
    "cv2", "duckdb", "catboost", "tensorflow", "torch", "markupsafe",
    "wrapt", "zope_interface", "pyyaml", "lxml", "pyexpat", "_elementtree",
    "_json", "_pickle", "_socket", "_ssl", "_hashlib", "_datetime",
    "_decimal", "_io", "_csv", "_struct", "_bisect", "_heapq", "_thread",
    "_weakref",     "_codecs", "unicodedata", "zlib", "lzma", "bz2", "zstd",
    "compression_zlib", "compression_gzip", "compression_zstd",
    "ssl",
    "cffi", "cython",
})

_OS_BINDING = frozenset({
    "socket", "select", "selectors", "subprocess", "multiprocessing", "os",
    "posix", "nt", "pwd", "grp", "spwd", "crypt", "fcntl", "termios", "tty",
    "pty", "resource", "syslog", "mmap", "signal", "winreg", "winsound",
    "msvcrt", "readline", "curses", "fcntl", "asyncore", "asynchat",
    "imaplib", "smtplib", "ftplib", "nntplib", "telnetlib", "poplib",
    "webbrowser", "cgi", "cgitb", "wsgiref", "http_server", "xmlrpc",
    "xmlrpc_client", "asyncio", "selectors", "fcntl", "msilib",
    "platform", "sysconfig", "getpass", "curses", "turtle",
})

_STDLIB_INTERPRETER = frozenset({
    "sys", "builtins", "importlib", "importlib_abc", "marshal", "gc",
    "code", "codeop", "compileall", "symtable", "dis", "opcode", "types",
    "pkgutil", "modulefinder", "runpy", "site", "inspect", "ast", "tokenize",
    "parser", "ctypes", "ctypes_extra", "ctypes_extra2", "sys",
    "warnings", "traceback", "faulthandler", "gc", "atexit",
    "pkgutil", "zipimport", "importlib_machinery",
})

_INFEASIBLE = frozenset({
    "antigravity", "this", "turtle", "turtledemo", "idlelib", "tkinter",
    "__hello__", "__phello__", "_sitebuiltins", "_osx_support",
    "antigravity_cr",
})

_WRAPPER_FN_SUFFIXES = (
    "_int", "_ok", "_has_key", "_round_trip", "_exists", "_true",
    "_callable", "_present", "_url", "_fly",
)
_PRESENCE_RE = re.compile(
    r"\b(exists|callable|hasattr|exposes|is importable|function exists|"
    r"module exposes|is present)\b",
    re.IGNORECASE,
)
_FAMILY_CR_RE = re.compile(r"_cr\d*$")
_FAMILY_EXTRA_RE = re.compile(r"_extra\d*$")
_FAMILY_RUST_RE = re.compile(r"_rust$")
_FAMILY_NODE_RE = re.compile(r"_node$")
_FAMILY_Q_RE = re.compile(r"_q$")
_WRAPPER_DIGIT_RE = re.compile(r"\d_")


def family_key(name: str) -> str:
    """Collapse wave suffixes into a comparison key."""
    if not name:
        return ""
    key = name.strip()
    if key.startswith("theseus_"):
        key = key[len("theseus_"):]
    key = _FAMILY_RUST_RE.sub("", key)
    key = _FAMILY_NODE_RE.sub("", key)
    key = _FAMILY_CR_RE.sub("", key)
    key = _FAMILY_EXTRA_RE.sub("", key)
    key = _FAMILY_Q_RE.sub("", key)
    return key.lower()


def classify_feasibility(family: str, backend: str, spec_name: str) -> str:
    """Replacement-feasibility class for this spec's subject."""
    if backend == "rust_module":
        return "wrapper"
    fam = family.lower()
    name = (spec_name or "").lower()
    if fam in _INFEASIBLE or name in _INFEASIBLE or fam.startswith("antigravity"):
        return "infeasible"
    if fam in _STDLIB_INTERPRETER or fam.startswith("_") or fam.startswith("ctypes"):
        return "stdlib_interpreter"
    if fam in _OS_BINDING:
        return "os_binding"
    if fam in _HIGH_PURE:
        return "high"
    if fam in _NATIVE_CORE:
        return "native_core"
    if fam in _MEDIUM or any(fam.startswith(p + "_") for p in _MEDIUM):
        return "medium"
    if fam.startswith("email_") or fam.startswith("urllib_") or fam.startswith("xml_"):
        return "medium"
    if fam.startswith("http") or fam.startswith("html"):
        return "medium"
    return "needs_review"


def backend_kind(compiled: dict) -> str:
    lib = compiled.get("library") or {}
    backend = lib.get("backend") or ""
    if backend in (
        "python_module",
        "python_cleanroom",
        "node_cleanroom",
        "rust_module",
    ):
        return backend
    if backend == "cli":
        if lib.get("command") == "node" and lib.get("module_name"):
            return "node"
        return "cli"
    if lib.get("soname_patterns"):
        return "ctypes"
    compiled_lang = compiled.get("backend_lang") or ""
    if compiled_lang:
        return compiled_lang
    return "unknown"


def _is_true(value) -> bool:
    return value is True or value == "true" or value == "True"


def _function_name(spec: dict) -> str:
    fn = spec.get("function")
    if isinstance(fn, str) and fn:
        return fn
    call = spec.get("call")
    if isinstance(call, str) and call:
        return call.split("(", 1)[0].split(".")[-1]
    return ""


def _args_empty(spec: dict) -> bool:
    if "args" not in spec:
        # Chain kinds often use method_chain / steps instead of args.
        if spec.get("method_chain") or spec.get("steps") or spec.get("chain"):
            return False
        return True
    args = spec.get("args")
    return args == [] or args is None


def is_wrapper_function(fn: str, spec_name: str, backend: str) -> bool:
    if not fn:
        return False
    if any(fn.endswith(sfx) for sfx in _WRAPPER_FN_SUFFIXES):
        return True
    if _WRAPPER_DIGIT_RE.search(fn):
        return True
    stem = spec_name[len("theseus_"):] if spec_name.startswith("theseus_") else spec_name
    if stem.endswith("_q"):
        stem = stem[:-2]
    factory_prefix = stem + "_"
    if fn.startswith(factory_prefix):
        return True
    return False


def oracle_quality(
    invariant_count: int,
    zero_arg_ratio: float,
    expected_true_ratio: float,
    presence_ratio: float,
    backend: str,
    contract_shape: str,
) -> str:
    if invariant_count == 0:
        return "empty"
    if presence_ratio >= 0.8 or (
        expected_true_ratio >= 0.8 and zero_arg_ratio >= 0.8
    ):
        return "presence"
    if contract_shape == "self_test_wrapper" and invariant_count <= 3:
        return "factory_shallow"
    if contract_shape == "self_test_wrapper":
        return "self_test"
    if contract_shape == "wrapper":
        return "wrapper"
    if invariant_count <= 3:
        return "shallow"
    if invariant_count < 16:
        return "moderate"
    return "deep"


def contract_shape(
    backend: str,
    zero_arg_ratio: float,
    wrapper_fn_ratio: float,
    expected_true_ratio: float,
) -> str:
    if backend == "rust_module":
        return "wrapper"
    if backend in ("python_cleanroom", "node_cleanroom"):
        if zero_arg_ratio >= 0.9 or wrapper_fn_ratio >= 0.5:
            return "self_test_wrapper"
        return "cleanroom_public_api"
    if expected_true_ratio >= 0.8 and zero_arg_ratio >= 0.8:
        return "presence"
    return "public_api"


def ladder_for_spec(record: dict) -> str:
    """Map a classified spec onto ADR 0001 rungs (corpus as it exists today)."""
    if record.get("in_registry") and record.get("registry_status") == "verified":
        return "legacy_isolation"
    if (
        record.get("contract_shape") == "public_api"
        and record.get("oracle_quality") in ("moderate", "deep")
        and record.get("backend")
        not in ("python_cleanroom", "node_cleanroom", "rust_module")
    ):
        return "oracle_bound"
    if record.get("backend") in ("python_cleanroom", "node_cleanroom"):
        return "legacy_isolation" if record.get("in_registry") else "inventoried"
    if record.get("contract_shape") == "wrapper":
        return "inventoried"
    if record.get("invariant_count", 0) > 0:
        return "characterized_draft"
    return "inventoried"


def impl_signals(impl_path: Path | None) -> dict:
    out = {
        "impl_path": None,
        "impl_exists": False,
        "return_true": 0,
        "return_total": 0,
        "bytes": 0,
    }
    if impl_path is None:
        return out
    out["impl_path"] = str(impl_path)
    if not impl_path.is_file():
        return out
    text = impl_path.read_text(encoding="utf-8", errors="replace")
    out["impl_exists"] = True
    out["bytes"] = len(text.encode("utf-8"))
    true_hits = re.findall(r"^\s*return True\s*$", text, re.MULTILINE)
    true_hits += re.findall(r"^\s*return true\s*;?\s*$", text, re.MULTILINE)
    all_returns = re.findall(r"^\s*return\b", text, re.MULTILINE)
    out["return_true"] = len(true_hits)
    out["return_total"] = len(all_returns)
    return out


def _impl_path_for(compiled: dict, repo_root: Path) -> Path | None:
    backend = backend_kind(compiled)
    name = (compiled.get("library") or {}).get("module_name") or ""
    if backend == "python_cleanroom" and name:
        return repo_root / "cleanroom" / "python" / name / "__init__.py"
    if backend == "node_cleanroom" and name:
        return repo_root / "cleanroom" / "node" / name / "index.js"
    cleanroom_path = compiled.get("cleanroom_path")
    if cleanroom_path:
        p = repo_root / cleanroom_path
        py = p / "__init__.py"
        js = p / "index.js"
        if py.is_file():
            return py
        if js.is_file():
            return js
        return py
    return None


def classify_invariants(invariants: list) -> dict:
    n = len(invariants)
    zero_arg = 0
    expected_true = 0
    presence = 0
    wrapper_fn = 0
    functions = []
    for inv in invariants:
        spec = inv.get("spec") or {}
        fn = _function_name(spec)
        functions.append(fn)
        if _args_empty(spec):
            zero_arg += 1
        if _is_true(spec.get("expected")):
            expected_true += 1
        desc = inv.get("description") or ""
        if _PRESENCE_RE.search(desc) or _is_true(spec.get("expected")) and _args_empty(spec):
            # Count as presence-shaped only when the description says so,
            # or when a zero-arg invariant's only claim is True.
            if _PRESENCE_RE.search(desc):
                presence += 1
            elif _is_true(spec.get("expected")) and _args_empty(spec):
                presence += 1
        # wrapper_fn filled by caller (needs spec_name/backend)
    return {
        "invariant_count": n,
        "zero_arg": zero_arg,
        "expected_true": expected_true,
        "presence": presence,
        "functions": functions,
        "zero_arg_ratio": (zero_arg / n) if n else 0.0,
        "expected_true_ratio": (expected_true / n) if n else 0.0,
        "presence_ratio": (presence / n) if n else 0.0,
    }


def classify_compiled(
    compiled: dict,
    *,
    zsdl_path: Path,
    repo_root: Path,
    registry: dict,
) -> dict:
    name = (compiled.get("identity") or {}).get("canonical_name") or zsdl_path.stem
    backend = backend_kind(compiled)
    family = family_key(name)
    inv_stats = classify_invariants(compiled.get("invariants") or [])
    wrapper_hits = sum(
        1
        for fn in inv_stats["functions"]
        if is_wrapper_function(fn, name, backend)
    )
    n = inv_stats["invariant_count"]
    wrapper_fn_ratio = (wrapper_hits / n) if n else 0.0
    shape = contract_shape(
        backend,
        inv_stats["zero_arg_ratio"],
        wrapper_fn_ratio,
        inv_stats["expected_true_ratio"],
    )
    quality = oracle_quality(
        n,
        inv_stats["zero_arg_ratio"],
        inv_stats["expected_true_ratio"],
        inv_stats["presence_ratio"],
        backend,
        shape,
    )
    packages = registry.get("packages") or {}
    in_registry = name in packages
    registry_status = (packages.get(name) or {}).get("status")
    impl = impl_signals(_impl_path_for(compiled, repo_root))
    try:
        rel_file = str(zsdl_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        rel_file = str(zsdl_path)
    record = {
        "name": name,
        "file": rel_file,
        "backend": backend,
        "family": family,
        "intended_gold_set": family in INTENDED_GOLD_SET or family in {"libpcap", "pcap"},
        "invariant_count": n,
        "zero_arg_ratio": round(inv_stats["zero_arg_ratio"], 3),
        "expected_true_ratio": round(inv_stats["expected_true_ratio"], 3),
        "presence_ratio": round(inv_stats["presence_ratio"], 3),
        "wrapper_fn_ratio": round(wrapper_fn_ratio, 3),
        "oracle_quality": quality,
        "contract_shape": shape,
        "feasibility": classify_feasibility(family, backend, name),
        "in_registry": in_registry,
        "registry_status": registry_status,
        "impl_exists": impl["impl_exists"],
        "impl_return_true": impl["return_true"],
        "impl_return_total": impl["return_total"],
        "impl_bytes": impl["bytes"],
    }
    record["ladder"] = ladder_for_spec(record)
    record["withdraw_qualification"] = bool(
        in_registry and registry_status == "verified"
    )
    return record


def load_registry(path: Path) -> dict:
    if not path.is_file():
        return {"packages": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def compile_zsdl(path: Path) -> dict:
    compiler = zsdl_compile.ZSDLCompiler()
    return compiler.compile_file(path)


def _count(records: list, key: str) -> dict:
    c = Counter(r.get(key) or "unknown" for r in records)
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def build_families(spec_records: list) -> list:
    groups = defaultdict(list)
    for rec in spec_records:
        groups[rec["family"]].append(rec["name"])
    families = []
    for family, members in groups.items():
        uniq = sorted(set(members))
        families.append({
            "family": family,
            "count": len(uniq),
            "duplicate_wave": len(uniq) >= 2,
            "members": uniq,
        })
    families.sort(key=lambda f: (-f["count"], f["family"]))
    return families


def scan_characterization(repo_root: Path) -> list:
    """Classify gold/<family>/ authority + uncertainty ledgers (ADR 0003)."""
    gold_root = repo_root / "gold"
    rows = []
    if not gold_root.is_dir():
        return rows
    yaml = zsdl_compile.yaml
    for path in sorted(gold_root.iterdir()):
        if not path.is_dir() or not (path / "package.md").is_file():
            continue
        rec = {
            "family": path.name,
            "intended_gold_set": path.name in INTENDED_GOLD_SET,
            "characterization_cohort": path.name in CHARACTERIZATION_COHORT,
            "has_authority": True,
            "has_ledger": (path / "uncertainty.yaml").is_file(),
            "has_probes": (path / "probes.yaml").is_file(),
            "has_held_out": (path / "held_out.zspec.zsdl").is_file(),
            "reviewed": False,
            "item_count": 0,
            "open_items": [],
            "status": "missing_ledger",
        }
        ledger = path / "uncertainty.yaml"
        if not rec["has_ledger"]:
            rows.append(rec)
            continue
        try:
            doc = yaml.safe_load(ledger.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001 — autopsy must classify, not abort
            rec["status"] = "invalid_ledger"
            rec["error"] = str(exc)
            rows.append(rec)
            continue
        if not isinstance(doc, dict):
            rec["status"] = "invalid_ledger"
            rec["error"] = "top-level must be a mapping"
            rows.append(rec)
            continue
        items = doc.get("items") or []
        rec["item_count"] = len(items)
        rec["reviewed"] = bool(doc.get("reviewed"))
        rec["open_items"] = [
            item.get("id") for item in items
            if item.get("status") not in LEDGER_STATUSES
        ]
        if rec["open_items"]:
            rec["status"] = "open"
        elif not rec["reviewed"]:
            rec["status"] = "unreviewed"
        elif not items:
            rec["status"] = "empty"
        else:
            rec["status"] = "accepted"
        rows.append(rec)
    return rows


def gold_set_candidates(spec_records: list) -> list:
    out = []
    for rec in spec_records:
        if rec["backend"] in ("python_cleanroom", "node_cleanroom", "rust_module"):
            continue
        if rec["contract_shape"] != "public_api":
            continue
        if rec["oracle_quality"] not in ("moderate", "deep"):
            continue
        if rec["feasibility"] not in ("high", "medium"):
            continue
        out.append({
            "name": rec["name"],
            "family": rec["family"],
            "backend": rec["backend"],
            "invariant_count": rec["invariant_count"],
            "oracle_quality": rec["oracle_quality"],
            "feasibility": rec["feasibility"],
            "intended_gold_set": rec["intended_gold_set"],
        })
    out.sort(key=lambda r: (-int(r["intended_gold_set"]), -r["invariant_count"], r["name"]))
    return out


def withdrawn_entries(spec_records: list, registry: dict) -> list:
    by_name = {r["name"]: r for r in spec_records}
    out = []
    for name, info in sorted((registry.get("packages") or {}).items()):
        if info.get("status") != "verified":
            continue
        rec = by_name.get(name) or {}
        reasons = []
        quality = rec.get("oracle_quality") or "missing_spec"
        shape = rec.get("contract_shape") or "unknown"
        if quality in ("factory_shallow", "presence", "self_test", "shallow", "empty"):
            reasons.append("oracle_too_shallow")
        if shape in ("self_test_wrapper", "wrapper", "presence"):
            reasons.append("not_public_api_oracle")
        if rec.get("zero_arg_ratio", 1.0) >= 0.9:
            reasons.append("zero_arg_wrappers")
        if rec.get("expected_true_ratio", 0) >= 0.8:
            reasons.append("expected_true_dominant")
        if not rec:
            reasons.append("spec_not_classified")
        if not reasons:
            reasons.append("legacy_isolation_is_not_qualification")
        out.append({
            "name": name,
            "legacy_status": "verified",
            "ladder": "legacy_isolation",
            "oracle_quality": quality,
            "contract_shape": shape,
            "invariant_count": rec.get("invariant_count", 0),
            "reasons": reasons,
        })
    return out


def summarize(spec_records: list, withdrawn: list, gold: list, families: list, errors: list, unmatched: list, characterization=None) -> dict:
    characterization = characterization or []
    registry_recs = [r for r in spec_records if r.get("in_registry")]
    factory = [r for r in spec_records if r.get("oracle_quality") == "factory_shallow"]
    public_deep = [
        r for r in spec_records
        if r.get("contract_shape") == "public_api" and r.get("oracle_quality") in ("moderate", "deep")
    ]
    dup_families = [f for f in families if f["duplicate_wave"]]
    return {
        "spec_count": len(spec_records),
        "compile_errors": len(errors),
        "unmatched_registry_packages": unmatched,
        "registry_classified": len(registry_recs),
        "withdrawn_from_qualification": len(withdrawn),
        "qualified": 0,
        "oracle_bound_public_api": len(public_deep),
        "factory_shallow": len(factory),
        "duplicate_families": len(dup_families),
        "gold_set_candidates": len(gold),
        "intended_gold_set": len(INTENDED_GOLD_SET),
        "characterization_cohort": len(CHARACTERIZATION_COHORT),
        "gold_characterization_families": len(characterization),
        "gold_characterization_accepted": sum(
            1 for row in characterization if row.get("status") == "accepted"
        ),
        "gold_characterization_open": sum(
            1 for row in characterization
            if row.get("status") in ("open", "unreviewed", "missing_ledger", "empty", "invalid_ledger")
        ),
        "by_backend": _count(spec_records, "backend"),
        "by_oracle_quality": _count(spec_records, "oracle_quality"),
        "by_contract_shape": _count(spec_records, "contract_shape"),
        "by_feasibility": _count(spec_records, "feasibility"),
        "by_ladder": _count(spec_records, "ladder"),
        "median_invariants_cleanroom": _median(
            [r["invariant_count"] for r in spec_records if r["backend"] in ("python_cleanroom", "node_cleanroom")]
        ),
        "median_invariants_public": _median(
            [r["invariant_count"] for r in spec_records if r["contract_shape"] == "public_api"]
        ),
    }


def _median(values: list) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def build_report(
    repo_root: Path,
    *,
    zspecs_dir: Path | None = None,
    registry_path: Path | None = None,
    progress: bool = False,
) -> dict:
    zspecs_dir = zspecs_dir or (repo_root / "zspecs")
    registry_path = registry_path or (repo_root / "theseus_registry.json")
    registry = load_registry(registry_path)
    paths = sorted(zspecs_dir.glob("*.zspec.zsdl"))
    spec_records = []
    errors = []
    for i, path in enumerate(paths, 1):
        if progress and i % 200 == 0:
            print(f"  classified {i}/{len(paths)} specs", file=sys.stderr)
        try:
            compiled = compile_zsdl(path)
            spec_records.append(
                classify_compiled(
                    compiled,
                    zsdl_path=path,
                    repo_root=repo_root,
                    registry=registry,
                )
            )
        except (zsdl_compile.CompileError, yaml_error()) as exc:
            errors.append({"file": str(path.name), "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 — autopsy must not abort the corpus
            errors.append({"file": str(path.name), "error": "{}: {}".format(type(exc).__name__, exc)})

    families = build_families(spec_records)
    gold = gold_set_candidates(spec_records)
    withdrawn = withdrawn_entries(spec_records, registry)
    characterization = scan_characterization(repo_root)
    spec_names = {r["name"] for r in spec_records}
    unmatched = sorted(
        n for n in (registry.get("packages") or {})
        if n not in spec_names
    )
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "decision": LADDER_DECISION,
        "summary": summarize(
            spec_records, withdrawn, gold, families, errors, unmatched,
            characterization=characterization,
        ),
        "intended_gold_set": sorted(INTENDED_GOLD_SET),
        "specs": spec_records,
        "families": families,
        "gold_set_candidates": gold,
        "characterization": characterization,
        "withdrawn_from_qualification": withdrawn,
        "unmatched_registry_packages": unmatched,
        "compile_errors": errors,
        "exhibits": _exhibits(spec_records),
    }


def yaml_error():
    """Return the YAML error type without making pyyaml a module-level name."""
    return zsdl_compile.yaml.YAMLError


def _exhibits(spec_records: list) -> dict:
    by_name = {r["name"]: r for r in spec_records}
    names = ("json", "theseus_json", "theseus_antigravity_cr", "hashlib", "semver")
    return {name: by_name[name] for name in names if name in by_name}


def render_markdown(report: dict) -> str:
    s = report["summary"]
    exhibits = report.get("exhibits") or {}
    gold = report.get("gold_set_candidates") or []
    characterization = report.get("characterization") or []
    errors = report.get("compile_errors") or []
    families = [f for f in report.get("families") or [] if f.get("duplicate_wave")][:25]
    withdrawn_n = s.get("withdrawn_from_qualification", 0)

    def table(counter: dict) -> str:
        lines = ["| Value | Count |", "|---|---:|"]
        for key, n in counter.items():
            lines.append("| `{}` | {} |".format(key, n))
        return "\n".join(lines)

    exhibit_lines = []
    for name, rec in exhibits.items():
        exhibit_lines.append(
            "- `{}`: backend `{}`, {} invariants, oracle `{}`, contract `{}`, ladder `{}`".format(
                name,
                rec.get("backend"),
                rec.get("invariant_count"),
                rec.get("oracle_quality"),
                rec.get("contract_shape"),
                rec.get("ladder"),
            )
        )
    char_lines = []
    for rec in characterization:
        if rec.get("intended_gold_set"):
            marker = " *(intended)*"
        elif rec.get("characterization_cohort"):
            marker = " *(cohort)*"
        else:
            marker = ""
        char_lines.append(
            "- `{}`{} — ledger `{}`, {} items, probes {}, held-out {}".format(
                rec["family"],
                marker,
                rec.get("status"),
                rec.get("item_count"),
                "yes" if rec.get("has_probes") else "no",
                "yes" if rec.get("has_held_out") else "no",
            )
        )
    gold_lines = []
    for rec in gold[:40]:
        marker = " *(intended)*" if rec.get("intended_gold_set") else ""
        gold_lines.append(
            "- `{}`{} — {} invariants, `{}`, feasibility `{}`, backend `{}`".format(
                rec["name"],
                marker,
                rec["invariant_count"],
                rec["oracle_quality"],
                rec["feasibility"],
                rec["backend"],
            )
        )
    fam_lines = [
        "- `{}` ({}) — {}".format(f["family"], f["count"], ", ".join("`{}`".format(m) for m in f["members"][:12]))
        for f in families
    ]
    err_lines = [
        "- `{}`: {}".format(e["file"], e["error"][:160])
        for e in errors[:20]
    ]

    parts = [
        "# Theseus Corpus Autopsy",
        "",
        "Generated: `{}`".format(report.get("generated_at")),
        "Schema: `{}`".format(report.get("schema")),
        "Decision: [`{}`](../../{})".format(report.get("decision"), report.get("decision")),
        "",
        "This report classifies the existing ZSDL corpus and clean-room registry.",
        "It does **not** claim any package is qualified. See ADR 0001.",
        "",
        "## Headline",
        "",
        "- **{}** source specs classified ({} compile errors).".format(s.get("spec_count"), s.get("compile_errors")),
        "- **{}** registry packages with `status=verified` are **withdrawn from qualification**.".format(withdrawn_n),
        "- **0** packages are `qualified`.",
        "- **{}** specs look like public-API oracles of moderate/deep depth (Layer 2 asset).".format(
            s.get("oracle_bound_public_api")
        ),
        "- **{}** specs match the 3-invariant clean-room factory (`factory_shallow`).".format(
            s.get("factory_shallow")
        ),
        "- Median invariant count: clean-room **{}**, public-API **{}**.".format(
            s.get("median_invariants_cleanroom"),
            s.get("median_invariants_public"),
        ),
        "- **{}** duplicate-wave families (same subject, `_cr` / `_cr2` / `_rust` suffixes).".format(
            s.get("duplicate_families")
        ),
        "- **{}** gold/<family>/ trees have an accepted uncertainty ledger (ADR 0003); **{}** still open/missing. **{}** are the intended qualification set; **{}** are the characterization cohort.".format(
            s.get("gold_characterization_accepted"),
            s.get("gold_characterization_open"),
            s.get("intended_gold_set"),
            s.get("characterization_cohort"),
        ),
        "- Registry names with no matching spec: `{}`.".format(
            ", ".join(s.get("unmatched_registry_packages") or []) or "none"
        ),
        "",
        "## Verification ladder (as applied to this corpus)",
        "",
        table(s.get("by_ladder") or {}),
        "",
        "Rungs are defined in ADR 0001. `legacy_isolation` is the old `verified` bit:",
        "the implementation passed its listed invariants with the original package blocked.",
        "That is not regenerative qualification.",
        "",
        "## By backend",
        "",
        table(s.get("by_backend") or {}),
        "",
        "## By oracle quality",
        "",
        table(s.get("by_oracle_quality") or {}),
        "",
        "## By contract shape",
        "",
        table(s.get("by_contract_shape") or {}),
        "",
        "## By replacement feasibility",
        "",
        table(s.get("by_feasibility") or {}),
        "",
        "## Exhibits",
        "",
    ]
    parts.extend(exhibit_lines or ["- (none of the expected exhibit specs were found)"])
    parts.extend([
        "",
        "`json` (Layer 2, public-API oracle) is the gold-set characterization exhibit.",
        "`theseus_json` was the Phase 0 factory-wrapper exhibit; ADR 0002 re-grades it on",
        "`dumps`/`loads` (`cleanroom_public_api`). Other `theseus_*` factory specs are unchanged.",
        "`theseus_antigravity_cr` is the exhibit that `expected: true` plus isolation is not a package.",
        "",
        "## Gold-set candidates (current Layer 2 oracles)",
        "",
        "These are **not** qualified. They are public-API specs whose current oracle depth",
        "and feasibility class make them the starting set for Phase 3, if Phase 1–2 succeed.",
        "The intended gold-set families are: `{}`.".format(", ".join(sorted(INTENDED_GOLD_SET))),
        "",
    ])
    parts.extend(gold_lines or ["- (none met the public-API + moderate/deep + high/medium bar)"])
    if len(gold) > 40:
        parts.append("- … {} more in `corpus-autopsy.json`".format(len(gold) - 40))
    parts.extend([
        "",
        "## Gold-set characterization (ADR 0003)",
        "",
        "Authority Markdown + reviewed uncertainty ledgers under `gold/<family>/`.",
        "Accepted ledgers are **not** qualification. `*(intended)*` is the ADR 0001",
        "qualification gold set. `*(cohort)*` is the characterization-only expansion.",
        "",
    ])
    parts.extend(char_lines or ["- (no gold/<family>/package.md trees found)"])
    parts.extend([
        "",
        "## Largest duplicate-wave families",
        "",
    ])
    parts.extend(fam_lines or ["- none"])
    parts.extend([
        "",
        "## Withdrawn qualification list",
        "",
        "Machine-readable file: [`withdrawn-verified.json`](withdrawn-verified.json).",
        "Every registry package whose `status` is `verified` is listed there as `legacy_isolation`.",
        "Count: **{}**.".format(withdrawn_n),
        "",
        "## Compile errors",
        "",
    ])
    parts.extend(err_lines or ["- none"])
    if len(errors) > 20:
        parts.append("- … {} more in `corpus-autopsy.json`".format(len(errors) - 20))
    parts.extend([
        "",
        "## Regenerating",
        "",
        "```bash",
        "make corpus-autopsy",
        "```",
        "",
    ])
    return "\n".join(parts) + "\n"


def withdrawn_document(report: dict) -> dict:
    withdrawn = report.get("withdrawn_from_qualification") or []
    return {
        "schema": "theseus-withdrawn-verified/0.1",
        "generated_at": report.get("generated_at"),
        "decision": LADDER_DECISION,
        "qualification_claim": "withdrawn",
        "count": len(withdrawn),
        "packages": withdrawn,
    }


def comparable_payload(report: dict) -> dict:
    """Drop volatile timestamps for --check."""
    payload = dict(report)
    payload.pop("generated_at", None)
    return payload


def write_reports(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    autopsy_json = out_dir / "corpus-autopsy.json"
    autopsy_md = out_dir / "corpus-autopsy.md"
    withdrawn_json = out_dir / "withdrawn-verified.json"
    autopsy_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    autopsy_md.write_text(render_markdown(report), encoding="utf-8")
    withdrawn_json.write_text(
        json.dumps(withdrawn_document(report), indent=2) + "\n", encoding="utf-8"
    )


def check_committed(report: dict, out_dir: Path) -> int:
    committed = out_dir / "corpus-autopsy.json"
    if not committed.is_file():
        print("missing {}".format(committed), file=sys.stderr)
        return 1
    existing = json.loads(committed.read_text(encoding="utf-8"))
    left = comparable_payload(existing)
    right = comparable_payload(report)
    if left == right:
        print("corpus autopsy is up to date")
        return 0
    # Compare summaries first for a useful error.
    if left.get("summary") != right.get("summary"):
        print("corpus autopsy summary drifted; run make corpus-autopsy", file=sys.stderr)
        print("committed: {}".format(json.dumps(left.get("summary"), sort_keys=True)), file=sys.stderr)
        print("current:   {}".format(json.dumps(right.get("summary"), sort_keys=True)), file=sys.stderr)
        return 1
    print("corpus autopsy JSON drifted (non-summary fields); run make corpus-autopsy", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify the Theseus spec corpus")
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--zspecs-dir", type=Path, default=None)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Write autopsy JSON to stdout")
    parser.add_argument("--check", action="store_true", help="Fail if committed autopsy is stale")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    out_dir = (args.out_dir or (repo_root / "reports" / "audit")).resolve()
    if not args.quiet and not args.json:
        print("Classifying ZSDL corpus under {}".format(repo_root / "zspecs"), file=sys.stderr)

    report = build_report(
        repo_root,
        zspecs_dir=args.zspecs_dir,
        registry_path=args.registry,
        progress=not args.quiet and not args.json,
    )

    if args.check:
        return check_committed(report, out_dir)

    if args.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    write_reports(report, out_dir)
    s = report["summary"]
    print(
        "Wrote {} specs → {} (withdrawn {}, gold-set candidates {}, errors {})".format(
            s["spec_count"],
            out_dir,
            s["withdrawn_from_qualification"],
            s["gold_set_candidates"],
            s["compile_errors"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
