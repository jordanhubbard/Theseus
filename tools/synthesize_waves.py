#!/usr/bin/env python3
"""
synthesize_waves.py — Wave-based clean-room synthesis over all ZSDL specs.

Processes specs in named waves that mirror the structure of spec *creation*
(see PLAN.md — Wave Series section).  State is persisted after each spec so
runs can be interrupted and resumed.  Each completed wave is summarised and
the state file is updated so the next wave picks up where the last left off.

Wave tiers
----------
Tier 1  s1–s2   Core Python stdlib (original PLAN.md Cycles 1-16 specs)
Tier 2  s3      Python C extension equivalents (synthesised as pure Python)
Tier 3  s4      CLI-backend specs  (Python wrapper scripts)
Tier 4  s5      Node.js-backend specs  (index.js)
Tier 5  s6      ctypes C libraries — simple
Tier 6  s7      ctypes C libraries — hard / expected-infeasible
Tier 7  w<N>    ZSDL wave-series specs, one synthesis wave per ZSDL wave
                (group by _extraNNNN or auto-batched prefix groups)

Usage
-----
  python3 tools/synthesize_waves.py --list
  python3 tools/synthesize_waves.py --wave s1
  python3 tools/synthesize_waves.py --next
  python3 tools/synthesize_waves.py --status
  python3 tools/synthesize_waves.py --reset-wave s1

Exit codes
----------
  0   Wave(s) ran; all specs succeeded
  1   Wave(s) ran; at least one spec failed / partial / infeasible
  2   Setup error (no specs, bad wave name, etc.)
  3   LLM not available
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import theseus.agent as agent_mod
import theseus.config as config_mod
from theseus.pipeline import PipelineResult, ZSpecPipeline
from theseus.synthesis.annotate import zsdl_path_for_spec_json
from theseus.synthesis.runner import SynthesisResult, SynthesisRunner

_BUILD_ZSPECS = _REPO_ROOT / "_build" / "zspecs"
_STATE_FILE = _REPO_ROOT / "reports" / "synthesis" / "wave_state.json"
_AUDIT_DIR = _REPO_ROOT / "reports" / "synthesis"

# ---------------------------------------------------------------------------
# Wave plan — Tier 1-6 (named, curated)
# ---------------------------------------------------------------------------

#: Each entry: name, title, and a ``match`` predicate.
#: match["names"]          — exact canonical_name list
#: match["backend"]        — library.backend field value
#: match["backend_lang"]   — synthesized backend_lang (python / c / javascript)
#: match["prefix_re"]      — regex on canonical_name
#:
#: Tier 7 waves are discovered dynamically from _extraNNNN groups.

_TIER1_7_WAVES: list[dict] = [
    # ------------------------------------------------------------------
    # Tier 1 — Core ZSDL specs, original Cycles 1-16
    # ------------------------------------------------------------------
    {
        "name": "s1",
        "title": "Core Python stdlib — simple (base64, json, struct, datetime, pathlib, re, urllib_parse, difflib)",
        "match": {"names": ["base64", "json", "struct", "datetime", "pathlib",
                            "re", "urllib_parse", "difflib"]},
    },
    {
        "name": "s2",
        "title": "Core Python stdlib — complex (hashlib, sqlite3, urllib3, numpy, pyyaml, lxml, packaging)",
        "match": {"names": ["hashlib", "sqlite3", "urllib3", "numpy", "pyyaml",
                            "lxml", "packaging", "pillow", "psutil", "pygments",
                            "markupsafe", "msgpack", "attrs", "chardet", "pyparsing",
                            "tomli", "six", "decorator", "idna", "platformdirs",
                            "pytz", "setuptools", "typing_extensions", "tzdata",
                            "wrapt", "pluggy", "certifi", "colorama", "more_itertools",
                            "fsspec", "dotenv", "pathspec", "filelock", "traitlets",
                            "tomlkit", "defusedxml", "distro", "docutils", "isodate",
                            "markdown", "stevedore", "dns", "networkx", "tornado",
                            "zope_interface", "fontTools", "protobuf"]},
    },
    # ------------------------------------------------------------------
    # Tier 2 — Python C extension equivalents (synthesised as pure Python)
    # ------------------------------------------------------------------
    {
        "name": "s3",
        "title": "Python C extension equivalents as pure Python",
        "match": {"names": ["_bisect", "_csv", "_datetime", "_decimal", "_hashlib",
                            "_heapq", "_io", "_json", "_pickle", "_socket", "_ssl",
                            "_struct", "_thread", "_weakref"]},
    },
    # ------------------------------------------------------------------
    # Tier 3 — CLI backends
    # ------------------------------------------------------------------
    {
        "name": "s4",
        "title": "CLI backends (curl, openssl, jq, and other non-node CLI specs)",
        "match": {"backend": "cli", "exclude_backend_lang": "javascript"},
    },
    # ------------------------------------------------------------------
    # Tier 4 — Node.js backends
    # ------------------------------------------------------------------
    {
        "name": "s5",
        "title": "Node.js backends (semver, uuid, minimist, ajv, chalk, lodash, express, prettier, …)",
        "match": {"backend_lang": "javascript"},
    },
    # ------------------------------------------------------------------
    # Tier 5 — ctypes C libraries — simpler / smaller APIs
    # ------------------------------------------------------------------
    {
        "name": "s6",
        "title": "ctypes C libraries — simple (zstd, lz4, libcrypto)",
        "match": {"names": ["zstd", "lz4", "libcrypto"]},
    },
    # ------------------------------------------------------------------
    # Tier 6 — ctypes C libraries — hard / expected-infeasible
    # ------------------------------------------------------------------
    {
        "name": "s7",
        "title": "ctypes C libraries — complex/hard (zlib, pcre2, libpng, libsodium, libxml2, libyaml, expat)",
        "match": {"names": ["zlib", "pcre2", "libpng", "libsodium", "libxml2",
                            "libyaml", "expat"]},
    },
]


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    """Load wave_state.json; return empty structure if missing."""
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"specs": {}, "waves_completed": []}


def _save_state(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _record_spec_result(state: dict, result: SynthesisResult) -> None:
    """Upsert a SynthesisResult into state["specs"]."""
    state["specs"][result.canonical_name] = {
        "status": result.status,
        "backend_lang": result.backend_lang,
        "attempted_at": result.attempted_at,
        "iterations": result.iterations,
        "pass_count": result.final_pass_count,
        "fail_count": result.final_fail_count,
        "total_invariants": result.total_invariants,
        "notes": result.notes,
        "infeasible_reason": result.infeasible_reason,
    }


# ---------------------------------------------------------------------------
# Spec discovery helpers
# ---------------------------------------------------------------------------

def _all_spec_paths() -> list[Path]:
    if not _BUILD_ZSPECS.is_dir():
        return []
    return sorted(_BUILD_ZSPECS.glob("*.zspec.json"))


def _load_spec_meta(path: Path) -> dict:
    """Return lightweight metadata dict for a spec (no invariants list)."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    lib = d.get("library", {})
    from theseus.synthesis.build import backend_lang_for_spec
    return {
        "canonical_name": d.get("identity", {}).get("canonical_name", path.stem.replace(".zspec", "")),
        "backend": lib.get("backend", "ctypes"),
        "backend_lang": backend_lang_for_spec(lib),
        "invariant_count": len(d.get("invariants", [])),
        "path": path,
    }


