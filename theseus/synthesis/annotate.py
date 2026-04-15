"""
theseus/synthesis/annotate.py

Writes synthesis results back into the .zspec.zsdl source file.

Strategy:
  - Append a ``synthesis:`` YAML block at the end of the file.
  - Never rewrite existing spec content — preserve custom YAML tags, comments, etc.
  - Use hand-formatted string interpolation (not PyYAML dump) so we never disturb
    ZSDL-specific tags like !b64, !hex, !ascii, !tuple.
  - If a synthesis block already exists, raise unless overwrite_existing=True.
  - The compiled .zspec.json already passes unknown top-level keys through
    (additionalProperties: true), so no compiler changes are needed.
"""
from __future__ import annotations

import re
from pathlib import Path

from theseus.synthesis.runner import SynthesisResult


# Marker we look for to detect an existing synthesis block.
_SYNTH_MARKER = "\nsynthesis:"
_SYNTH_MARKER_START = "synthesis:"  # catches files that start with it
# Full block start (including the preceding comment banner) used for truncation
# so that overwrite does not accumulate duplicate comment lines.
_SYNTH_BLOCK_START = "\n# ── Synthesis layer annotation "


class SynthesisAnnotator:
    """Appends a ``synthesis:`` block to a .zspec.zsdl file."""

    def annotate(
        self,
        zsdl_path: Path,
        result: SynthesisResult,
        *,
        overwrite_existing: bool = False,
    ) -> None:
        """
        Append synthesis metadata to the ZSDL source file.

        Args:
            zsdl_path: path to the .zspec.zsdl file.
            result: SynthesisResult from the synthesis loop.
            overwrite_existing: if True, replace an existing synthesis block;
                if False (default), raise ValueError if one already exists.

        Raises:
            FileNotFoundError: if zsdl_path does not exist.
            ValueError: if a synthesis block already exists and
                overwrite_existing is False.
        """
        if not zsdl_path.exists():
            raise FileNotFoundError(f"ZSDL file not found: {zsdl_path}")

        existing = zsdl_path.read_text(encoding="utf-8")
        has_block = _SYNTH_MARKER in existing or existing.lstrip().startswith(
            _SYNTH_MARKER_START
        )

        if has_block:
            if not overwrite_existing:
                raise ValueError(
                    f"A synthesis: block already exists in {zsdl_path}. "
                    "Pass overwrite_existing=True to replace it."
                )
            # Truncate before the block's comment banner (if present) so we
            # don't accumulate duplicate header lines on repeated overwrites.
            idx = existing.find(_SYNTH_BLOCK_START)
            if idx == -1:
                # No comment banner — fall back to just before synthesis:
                idx = existing.find(_SYNTH_MARKER)
            if idx == -1:
                # Block is at the very start — just overwrite the whole file.
                existing = ""
            else:
                existing = existing[:idx]

        block = _build_synthesis_block(result)
        zsdl_path.write_text(existing + block, encoding="utf-8")


def zsdl_path_for_spec_json(spec_json_path: Path) -> Path:
    """
    Derive the .zspec.zsdl source path from a compiled .zspec.json path.

    Example:
        _build/zspecs/zlib.zspec.json  →  zspecs/zlib.zspec.zsdl
    """
    repo_root = _find_repo_root(spec_json_path)
    # The compiled JSON lives at _build/zspecs/<name>.zspec.json
    # Strip the _build/ prefix to get zspecs/<name>.zspec.json, then .zsdl
    parts = spec_json_path.parts
    try:
        build_idx = parts.index("_build")
        rel_parts = parts[build_idx + 1:]  # zspecs/<name>.zspec.json
    except ValueError:
        # Fall back: just change suffix
        rel_parts = (spec_json_path.name,)

    zsdl_rel = Path(*rel_parts).with_suffix(".zsdl")
    return repo_root / zsdl_rel


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_repo_root(start: Path) -> Path:
    """Walk up from *start* to find the directory containing Makefile."""
    candidate = start.resolve()
    for _ in range(10):
        if (candidate / "Makefile").exists():
            return candidate
        candidate = candidate.parent
    return start.resolve().parent.parent


def _build_synthesis_block(result: SynthesisResult) -> str:
    """Render a synthesis: YAML block as a string to append to the ZSDL file."""
    lines: list[str] = []
    lines.append("")
    lines.append("# ── Synthesis layer annotation " + "─" * 47)
    lines.append("synthesis:")
    lines.append(f"  status: {result.status}")
    lines.append(f"  model: {result.model}")
    lines.append(f"  attempted_at: {result.attempted_at}")
    lines.append(f"  iterations: {result.iterations}")
    lines.append(f"  pass_count: {result.final_pass_count}")
    lines.append(f"  fail_count: {result.final_fail_count}")
    lines.append(f"  total_invariants: {result.total_invariants}")
    lines.append(f"  notes: {_yaml_str(result.notes)}")

    if result.infeasible_reason is None:
        lines.append("  infeasible_reason: null")
    else:
        lines.append(f"  infeasible_reason: {_yaml_str(result.infeasible_reason)}")

    if result.failed_invariant_details:
        lines.append("  invariant_annotations:")
        for inv_id, detail in result.failed_invariant_details.items():
            lines.append(f"    {_yaml_str(inv_id)}:")
            lines.append(f"      status: {detail.get('status', 'failed')}")
            lines.append(f"      reason: {_yaml_str(detail.get('reason', ''))}")
    else:
        lines.append("  invariant_annotations: {}")

    lines.append("")  # trailing newline
    return "\n".join(lines)


def _yaml_str(value: str) -> str:
    """
    Render a string value as a safe YAML scalar.

    If the string contains special characters, wraps it in double quotes
    with internal double-quotes escaped.
    """
    if not value:
        return '""'
    # Characters that need quoting in YAML scalars.
    needs_quoting = any(
        c in value for c in (':', '#', '"', "'", '\n', '\r', '\t', '{', '}', '[', ']')
    ) or value[0] in ('-', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`')

    if not needs_quoting:
        return value

    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
