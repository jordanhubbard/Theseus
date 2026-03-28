#!/usr/bin/env python3
"""
extract_candidates.py  — Phase Z extraction

Read the top_candidates.json ranking and a snapshot directory, and produce
one unified extraction record per candidate in an output directory.

Each extraction record merges information from all ecosystems for that package
and adds a structured analysis section covering version agreement, confidence,
dependency coverage, license agreement, and deprecation status.  These records
are the input for the downstream porting step.

Usage:
    python3 tools/extract_candidates.py SNAPSHOT CANDIDATES.json --out DIR [--top N]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_records_by_name(snapshot_root: Path) -> dict[str, list[dict]]:
    """Return all canonical records in snapshot_root grouped by canonical_name."""
    by_name: dict[str, list[dict]] = defaultdict(list)
    for path in snapshot_root.rglob("*.json"):
        if path.name == "manifest.json" or "reports" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "identity" in data:
                name = data["identity"].get("canonical_name", "unknown")
                by_name[name].append(data)
        except Exception:
            continue
    return by_name


def _version_info(records: list[dict]) -> tuple[bool, dict[str, str]]:
    """Return (agreement, {ecosystem: version})."""
    by_eco = {
        r["identity"]["ecosystem"]: r["identity"].get("version", "")
        for r in records
        if "identity" in r
    }
    agreement = len(set(by_eco.values())) <= 1
    return agreement, by_eco


def _dep_union(records: list[dict]) -> dict[str, list[str]]:
    """Return union of all dependency lists across ecosystems."""
    result: dict[str, set[str]] = {"build": set(), "host": set(), "runtime": set(), "test": set()}
    for rec in records:
        deps = rec.get("dependencies", {})
        for k in result:
            result[k].update(deps.get(k, []))
    return {k: sorted(v) for k, v in result.items()}


def _dep_count(rec: dict) -> int:
    deps = rec.get("dependencies", {})
    return sum(len(deps.get(k, [])) for k in ("build", "host", "runtime", "test"))


def _license_info(records: list[dict]) -> tuple[bool, dict[str, list[str]]]:
    """Return (agreement, {ecosystem: [licenses]})."""
    by_eco = {
        r["identity"]["ecosystem"]: sorted(r.get("descriptive", {}).get("license", []))
        for r in records
        if "identity" in r
    }
    agreement = len({tuple(v) for v in by_eco.values()}) <= 1
    return agreement, by_eco


def _build_notes(
    records: list[dict],
    version_agreement: bool,
    versions_by_eco: dict[str, str],
    dep_count_by_eco: dict[str, int],
    deprecated_in: list[str],
) -> list[str]:
    notes = []

    if version_agreement:
        v = next(iter(versions_by_eco.values()), "unknown")
        notes.append(f"version agreement: all ecosystems at {v!r}")
    else:
        parts = ", ".join(f"{e}={v}" for e, v in sorted(versions_by_eco.items()))
        notes.append(f"version skew: {parts}")

    ecos = sorted(dep_count_by_eco.keys())
    for i in range(len(ecos)):
        for j in range(i + 1, len(ecos)):
            a, b = ecos[i], ecos[j]
            diff = dep_count_by_eco[b] - dep_count_by_eco[a]
            if diff > 0:
                notes.append(f"{b} has {diff} more dep(s) than {a}")
            elif diff < 0:
                notes.append(f"{a} has {-diff} more dep(s) than {b}")

    if deprecated_in:
        notes.append(f"deprecated in: {', '.join(sorted(deprecated_in))}")

    return notes


def extract_candidate(name: str, records: list[dict], score: float) -> dict:
    """Produce a merged extraction record for a single package."""
    ecosystems = sorted({r["identity"]["ecosystem"] for r in records if "identity" in r})

    version_agreement, versions_by_eco = _version_info(records)
    license_agreement, license_by_eco = _license_info(records)
    dep_union = _dep_union(records)

    # Use the highest-confidence record for scalar descriptive fields
    best = max(records, key=lambda r: float(r.get("provenance", {}).get("confidence", 0.0)))
    desc = best.get("descriptive", {})

    maintainers_union = sorted({
        m
        for rec in records
        for m in rec.get("descriptive", {}).get("maintainers", [])
        if m
    })
    conflicts_union = sorted({
        c for rec in records for c in rec.get("conflicts", []) if c
    })
    deprecated_any = any(rec.get("descriptive", {}).get("deprecated", False) for rec in records)
    platforms_union = sorted({
        p for rec in records for p in rec.get("platforms", {}).get("include", []) if p
    })
    sources_union = sorted({
        s["url"]
        for rec in records
        for s in rec.get("sources", [])
        if s.get("url")
    })
    license_union = sorted({
        lic for rec in records for lic in rec.get("descriptive", {}).get("license", []) if lic
    })

    conf_by_eco = {
        r["identity"]["ecosystem"]: round(float(r.get("provenance", {}).get("confidence", 0.0)), 3)
        for r in records
        if "identity" in r
    }
    dep_count_by_eco = {
        r["identity"]["ecosystem"]: _dep_count(r)
        for r in records
        if "identity" in r
    }
    deprecated_in = [
        r["identity"]["ecosystem"]
        for r in records
        if "identity" in r and r.get("descriptive", {}).get("deprecated", False)
    ]

    notes = _build_notes(
        records, version_agreement, versions_by_eco, dep_count_by_eco, deprecated_in
    )

    return {
        "canonical_name": name,
        "score": score,
        "ecosystems": ecosystems,
        "merged": {
            "summary": desc.get("summary", ""),
            "homepage": desc.get("homepage", ""),
            "license": license_union,
            "maintainers": maintainers_union,
            "deprecated": deprecated_any,
            "conflicts": conflicts_union,
            "dependencies": dep_union,
            "platforms_include": platforms_union,
            "sources": sources_union,
        },
        "per_ecosystem": {
            r["identity"]["ecosystem"]: r for r in records if "identity" in r
        },
        "analysis": {
            "version_agreement": version_agreement,
            "versions_by_ecosystem": versions_by_eco,
            "confidence_avg": round(
                sum(conf_by_eco.values()) / max(1, len(conf_by_eco)), 3
            ),
            "confidence_by_ecosystem": conf_by_eco,
            "dep_union_size": sum(len(v) for v in dep_union.values()),
            "dep_count_by_ecosystem": dep_count_by_eco,
            "license_agreement": license_agreement,
            "license_by_ecosystem": license_by_eco,
            "deprecated_in": sorted(deprecated_in),
            "has_conflicts": bool(conflicts_union),
            "notes": notes,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Phase Z: extract top candidates into merged records."
    )
    ap.add_argument("snapshot", type=Path, help="Snapshot directory")
    ap.add_argument("candidates", type=Path, help="top_candidates.json ranking file")
    ap.add_argument(
        "--top", type=int, default=50, help="How many top candidates to extract (default: 50)"
    )
    ap.add_argument("--out", type=Path, required=True, help="Output directory")
    args = ap.parse_args()

    ranked = json.loads(args.candidates.read_text(encoding="utf-8"))[: args.top]
    by_name = load_records_by_name(args.snapshot)

    args.out.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    for entry in ranked:
        name = entry["canonical_name"]
        records = by_name.get(name)
        if not records:
            continue
        extracted = extract_candidate(name, records, entry["score"])
        out_file = args.out / f"{name}.json"
        out_file.write_text(
            json.dumps(extracted, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        manifest.append(
            {
                "canonical_name": name,
                "ecosystems": extracted["ecosystems"],
                "file": out_file.name,
                "score": entry["score"],
            }
        )

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"Extracted {len(manifest)} candidates to {args.out}/")
    if manifest:
        print(f"Top candidate: {manifest[0]['canonical_name']} (score {manifest[0]['score']})")


if __name__ == "__main__":
    main()
