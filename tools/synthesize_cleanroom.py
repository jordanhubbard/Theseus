#!/usr/bin/env python3
"""
synthesize_cleanroom.py — LLM-driven clean-room package synthesis.

Given a compiled spec with backend_lang=python_cleanroom or node_cleanroom,
asks the LLM to produce a complete reimplementation, then verifies it using
the isolation harness in cleanroom_verify.py.

No imports of the original package are allowed in the implementation.
Only Python stdlib (or Node built-ins) may be used.

Usage:
  python3 tools/synthesize_cleanroom.py _build/zspecs/theseus_json.zspec.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import theseus.agent as agent_mod
import theseus.config as config_mod
from theseus.synthesis.prompt import PromptBuilder
from theseus.synthesis.runner import SynthesisResult
from tools.cleanroom_verify import verify as _verify

_CLEANROOM_PYTHON = _REPO_ROOT / "cleanroom" / "python"
_CLEANROOM_NODE   = _REPO_ROOT / "cleanroom" / "node"

# ---------------------------------------------------------------------------
# System prompt — enforces clean-room constraints
# ---------------------------------------------------------------------------

_PY_SYSTEM_PROMPT = """\
You are implementing a Python package from a behavioral specification as part of the Theseus \
clean-room rewrite initiative.

HARD RULES — any violation causes immediate rejection:
1. Do NOT import the package being replaced. If the spec is named `theseus_json`, do NOT \
`import json` or `import simplejson` or any other JSON library.
2. Do NOT import any third-party library. Only Python standard library built-ins are allowed \
(os, sys, re, struct, math, etc.).
3. Exception: you MAY import other Theseus-verified packages if they are explicitly listed \
in the spec notes as allowed dependencies.
4. Do NOT use subprocess to call external tools.
5. The implementation must be entirely self-contained — no network calls, no file I/O beyond \
what the invariants require.

OUTPUT FORMAT — required:
Produce the implementation as a single Python file using this exact XML wrapper:

<file name="__init__.py"><content>
# your implementation here
</content></file>

The file must export every function named in the invariants.
"""

_NODE_SYSTEM_PROMPT = """\
You are implementing a Node.js package from a behavioral specification as part of the Theseus \
clean-room rewrite initiative.

HARD RULES — any violation causes immediate rejection:
1. Do NOT require() the package being replaced.
2. Do NOT require() any npm package.
3. Only Node.js built-in modules are allowed — but NOT the module being replaced \
(e.g., if replacing 'path', do NOT require('path')).
4. Do NOT use child_process to call external tools.
5. The implementation must be entirely self-contained.

OUTPUT FORMAT — required:
Produce the implementation as a single JavaScript file using this exact XML wrapper:

<file name="index.js"><content>
// your implementation here
</content></file>

