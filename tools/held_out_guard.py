#!/usr/bin/env python3
"""
held_out_guard.py — Fail if a synthesis prompt leaks held-out oracle tokens.

Usage:
  python3 tools/held_out_guard.py
  python3 tools/held_out_guard.py --spec zspecs/theseus_json.zspec.zsdl \\
      --held-out gold/json/held_out.zspec.zsdl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools"))

import zsdl_compile  # noqa: E402
from theseus.synthesis.prompt import PromptBuilder  # noqa: E402

DEFAULT_SPEC = _REPO_ROOT / "zspecs" / "theseus_json.zspec.zsdl"
DEFAULT_HELD_OUT = _REPO_ROOT / "gold" / "json" / "held_out.zspec.zsdl"

# Extra distinctive strings from the JSON held-out file. Keep these out of
# gold/json/package.md and zspecs/theseus_json.zspec.zsdl.
_JSON_SPIKE_TOKENS = (
    "1.5e2",
    "café",
    "caf\\u00e9",
    "[1,]",
    "\\u0041",
    'say "hi"',
    "{]",
)

_SKIP_SPEC_KEYS = frozenset({"function", "expected_exception"})


def _walk_strings(value, out):
    if isinstance(value, str):
        if value:
            out.append(value)
        return
    if isinstance(value, list):
        for item in value:
            _walk_strings(item, out)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SKIP_SPEC_KEYS:
                continue
            _walk_strings(item, out)


def tokens_from_compiled(compiled):
    """Collect argument/expected strings from a compiled spec's invariants."""
    found = []
    for inv in compiled.get("invariants") or []:
        spec = inv.get("spec") or {}
        _walk_strings(spec.get("args"), found)
        _walk_strings(spec.get("expected"), found)
        _walk_strings(spec.get("kwargs"), found)
        ident = inv.get("id") or ""
        if "held_out" in ident:
            found.append(ident)
    tokens = []
    seen = set()
    for raw in found:
        if raw in seen:
            continue
        seen.add(raw)
        if len(raw) < 3:
            continue
        tokens.append(raw)
    return tokens


def distinctive_tokens(held_compiled, public_compiled=None):
    """Held-out strings that are not also in the public oracle."""
    held = set(tokens_from_compiled(held_compiled))
    public = set(tokens_from_compiled(public_compiled or {}))
    distinctive = [token for token in held if token not in public]
    seen = set(distinctive)
    for extra in _JSON_SPIKE_TOKENS:
        if extra not in seen:
            distinctive.append(extra)
            seen.add(extra)
    return distinctive


def synthesis_prompt_text(compiled):
    system, user = PromptBuilder().initial_prompt(
        compiled, compiled.get("backend_lang") or "python_cleanroom"
    )
    return system + "\n" + user


def leaked_tokens(prompt, tokens):
    leaks = []
    for token in tokens:
        if token in prompt:
            leaks.append(token)
    return leaks


def check(spec_path, held_out_path):
    compiler = zsdl_compile.ZSDLCompiler()
    public = compiler.compile_file(Path(spec_path))
    held = compiler.compile_file(Path(held_out_path))
    prompt = synthesis_prompt_text(public)
    return leaked_tokens(prompt, distinctive_tokens(held, public))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fail if held-out oracle tokens leak into a synthesis prompt"
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--held-out", type=Path, default=DEFAULT_HELD_OUT)
    args = parser.parse_args(argv)
    leaks = check(args.spec, args.held_out)
    if leaks:
        print("held-out tokens leaked into synthesis prompt:", file=sys.stderr)
        for token in leaks:
            print("  " + repr(token), file=sys.stderr)
        return 1
    print("held-out guard: no leaks ({} vs {})".format(args.spec, args.held_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