def _all_spec_metas() -> list[dict]:
    """Return metadata for every compiled spec."""
    result = []
    for p in _all_spec_paths():
        m = _load_spec_meta(p)
        if m:
            result.append(m)
    return result


# ---------------------------------------------------------------------------
# Wave resolution
# ---------------------------------------------------------------------------

def _match_spec(meta: dict, match: dict) -> bool:
    """Return True if *meta* satisfies *match* predicate dict."""
    if "names" in match:
        if meta["canonical_name"] not in match["names"]:
            return False
    if "backend" in match:
        if meta["backend"] != match["backend"]:
            return False
    if "backend_lang" in match:
        if meta["backend_lang"] != match["backend_lang"]:
            return False
    if "exclude_backend_lang" in match:
        if meta["backend_lang"] == match["exclude_backend_lang"]:
            return False
    if "prefix_re" in match:
        if not re.search(match["prefix_re"], meta["canonical_name"]):
            return False
    return True


def _discover_zsdl_wave_groups() -> list[dict]:
    """
    Discover Tier-7 waves from specs with _extraNNNN suffixes.

    Each distinct NNNN value = one ZSDL wave → one synthesis wave named
    ``w<NNNN>`` (e.g. ``w3346``, ``w3361``, …).
    Returns a list of wave dicts sorted by wave number.
    """
    groups: dict[int, list[str]] = defaultdict(list)
    for p in _all_spec_paths():
        name = p.stem.replace(".zspec", "")
        m = re.search(r"_extra(\d{3,})", name)  # 3+ digits to avoid _extra, _extra2 etc.
        if m:
            groups[int(m.group(1))].append(name)

    waves = []
    for num in sorted(groups):
        names = sorted(groups[num])
        waves.append({
            "name": f"w{num}",
            "title": f"ZSDL wave-series _extra{num} ({len(names)} specs: {', '.join(names[:4])}{'…' if len(names) > 4 else ''})",
            "match": {"names": names},
        })
    return waves