The file must export every function named in the invariants via module.exports.
"""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_initial_prompt(spec: dict, lang: str) -> str:
    name = spec["identity"]["canonical_name"]
    notes = spec.get("provenance", {}).get("notes", [])
    invs = spec.get("invariants", [])

    inv_lines = []
    for inv in invs:
        s = inv.get("spec", {})
        fn = s.get("function", "?")
        args = s.get("args", [])
        exp = s.get("expected", "?")
        inv_lines.append(f"  - {fn}({json.dumps(args)[1:-1]}) → {json.dumps(exp)}")

    notes_text = "\n".join(f"  * {n}" for n in notes) if notes else "  (none)"

    if lang == "python_cleanroom":
        file_hint = f"`cleanroom/python/{name}/__init__.py`"
        ext = "Python"
    else:
        file_hint = f"`cleanroom/node/{name}/index.js`"
        ext = "JavaScript"

    return (
        f"Package: {name}\n"
        f"Language: {ext} (clean-room, no wrapping of the original)\n\n"
        f"Context notes:\n{notes_text}\n\n"
        f"Invariants to satisfy:\n" + "\n".join(inv_lines) + "\n\n"
        f"Write a complete implementation at {file_hint} that exports all required functions.\n"
        f"Do NOT import the original package. Implement everything from scratch.\n"
    )


def _build_revision_prompt(spec: dict, lang: str, prev_source: str, failures: list[dict], iteration: int) -> str:
    name = spec["identity"]["canonical_name"]
    failure_lines = "\n".join(
        f"  - {f['invariant']}: {f['error'][:300]}" for f in failures
    )
    return (
        f"Package: {name} — iteration {iteration} revision\n\n"
        f"Previous implementation produced these failures:\n{failure_lines}\n\n"
        f"Previous implementation:\n```\n{prev_source}\n```\n\n"
        f"Fix the failures. Do NOT import the original package. Output using the <file> XML format.\n"
    )


# ---------------------------------------------------------------------------
# Core synthesis loop
# ---------------------------------------------------------------------------

def synthesize(spec_json_path: str, ai_cfg: dict | None = None, max_iterations: int = 3) -> SynthesisResult:
    path = Path(spec_json_path)
    spec = json.loads(path.read_text())
    name = spec["identity"]["canonical_name"]
    lang = spec.get("backend_lang", "")
    total_invariants = len(spec.get("invariants", []))
    attempted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if ai_cfg is None:
        ai_cfg = config_mod.load().get("ai", {})

    try:
        model = ai_cfg.get("model", "unknown")
    except Exception:
        model = "unknown"

    if lang == "python_cleanroom":
        out_dir = _CLEANROOM_PYTHON / name
        system_prompt = _PY_SYSTEM_PROMPT
        impl_file = "__init__.py"
    elif lang == "node_cleanroom":
        out_dir = _CLEANROOM_NODE / name
        system_prompt = _NODE_SYSTEM_PROMPT
        impl_file = "index.js"
    else:
        return SynthesisResult(
            canonical_name=name,
            backend_lang=lang,
            status="infeasible",
            model=model,
            attempted_at=attempted_at,
            iterations=0,
            notes=f"Not a cleanroom spec: backend_lang={lang!r}",
            infeasible_reason="wrong_backend",
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    prev_source = ""
    last_result: dict | None = None

    for iteration in range(1, max_iterations + 1):
        # Build prompt
        if iteration == 1:
            user_prompt = _build_initial_prompt(spec, lang)
        else:
            failures = last_result.get("errors", []) if last_result else []
            user_prompt = _build_revision_prompt(spec, lang, prev_source, failures, iteration)

        # Call LLM
        try:
            llm_response = agent_mod.run_prompt(user_prompt, ai_cfg, system=system_prompt)
        except RuntimeError as exc:
            return SynthesisResult(
                canonical_name=name,
                backend_lang=lang,
                status="infeasible",
                model=model,
                attempted_at=attempted_at,
                iterations=iteration,
                notes=f"LLM unavailable: {exc}",
                infeasible_reason="llm_unavailable",
            )

        # Extract source file from LLM response
        try:
            source_files = PromptBuilder.extract_source_files(llm_response)
        except ValueError:
            source_files = {}

        impl_content = source_files.get(impl_file, "")
        if not impl_content:
            # Try to recover raw code block
            import re
            m = re.search(r"```(?:python|javascript|js)?\n(.*?)```", llm_response, re.DOTALL)
            if m:
                impl_content = m.group(1).strip()

        if not impl_content:
            last_result = {"pass": 0, "fail": total_invariants,
                           "errors": [{"invariant": "ALL", "error": "LLM produced no parseable source file"}]}
            continue

        # Write implementation
        (out_dir / impl_file).write_text(impl_content)
        prev_source = impl_content

        # Verify in isolation
        last_result = _verify(spec_json_path)

        if last_result["fail"] == 0:
            return SynthesisResult(
                canonical_name=name,
                backend_lang=lang,
                status="success",
                model=model,
                attempted_at=attempted_at,
                iterations=iteration,
                final_pass_count=last_result["pass"],
                final_fail_count=0,
                total_invariants=total_invariants,
                notes=f"Clean-room synthesis succeeded in {iteration} iteration(s). {last_result['pass']} invariants passing.",
            )

    # All iterations failed
    fail_details = {
        e["invariant"]: {"status": "failed", "reason": e["error"]}
        for e in (last_result.get("errors", []) if last_result else [])
    }
    final_pass = last_result.get("pass", 0) if last_result else 0
    final_fail = last_result.get("fail", total_invariants) if last_result else total_invariants

    return SynthesisResult(
        canonical_name=name,
        backend_lang=lang,
        status="failed" if final_pass > 0 else "failed",
        model=model,
        attempted_at=attempted_at,
        iterations=max_iterations,
        final_pass_count=final_pass,
        final_fail_count=final_fail,
        total_invariants=total_invariants,
        notes=f"Clean-room synthesis failed after {max_iterations} iteration(s). {final_fail} invariants still failing.",
        failed_invariant_details=fail_details,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Synthesize a clean-room package implementation")
    parser.add_argument("spec_json", help="Compiled .zspec.json path")
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()

    result = synthesize(args.spec_json, max_iterations=args.iterations)
    print(f"  {result.canonical_name}: {result.status} ({result.final_pass_count}/{result.total_invariants})")
    if result.notes:
        print(f"  {result.notes}")
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
