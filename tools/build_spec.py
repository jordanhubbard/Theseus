#!/usr/bin/env python3
"""
build_spec.py

Takes a canonical record JSON file (SPEC), runs it through a driver to produce
output files, optionally dispatches to a registered target for building, and
on success stores the spec + output files at the configured artifact URL.

Usage:
    python3 tools/build_spec.py SPEC [--driver DRIVER] [--target TARGET]
                                     [--store URL] [--ai] [--config PATH]

Options:
  --driver   freebsd_ports or nixpkgs (default: both)
  --target   Target name from config.yaml targets list (default: local only)
  --store    Override artifact store URL from config.yaml
  --ai       Invoke AI agent to fill in missing fields before running driver
  --config   Path to config.yaml (default: ./config.yaml)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from theseus.drivers import DRIVERS
import theseus.config as config_mod
import theseus.agent as agent_mod
import theseus.remote as remote_mod
import theseus.store as store_mod


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build output files from a canonical spec record.",
    )
    parser.add_argument("spec", help="Path to canonical record JSON file")
    parser.add_argument(
        "--driver",
        choices=["freebsd_ports", "nixpkgs", "both"],
        default="both",
        help="Driver(s) to run (default: both)",
    )
    parser.add_argument(
        "--target",
        help="Target name from config.yaml targets list",
    )
    parser.add_argument(
        "--store",
        help="Override artifact store URL from config.yaml",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Invoke AI agent to fill in missing fields before running driver",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "--cache-sources",
        action="store_true",
        default=None,
        help="Upload generated source files to artifact store (overrides config.yaml)",
    )
    parser.add_argument(
        "--no-cache-sources",
        action="store_true",
        help="Do not upload generated source files (overrides config.yaml)",
    )
    args = parser.parse_args(argv)

    # Load config
    config_path = Path(args.config) if args.config else None
    cfg = config_mod.load(config_path)

    # Load spec
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
        return 1

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: failed to load spec: {e}", file=sys.stderr)
        return 1

    canonical_name = spec.get("identity", {}).get("canonical_name", "unknown")

    # AI enhancement
    if args.ai:
        ai_cfg = cfg.get("ai", {})
        if agent_mod.available(ai_cfg):
            print("Invoking AI agent to enhance spec...")
            prompt = (
                "Given this canonical package record, fill in any missing fields "
                "including sha256 checksums, correct dependency names, and USES hints. "
                "Return the complete updated JSON only.\n\n"
                + json.dumps(spec)
            )
            try:
                response = agent_mod.run_prompt(prompt, ai_cfg)
                # Try to parse AI response as JSON
                try:
                    enhanced = json.loads(response)
                    # Merge enhanced fields into spec
                    spec.update(enhanced)
                    print("AI enhancement applied.")
                except json.JSONDecodeError:
                    print("WARNING: AI response was not valid JSON; skipping enhancement.")
            except RuntimeError as e:
                print(f"WARNING: AI agent failed: {e}")
        else:
            print("WARNING: --ai requested but no AI provider is available.")

    # Determine which drivers to run
    if args.driver == "both":
        drivers_to_run = ["freebsd_ports", "nixpkgs"]
    else:
        drivers_to_run = [args.driver]

    # Run drivers
    generated_files: list[str] = []
    for driver_name in drivers_to_run:
        driver_fn = DRIVERS[driver_name]
        output = driver_fn(spec)
        out_dir = Path("output") / driver_name / canonical_name
        out_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in output.items():
            fpath = out_dir / filename
            fpath.write_text(content, encoding="utf-8")
            generated_files.append(str(fpath))
            print(f"  wrote: {fpath}")

    # Target dispatch
    store_url = args.store or cfg.get("artifact_store", {}).get("url", "")
    all_targets = cfg.get("targets", [])

    def _find_target(name: str | None, driver_name: str) -> dict | None:
        """Return target config by explicit name, or auto-route by driver field."""
        if name:
            t = next((t for t in all_targets if t.get("name") == name), None)
            if t is None:
                print(f"WARNING: target '{name}' not found in config.yaml")
            return t
        # Auto-route: find first target whose 'driver' field matches driver_name.
        return next((t for t in all_targets if t.get("driver") == driver_name), None)

    build_results = []
    for driver_name in drivers_to_run:
        out_dir = Path("output") / driver_name / canonical_name
        target_cfg = _find_target(args.target, driver_name)
        if target_cfg is None:
            if args.target:
                continue  # warning already printed
            # No auto-routable target — skip remote dispatch for this driver.
            continue
        print(f"\nDispatching {driver_name} build to target '{target_cfg['name']}'...")
        result = remote_mod.build_on_target(
            driver_name, out_dir, canonical_name, target_cfg
        )
        build_results.append(result)
        status = "OK" if result.success else "FAILED"
        print(f"  [{status}] returncode={result.returncode}")
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)

    # Artifact store
    store_cfg = cfg.get("artifact_store", {})

    # Resolve cache_generated_sources: CLI flags override config, config defaults to False.
    if args.no_cache_sources:
        cache_sources = False
    elif args.cache_sources:
        cache_sources = True
    else:
        cache_sources = bool(store_cfg.get("cache_generated_sources", False))

    if store_url and cache_sources:
        for driver_name in drivers_to_run:
            out_dir = Path("output") / driver_name / canonical_name
            print(f"\nStoring {driver_name} generated sources to {store_url}...")
            ok, errmsg = store_mod.store(
                store_url, canonical_name, driver_name, spec, out_dir, store_cfg
            )
            if ok:
                print(f"  stored: {store_url}/{canonical_name}/{driver_name}/")
            else:
                print(f"  WARNING: store failed: {errmsg}", file=sys.stderr)
    elif store_url and not cache_sources:
        print("\nGenerated sources not cached (cache_generated_sources=false)."
              " Use --cache-sources to override.")

    print(f"\nSummary: {len(generated_files)} files generated for '{canonical_name}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