def _build_wave_list() -> list[dict]:
    """Return the full ordered wave list (Tier 1-6 + discovered Tier-7)."""
    return _TIER1_7_WAVES + _discover_zsdl_wave_groups()


def _resolve_wave(wave_name: str, wave_list: list[dict]) -> dict | None:
    """Find a wave by name (case-insensitive)."""
    for w in wave_list:
        if w["name"].lower() == wave_name.lower():
            return w
    return None


def _specs_for_wave(wave: dict, all_metas: list[dict]) -> list[dict]:
    """Return the spec metas belonging to *wave*, in stable order."""
    match = wave["match"]
    matched = [m for m in all_metas if _match_spec(m, match)]
    # Stable sort: by canonical_name
    return sorted(matched, key=lambda m: m["canonical_name"])


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(wave_list: list[dict], all_metas: list[dict], state: dict) -> int:
    """Print all waves, their spec counts, and completion status."""
    done_waves = set(state.get("waves_completed", []))
    spec_states = state.get("specs", {})

    print(f"{'Wave':<10} {'Specs':>5} {'Done':>5} {'Pass':>5} {'Fail':>5}  Status   Title")
    print("-" * 90)
    for w in wave_list:
        specs = _specs_for_wave(w, all_metas)
        total = len(specs)
        if total == 0:
            continue
        done = sum(1 for m in specs if m["canonical_name"] in spec_states)
        passing = sum(1 for m in specs
                      if spec_states.get(m["canonical_name"], {}).get("status") == "success")
        failing = sum(1 for m in specs
                      if spec_states.get(m["canonical_name"], {}).get("status") in
                         ("failed", "partial", "build_failed"))
        if w["name"] in done_waves:
            status_label = "DONE"
        elif done > 0:
            status_label = "partial"
        else:
            status_label = "pending"
        print(f"{w['name']:<10} {total:>5} {done:>5} {passing:>5} {failing:>5}  {status_label:<8} {w['title'][:55]}")
    return 0


def cmd_status(wave_list: list[dict], all_metas: list[dict], state: dict) -> int:
    """Print per-spec status for all processed specs."""
    spec_states = state.get("specs", {})
    if not spec_states:
        print("No specs have been synthesised yet. Run --next or --wave <name>.")
        return 0

    by_status: dict[str, list[str]] = defaultdict(list)
    for name, info in sorted(spec_states.items()):
        by_status[info["status"]].append(name)

    total = len(spec_states)
    print(f"Synthesised specs: {total}")
    for st in ["success", "partial", "failed", "build_failed", "infeasible"]:
        names = by_status.get(st, [])
        if names:
            print(f"\n  {st.upper()} ({len(names)}):")
            for n in names:
                info = spec_states[n]
                print(f"    {n:40s} {info.get('pass_count',0):3d}p/{info.get('fail_count',0):3d}f")
    return 0


def cmd_reset_wave(wave_name: str, wave_list: list[dict], all_metas: list[dict],
                   state: dict) -> int:
    """Clear state for all specs in a wave so it runs fresh."""
    wave = _resolve_wave(wave_name, wave_list)
    if wave is None:
        print(f"error: unknown wave {wave_name!r}", file=sys.stderr)
        return 2
    specs = _specs_for_wave(wave, all_metas)
    cleared = 0
    for m in specs:
        if m["canonical_name"] in state["specs"]:
            del state["specs"][m["canonical_name"]]
            cleared += 1
    if wave_name in state.get("waves_completed", []):
        state["waves_completed"].remove(wave_name)
    _save_state(state)
    print(f"Cleared {cleared} spec entries for wave {wave_name!r}.")
    return 0


