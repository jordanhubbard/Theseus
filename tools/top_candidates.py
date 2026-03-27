#!/usr/bin/env python3
"""
top_candidates.py

Rank packages as promising first candidates for Z extraction.

Heuristics:
- present in both ecosystems = good
- higher provenance confidence = good
- fewer dependencies = easier
- tests present = good
- patches present = slight complexity penalty
"""

from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

def load_records(snapshot_root: Path):
    for path in snapshot_root.rglob("*.json"):
        if path.name == "manifest.json" or "reports" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "identity" in data:
                yield data
        except Exception:
            continue

def score_record(rec: dict) -> float:
    deps = rec.get("dependencies", {})
    dep_count = sum(len(deps.get(k, [])) for k in ("build", "host", "runtime", "test"))
    conf = float(rec.get("provenance", {}).get("confidence", 0.5))
    tests = rec.get("tests", {})
    has_tests = any(bool(v) for v in tests.values())
    patch_count = len(rec.get("patches", []))
    score = 0.0
    score += conf * 50.0
    if has_tests:
        score += 15.0
    score += max(0, 20 - dep_count)
    score -= patch_count * 2.0
    return round(score, 3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    groups = defaultdict(list)
    for rec in load_records(args.snapshot):
        name = rec.get("identity", {}).get("canonical_name", "unknown")
        groups[name].append(rec)

    ranked = []
    for name, entries in groups.items():
        ecosystems = sorted({e.get("identity", {}).get("ecosystem") for e in entries})
        score = sum(score_record(e) for e in entries) / max(1, len(entries))
        if "nixpkgs" in ecosystems and "freebsd_ports" in ecosystems:
            score += 25.0
        ranked.append({
            "canonical_name": name,
            "ecosystems": ecosystems,
            "score": round(score, 3),
            "versions": sorted({e.get("identity", {}).get("version", "") for e in entries}),
            "avg_confidence": round(sum(float(e.get("provenance", {}).get("confidence", 0.5)) for e in entries) / len(entries), 3),
            "has_any_tests": any(any(bool(v) for v in e.get("tests", {}).values()) for e in entries),
            "total_patch_count": sum(len(e.get("patches", [])) for e in entries),
        })

    ranked.sort(key=lambda x: (-x["score"], x["canonical_name"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ranked, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(ranked[:20], indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
