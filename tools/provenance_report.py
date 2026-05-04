#!/usr/bin/env python3
"""
provenance_report.py — Generate a provenance attestation for a Theseus spec.

A provenance report documents:
  - What sources the spec was derived from (public documentation, RFCs, headers)
  - What sources it was explicitly NOT derived from (implementation source files)
  - Whether a clean-room implementation has been verified in isolation
  - The behavioral invariants that serve as the clean-room boundary

Usage:
  python3 tools/provenance_report.py zspecs/zlib.zspec.zsdl
  python3 tools/provenance_report.py zspecs/theseus_json.zspec.zsdl
  python3 tools/provenance_report.py zspecs/hashlib.zspec.zsdl --json
  python3 tools/provenance_report.py zspecs/hashlib.zspec.zsdl --out provenance.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = _REPO_ROOT / "theseus_registry.json"
_BUILD_DIR = _REPO_ROOT / "_build" / "zspecs"


def _load_registry() -> dict:
    if not _REGISTRY_PATH.exists():
        return {"packages": {}}
    return json.loads(_REGISTRY_PATH.read_text())


def _sniff_zsdl(path: Path) -> dict:
    """Extract key fields from a .zspec.zsdl without full YAML parse."""
    text = path.read_text(errors="replace")
    result = {}

    for field in ("spec", "backend", "docs", "version"):
        m = re.search(rf"^{field}:\s*(.+)$", text, re.MULTILINE)
        if m:
            result[field] = m.group(1).strip().strip('"')

    rfcs = re.findall(r'^\s+-\s+"(RFC\d+[^"]*)"', text, re.MULTILINE)
    result["rfcs"] = rfcs

    prov_block = re.search(
        r"^provenance:\s*\n((?:[ \t]+.+\n?)*)", text, re.MULTILINE
    )
    if prov_block:
        prov_text = prov_block.group(1)

        derived = re.findall(r'derived_from:\s*\n((?:\s+-[^\n]+\n?)*)', prov_text)
        if derived:
            result["derived_from"] = re.findall(r'^\s+-\s+"?([^"\n]+)"?', derived[0], re.MULTILINE)

        not_derived = re.findall(r'not_derived_from:\s*\n((?:\s+-[^\n]+\n?)*)', prov_text)
        if not_derived:
            result["not_derived_from"] = re.findall(r'^\s+-\s+"?([^"\n]+)"?', not_derived[0], re.MULTILINE)

        m_notes = re.search(r'notes:\s*"([^"]+)"', prov_text)
        if m_notes:
            result["notes"] = m_notes.group(1)

        m_created = re.search(r'created_at:\s*"([^"]+)"', prov_text)
        if m_created:
            result["created_at"] = m_created.group(1)

    inv_count = len(re.findall(r"^\s+function:\s", text, re.MULTILINE))
    result["invariant_count"] = inv_count

    return result


def _load_compiled(zsdl_path: Path) -> dict | None:
    stem = zsdl_path.stem
    compiled = _BUILD_DIR / f"{stem}.json"
    if compiled.exists():
        try:
            return json.loads(compiled.read_text())
        except Exception:
            return None
    return None


def generate(spec_path: Path) -> dict:
    """Generate a provenance report dict for a spec file."""
    if not spec_path.exists():
        print(f"ERROR: spec not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    meta = _sniff_zsdl(spec_path)
    registry = _load_registry()

    spec_name = meta.get("spec", spec_path.stem.replace(".zspec", ""))
    reg_entry = registry["packages"].get(spec_name)
    is_verified = reg_entry is not None and reg_entry.get("status") == "verified"

    compiled = _load_compiled(spec_path)
    invariants = []
    if compiled:
        for inv in compiled.get("invariants", []):
            fn = inv.get("function") or inv.get("id") or inv.get("describe", "")
            kind = inv.get("kind", "?")
            expected = inv.get("expected", "")
            invariants.append({"function": fn, "kind": kind, "expected": expected})

    cleanroom_path = reg_entry.get("cleanroom_path", "") if reg_entry else ""
    cleanroom_exists = bool(cleanroom_path and (_REPO_ROOT / cleanroom_path).exists())

    return {
        "spec_name": spec_name,
        "spec_file": str(spec_path.relative_to(_REPO_ROOT)),
        "backend": meta.get("backend", "unknown"),
        "version": meta.get("version", ""),
        "docs": meta.get("docs", ""),
        "rfcs": meta.get("rfcs", []),
        "provenance": {
            "derived_from": meta.get("derived_from", []),
            "not_derived_from": meta.get("not_derived_from", []),
            "notes": meta.get("notes", ""),
            "created_at": meta.get("created_at", ""),
        },
        "invariant_count": meta.get("invariant_count", len(invariants)),
        "invariants": invariants,
        "clean_room": {
            "verified": is_verified,
            "cleanroom_path": cleanroom_path,
            "implementation_exists": cleanroom_exists,
        },
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _render_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# Provenance Report: `{report['spec_name']}`")
    lines.append("")
    lines.append(f"**Generated:** {report['report_generated_at']}")
    lines.append(f"**Spec file:** `{report['spec_file']}`")
    lines.append(f"**Backend:** `{report['backend']}`")
    if report["version"]:
        lines.append(f"**Version:** `{report['version']}`")
    if report["docs"]:
        lines.append(f"**Reference docs:** {report['docs']}")
    lines.append("")

    cr = report["clean_room"]
    if cr["verified"]:
        lines.append("## Clean-Room Status: ✓ VERIFIED")
        lines.append("")
        lines.append(
            f"A clean-room implementation exists at `{cr['cleanroom_path']}` and has been "
            "verified in isolation (original package blocked during testing)."
        )
    else:
        lines.append("## Clean-Room Status: NOT VERIFIED")
        lines.append("")
        lines.append(
            "No verified clean-room implementation exists for this spec yet. "
            "Run `make pipeline SYNTH_ZSDL=" + report["spec_file"] + "` to synthesize one."
        )
    lines.append("")

    prov = report["provenance"]
    lines.append("## Provenance")
    lines.append("")
    lines.append("### Derived From")
    lines.append("")
    lines.append("The behavioral specification was authored using only the following public sources:")
    lines.append("")
    for src in prov["derived_from"]:
        lines.append(f"- {src}")
    if not prov["derived_from"]:
        lines.append("- *(not specified)*")
    lines.append("")

    lines.append("### NOT Derived From")
    lines.append("")
    lines.append(
        "The following implementation source files were explicitly excluded from "
        "the specification process (clean-room boundary):"
    )
    lines.append("")
    for src in prov["not_derived_from"]:
        lines.append(f"- `{src}`")
    if not prov["not_derived_from"]:
        lines.append("- *(not specified)*")
    lines.append("")

    if prov["notes"]:
        lines.append("### Notes")
        lines.append("")
        lines.append(prov["notes"])
        lines.append("")

    if report["rfcs"]:
        lines.append("### Referenced Standards")
        lines.append("")
        for rfc in report["rfcs"]:
            lines.append(f"- {rfc}")
        lines.append("")

    lines.append("## Behavioral Invariants")
    lines.append("")
    lines.append(
        f"This spec defines **{report['invariant_count']} invariants** that "
        "constitute the clean-room boundary. Any correct implementation must "
        "satisfy all of them. Run `make verify-behavior ZSPEC=_build/zspecs/"
        f"{report['spec_name']}.zspec.json` to validate against the real library."
    )
    if report["invariants"]:
        lines.append("")
        lines.append("| Function | Kind | Expected |")
        lines.append("|----------|------|----------|")
        for inv in report["invariants"][:20]:
            fn = inv["function"] or "*(table)*"
            lines.append(f"| `{fn}` | `{inv['kind']}` | `{str(inv['expected'])[:60]}` |")
        if len(report["invariants"]) > 20:
            lines.append(f"| … | … | *({len(report['invariants']) - 20} more)* |")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a provenance attestation for a Theseus spec")
    parser.add_argument("spec", help="Path to .zspec.zsdl file")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    parser.add_argument("--out", help="Write output to this file instead of stdout")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = _REPO_ROOT / spec_path

    report = generate(spec_path)

    if args.json:
        output = json.dumps(report, indent=2)
    else:
        output = _render_markdown(report)

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(output)
        print(f"Provenance report written to {out_path}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