def cmd_run_wave(
    wave: dict,
    all_metas: list[dict],
    state: dict,
    ai_cfg: dict,
    *,
    max_iterations: int,
    jobs: int,
    no_annotate: bool,
    verbose: bool,
    llm_timeout: int,
    force: bool,
) -> int:
    """
    Run the full ZSpec pipeline for every spec in *wave*.

    Each spec goes through: compile → verify_real → synthesize → gate → annotate.
    Specs that have already reached a terminal state (success / infeasible) are
    skipped unless --force is given.
    """
    specs = _specs_for_wave(wave, all_metas)
    if not specs:
        print(f"No specs found for wave {wave['name']!r}.")
        return 2

    spec_states = state.setdefault("specs", {})
    pending = [
        m for m in specs
        if force or m["canonical_name"] not in spec_states
        or spec_states[m["canonical_name"]]["status"] in ("failed", "partial", "build_failed")
    ]

    already_done = len(specs) - len(pending)
    print(f"\n=== Wave {wave['name']}: {wave['title']} ===")
    print(f"  {len(specs)} spec(s) total  |  {already_done} already done  |  {len(pending)} to run")

    if not pending:
        print("  Nothing to do — all specs already synthesised. Use --force to re-run.")
        return 0

    work_base = Path(tempfile.gettempdir()) / "theseus-synthesis"
    work_base.mkdir(parents=True, exist_ok=True)

    # Build the pipeline once; it is reused for every spec in this wave.
    pipeline = ZSpecPipeline(
        max_iterations=max_iterations,
        work_dir=work_base,
        annotate=not no_annotate,
        # Real-library verification is skipped here because the wave runner
        # processes specs in bulk — many may target libraries not installed on
        # the current machine.  Callers that need per-spec real-verify should
        # use run_pipeline.py directly.
        skip_real_verify=True,
        gate_on_synthesis=True,
        ai_cfg=ai_cfg,
        verbose=verbose,
        llm_timeout=llm_timeout,
    )

    results: list[SynthesisResult] = []

    for i, meta in enumerate(pending, 1):
        name = meta["canonical_name"]
        print(f"  [{i}/{len(pending)}] {name} …", end=" ", flush=True)

        # Prefer the .zsdl source so the pipeline can re-compile + synthesize
        # in one shot.  Fall back to synthesis-only on the compiled spec when
        # the source is not present (e.g. hand-imported specs).
        zsdl_path = zsdl_path_for_spec_json(meta["path"])

        if zsdl_path.exists():
            pr: PipelineResult = pipeline.run(zsdl_path)
            result = pr.synthesis_result
            if result is None:
                # Pipeline stopped before synthesis (compile error, etc.)
                result = SynthesisResult(
                    canonical_name=name,
                    backend_lang=meta["backend_lang"],
                    status="infeasible",
                    model="",
                    attempted_at="",
                    iterations=0,
                    notes=f"Pipeline stopped at step: {pr.outcome}",
                    infeasible_reason="pipeline_error",
                )
        else:
            # No .zsdl source — run synthesis-only on the pre-compiled spec.
            runner = SynthesisRunner(
                ai_cfg,
                max_iterations=max_iterations,
                verbose=verbose,
                llm_timeout=llm_timeout,
            )
            try:
                spec = json.loads(meta["path"].read_text(encoding="utf-8"))
                result = runner.run(spec, meta["path"], work_base)
            except Exception as exc:
                result = SynthesisResult(
                    canonical_name=name,
                    backend_lang=meta["backend_lang"],
                    status="infeasible",
                    model="",
                    attempted_at="",
                    iterations=0,
                    notes=f"Runner exception: {exc}",
                    infeasible_reason="runner_exception",
                )

        print(
            f"{result.status}"
            + (f" ({result.final_pass_count}/{result.total_invariants})"
               if result.total_invariants else "")
        )

        _record_spec_result(state, result)
        _save_state(state)   # persist after every spec

        results.append(result)

    # Wave-level summary
    _print_wave_summary(wave["name"], results)

    # Mark wave complete when no specs remain in a retryable state.
    remaining = [
        m for m in specs
        if spec_states.get(m["canonical_name"], {}).get("status")
           in ("failed", "partial", "build_failed", None)
    ]
    if not remaining:
        completed = state.setdefault("waves_completed", [])
        if wave["name"] not in completed:
            completed.append(wave["name"])
        _save_state(state)
        print(f"  Wave {wave['name']} marked complete.")

    any_bad = any(r.status in ("failed", "partial", "build_failed") for r in results)
    return 1 if any_bad else 0



