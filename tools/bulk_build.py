#!/usr/bin/env python3
"""
bulk_build.py

Drive the full spec pipeline for the top-N packages from a ranked-by-deps
report.  For each candidate:

  1. Find its snapshot record(s) across ecosystems
  2. Generate a canonical spec (merged from all ecosystems)
  3. Run the appropriate driver(s) to produce build files
  4. Dispatch builds to the right worker in parallel:
       freebsd_ports → freebsd.local
       nixpkgs       → ubuntu.local
  5. Optionally cache generated sources to S3 (if cache_generated_sources=true)
  6. Write the spec to specs/<canonical_name>.json and stage for git commit

Usage:
    python3 tools/bulk_build.py RANKED_JSON SNAPSHOT_DIR
        [--top N] [--min-refs N] [--ecosystems freebsd_ports,nixpkgs]
        [--drivers freebsd_ports,nixpkgs] [--dry-run] [--config PATH]
        [--jobs N]

Options:
  --top N           Process top N packages from the ranked list (default: 100)
  --min-refs N      Skip packages with fewer than N refs (default: 5)
  --ecosystems      Comma-separated list of ecosystems to consider (default: all)
  --drivers         Comma-separated drivers to run (default: match ecosystem)
  --dry-run         Print what would be done without building
  --config PATH     Path to config.yaml (site overrides in config.site.yaml)
  --jobs N          Parallel build jobs (default: 2, one per worker)
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import theseus.config as config_mod
import theseus.remote as remote_mod
import theseus.store as store_mod
from theseus.drivers import DRIVERS

# ---------------------------------------------------------------------------
# Record loading
# ---------------------------------------------------------------------------

def load_snapshot_index(snapshot_dirs: list[Path]) -> dict[str, list[dict]]:
    """Return {canonical_name: [record, ...]} from all snapshot dirs."""
    index: dict[str, list[dict]] = {}
    for snap in snapshot_dirs:
        for path in sorted(snap.rglob("*.json")):
            if path.name == "manifest.json":
                continue
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(rec, dict) or "identity" not in rec:
                    continue
                name = rec["identity"].get("canonical_name") or rec["identity"].get("name")
                if name:
                    index.setdefault(name, []).append(rec)
            except Exception:
                continue
    return index


def merge_records(records: list[dict]) -> dict:
    """
    Merge multiple ecosystem records for the same canonical name into one spec.
    Takes the most confident record as the base, then unions deps, sources,
    maintainers, and conflicts from all records.
    """
    if not records:
        return {}
    # Use highest-confidence record as base
    base = max(records, key=lambda r: float(r.get("provenance", {}).get("confidence", 0)))
    spec = json.loads(json.dumps(base))  # deep copy

    for rec in records:
        if rec is base:
            continue
        # Union sources (by url)
        existing_urls = {s.get("url") for s in spec.get("sources", [])}
        for src in rec.get("sources", []):
            if src.get("url") not in existing_urls:
                spec.setdefault("sources", []).append(src)
                existing_urls.add(src.get("url"))
        # Union deps
        for bucket in ("build", "host", "runtime", "test"):
            existing = set(spec.get("dependencies", {}).get(bucket, []))
            for dep in rec.get("dependencies", {}).get(bucket, []):
                if dep not in existing:
                    spec.setdefault("dependencies", {}).setdefault(bucket, []).append(dep)
                    existing.add(dep)
        # Union maintainers
        existing_m = set(spec.get("descriptive", {}).get("maintainers", []))
        for m in rec.get("descriptive", {}).get("maintainers", []):
            if m not in existing_m:
                spec.setdefault("descriptive", {}).setdefault("maintainers", []).append(m)
                existing_m.add(m)
        # Union conflicts
        existing_c = set(spec.get("conflicts", []))
        for c in rec.get("conflicts", []):
            if c not in existing_c:
                spec.setdefault("conflicts", []).append(c)
                existing_c.add(c)

    # Record which ecosystems contributed
    ecosystems = sorted({r.get("identity", {}).get("ecosystem", "") for r in records} - {""})
    spec.setdefault("extensions", {})["merged_from"] = ecosystems

    return spec


# ---------------------------------------------------------------------------
# Build one package
# ---------------------------------------------------------------------------

_print_lock = threading.Lock()


def _log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def build_one(
    canonical_name: str,
    records: list[dict],
    drivers_to_run: list[str],
    cfg: dict,
    specs_dir: Path,
    dry_run: bool,
) -> dict:
    """
    Run the full pipeline for one canonical package.
    Returns a result dict with keys: name, drivers, success, errors.
    """
    result = {"name": canonical_name, "drivers": {}, "errors": []}

    spec = merge_records(records)
    if not spec:
        result["errors"].append("no records found")
        return result

    all_targets = cfg.get("targets", [])
    store_cfg = cfg.get("artifact_store", {})
    store_url = store_cfg.get("url", "")
    cache_sources = bool(store_cfg.get("cache_generated_sources", False))

    for driver_name in drivers_to_run:
        if driver_name not in DRIVERS:
            result["errors"].append(f"unknown driver: {driver_name}")
            continue

        out_dir = Path("output") / driver_name / canonical_name

        if dry_run:
            _log(f"  [DRY-RUN] {canonical_name} / {driver_name}")
            result["drivers"][driver_name] = "dry-run"
            continue

        # Generate build files
        try:
            driver_fn = DRIVERS[driver_name]
            output = driver_fn(spec)
            out_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in output.items():
                (out_dir / filename).write_text(content, encoding="utf-8")
        except Exception as e:
            result["errors"].append(f"{driver_name} driver error: {e}")
            result["drivers"][driver_name] = "driver-error"
            continue

        # Find target by driver field
        target_cfg = next(
            (t for t in all_targets if t.get("driver") == driver_name), None
        )

        build_ok = False
        if target_cfg:
            _log(f"  [{canonical_name}] dispatching {driver_name} → {target_cfg['name']}")
            try:
                res = remote_mod.build_on_target(
                    driver_name, out_dir, canonical_name, target_cfg
                )
                build_ok = res.success
                status = "OK" if res.success else "FAILED"
                _log(f"  [{canonical_name}] {driver_name} [{status}] rc={res.returncode}")
                if not res.success and res.stderr:
                    _log(f"  [{canonical_name}] stderr: {res.stderr[:200].rstrip()}")
            except Exception as e:
                result["errors"].append(f"{driver_name} build error: {e}")
                result["drivers"][driver_name] = "build-error"
                continue
        else:
            _log(f"  [{canonical_name}] no target for {driver_name}, skipping build")
            build_ok = None  # generated but not built

        result["drivers"][driver_name] = "ok" if build_ok else ("failed" if build_ok is False else "generated")

        # Cache generated sources to S3 if configured
        if store_url and cache_sources:
            try:
                ok, errmsg = store_mod.store(
                    store_url, canonical_name, driver_name, spec, out_dir, store_cfg
                )
                if not ok:
                    result["errors"].append(f"store failed: {errmsg}")
            except Exception as e:
                result["errors"].append(f"store error: {e}")

    # Write spec to specs/ (always, regardless of build outcome)
    spec_path = specs_dir / f"{canonical_name}.json"
    try:
        spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
        _log(f"  [{canonical_name}] spec written → specs/{canonical_name}.json")
    except Exception as e:
        result["errors"].append(f"spec write error: {e}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bulk spec generation and build pipeline.")
    ap.add_argument("ranked_json", type=Path,
                    help="ranked-by-deps.json from rank_by_deps.py")
    ap.add_argument("snapshot_dirs", type=Path, nargs="+",
                    help="One or more snapshot directories to load records from")
    ap.add_argument("--top", type=int, default=100,
                    help="Process top N packages (default: 100)")
    ap.add_argument("--min-refs", type=int, default=5,
                    help="Skip packages with fewer than N refs (default: 5)")
    ap.add_argument("--ecosystems",
                    help="Comma-separated ecosystems to include (default: all)")
    ap.add_argument("--drivers",
                    help="Comma-separated drivers to run (default: freebsd_ports,nixpkgs)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print actions without building")
    ap.add_argument("--config", type=Path, default=None,
                    help="Path to config.yaml (site overrides loaded from config.site.yaml alongside it)")
    ap.add_argument("--jobs", type=int, default=2,
                    help="Parallel build threads (default: 2)")
    args = ap.parse_args(argv)

    cfg = config_mod.load(args.config)

    # Load ranked list
    ranked = json.loads(args.ranked_json.read_text(encoding="utf-8"))

    # Filter
    ecosystem_filter = set(args.ecosystems.split(",")) if args.ecosystems else None
    candidates = []
    for entry in ranked:
        if entry["ref_count"] < args.min_refs:
            continue
        if not entry["in_snapshot"]:
            continue
        if ecosystem_filter and not (set(entry["ecosystems"]) & ecosystem_filter):
            continue
        candidates.append(entry["canonical_name"])
        if len(candidates) >= args.top:
            break

    if not candidates:
        print("No candidates match filters.", file=sys.stderr)
        return 1

    print(f"Processing {len(candidates)} packages (top={args.top}, min-refs={args.min_refs})")

    # Load snapshot index
    print(f"Loading snapshot records from {[str(d) for d in args.snapshot_dirs]}...")
    index = load_snapshot_index(args.snapshot_dirs)
    print(f"Indexed {len(index)} canonical names.")

    # Determine drivers
    if args.drivers:
        drivers_to_run = [d.strip() for d in args.drivers.split(",")]
    else:
        drivers_to_run = ["freebsd_ports", "nixpkgs"]

    specs_dir = _REPO_ROOT / "specs"
    specs_dir.mkdir(exist_ok=True)

    # Run pipeline
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(
                build_one,
                name,
                index.get(name, []),
                drivers_to_run,
                cfg,
                specs_dir,
                args.dry_run,
            ): name
            for name in candidates
        }
        for future in as_completed(futures):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                results.append({"name": futures[future], "errors": [str(e)], "drivers": {}})

    # Summary
    total = len(results)
    specs_written = sum(1 for r in results if not r["errors"] or
                        any(v in ("ok", "generated") for v in r["drivers"].values()))
    build_ok = sum(1 for r in results if any(v == "ok" for v in r["drivers"].values()))
    errors = sum(1 for r in results if r["errors"])

    print(f"\nDone: {total} packages processed")
    print(f"  Specs written:  {specs_written}")
    print(f"  Builds OK:      {build_ok}")
    print(f"  With errors:    {errors}")

    if errors:
        print("\nPackages with errors:")
        for r in sorted(results, key=lambda x: x["name"]):
            if r["errors"]:
                print(f"  {r['name']}: {'; '.join(r['errors'])}")

    if not args.dry_run and specs_written > 0:
        print(f"\nSpecs written to specs/. Stage with:")
        print(f"  git add specs/ && git commit -m 'Add top-{args.top} canonical specs'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