def _print_wave_summary(wave_name: str, results: list[SynthesisResult]) -> None:
    by_status: dict[str, int] = defaultdict(int)
    total_pass = total_fail = 0
    for r in results:
        by_status[r.status] += 1
        total_pass += r.final_pass_count
        total_fail += r.final_fail_count
    parts = "  ".join(f"{st}={n}" for st, n in sorted(by_status.items()))
    print(
        f"\n  Wave {wave_name} summary: {len(results)} run  |  "
        f"{parts}  |  {total_pass}p/{total_fail}f invariants"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave-based clean-room synthesis over all ZSDL specs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true",
                      help="List all waves with spec counts and current status.")
    mode.add_argument("--wave", metavar="NAME",
                      help="Run a specific wave (e.g. s1, s2, w3346).")
    mode.add_argument("--next", action="store_true",
                      help="Run the next wave that has pending specs.")
    mode.add_argument("--status", action="store_true",
                      help="Show per-spec synthesis status.")
    mode.add_argument("--reset-wave", metavar="NAME",
                      help="Clear all state for a wave so it re-runs from scratch.")

    parser.add_argument("--max-iterations", type=int, default=3, metavar="N",
                        help="Max LLM iterations per spec (default: 3).")
    parser.add_argument("--jobs", type=int, default=1, metavar="N",
                        help="Parallel workers (default: 1; LLM rate limits apply).")
    parser.add_argument("--timeout", type=int, default=0, metavar="SECONDS",
                        help="LLM timeout per spec in seconds (0 = provider default).")
    parser.add_argument("--no-annotate", action="store_true",
                        help="Skip writing results back to .zspec.zsdl files.")
    parser.add_argument("--verbose", action="store_true",
                        help="Stream verify_behavior.py output.")
    parser.add_argument("--force", action="store_true",
                        help="Re-run specs even if they already have a state entry.")
    parser.add_argument("--config", type=Path, default=None, metavar="PATH",
                        help="Path to config.yaml.")

    args = parser.parse_args(argv)

    # --- Build wave list and load all spec metas ---
    all_metas = _all_spec_metas()
    if not all_metas and not args.list and not args.status:
        print("error: no compiled specs found. Run 'make compile-zsdl' first.", file=sys.stderr)
        return 2

    wave_list = _build_wave_list()
    state = _load_state()

    # --- List / status / reset don't need LLM ---
    if args.list:
        return cmd_list(wave_list, all_metas, state)
    if args.status:
        return cmd_status(wave_list, all_metas, state)
    if args.reset_wave:
        return cmd_reset_wave(args.reset_wave, wave_list, all_metas, state)

    # --- LLM required from here ---
    cfg = config_mod.load(args.config)
    ai_cfg = cfg.get("ai", {})
    if not agent_mod.available(ai_cfg):
        print(
            "error: no LLM provider configured. Install the claude CLI or set "
            "ai.openai_base_url in config.yaml.",
            file=sys.stderr,
        )
        return 3

    if args.wave:
        wave = _resolve_wave(args.wave, wave_list)
        if wave is None:
            print(f"error: unknown wave {args.wave!r}. Use --list to see all waves.", file=sys.stderr)
            return 2
        return cmd_run_wave(
            wave, all_metas, state, ai_cfg,
            max_iterations=args.max_iterations,
            jobs=args.jobs,
            no_annotate=args.no_annotate,
            verbose=args.verbose,
            llm_timeout=args.timeout,
            force=args.force,
        )

    if args.next:
        spec_states = state.get("specs", {})
        done_waves = set(state.get("waves_completed", []))
        for wave in wave_list:
            if wave["name"] in done_waves:
                continue
            specs = _specs_for_wave(wave, all_metas)
            if not specs:
                continue
            pending = [
                m for m in specs
                if m["canonical_name"] not in spec_states
                or spec_states[m["canonical_name"]]["status"] in ("failed", "partial", "build_failed")
            ]
            if pending:
                print(f"Next wave: {wave['name']} — {wave['title']}")
                return cmd_run_wave(
                    wave, all_metas, state, ai_cfg,
                    max_iterations=args.max_iterations,
                    jobs=args.jobs,
                    no_annotate=args.no_annotate,
                    verbose=args.verbose,
                    llm_timeout=args.timeout,
                    force=args.force,
                )
        print("All waves complete! Use --status to review results.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
