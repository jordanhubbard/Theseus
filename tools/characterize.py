#!/usr/bin/env python3
"""
characterize.py — Run the Phase 2 characterization loop for one gold-set family.

  python3 tools/characterize.py json
  python3 tools/characterize.py --all

A family directory gold/<family>/ must contain:
  package.md         Markdown authority with YAML frontmatter
  uncertainty.yaml   Reviewed uncertainty ledger (no status: open)

The loop:
  1. Validate authority + ledger
  2. Compile and verify the public Layer 2 oracle against the installed library
  3. Run live probes (installed API only; no implementation source)
  4. If a held-out oracle exists, compile + verify it and run held_out_guard
     when a clean-room public spec is also declared

Does not mark anything qualified (ADR 0001 / 0003).
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for extra in (_REPO_ROOT, _REPO_ROOT / "tools"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import yaml  # noqa: E402

import live_probe  # noqa: E402
import verify_behavior as vb  # noqa: E402
import zsdl_compile  # noqa: E402

try:
    import cleanroom_verify as cv
except ImportError:
    cv = None

try:
    import held_out_guard
except ImportError:
    held_out_guard = None

GOLD_ROOT = _REPO_ROOT / "gold"
REQUIRED_FRONTMATTER = (
    "family",
    "public_oracle",
    "ladder",
    "qualification",
)
LEDGER_STATUSES = frozenset({"resolved", "deferred", "held_out"})
OPTIONAL_SKIP_IMPORT = {
    "tomli": "tomllib",
    "tomllib": "tomllib",
    "uu": "uu",  # removed in Python 3.13 (PEP 594)
}


def _frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("{} must start with YAML frontmatter".format(path))
    _, rest = text.split("---\n", 1)
    parts = rest.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError("{} frontmatter is not closed".format(path))
    meta = yaml.safe_load(parts[0])
    if not isinstance(meta, dict):
        raise ValueError("{} frontmatter must be a mapping".format(path))
    return meta, parts[1]


def load_family(family: str):
    directory = GOLD_ROOT / family
    package = directory / "package.md"
    ledger = directory / "uncertainty.yaml"
    if not package.is_file():
        raise FileNotFoundError("missing {}".format(package))
    if not ledger.is_file():
        raise FileNotFoundError("missing {}".format(ledger))
    meta, body = _frontmatter(package)
    for key in REQUIRED_FRONTMATTER:
        if key not in meta:
            raise ValueError("{} missing frontmatter key {}".format(package, key))
    if meta["family"] != family:
        raise ValueError("{} family {!r} != directory {!r}".format(package, meta["family"], family))
    if meta.get("qualification") not in ("none", None):
        raise ValueError("{} must not claim qualification".format(package))
    doc = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("{}: top-level must be a mapping".format(ledger))
    items = doc.get("items") or []
    if not items:
        raise ValueError("{}: ledger has no items".format(ledger))
    if not doc.get("reviewed"):
        raise ValueError("{}: reviewed must be true".format(ledger))
    opens = [item.get("id") for item in items if item.get("status") not in LEDGER_STATUSES]
    if opens:
        raise ValueError("{}: unresolved items: {}".format(ledger, opens))
    probes = directory / "probes.yaml"
    return {
        "family": family,
        "dir": directory,
        "meta": meta,
        "body": body,
        "ledger": doc,
        "probes": probes if probes.is_file() else None,
    }


def _compile(zsdl: Path, out_name=None):
    compiler = zsdl_compile.ZSDLCompiler()
    compiled = compiler.compile_file(zsdl)
    out_dir = _REPO_ROOT / "_build" / "zspecs"
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_name:
        out = out_dir / out_name
    else:
        stem = zsdl.name
        if stem.endswith(".zsdl"):
            stem = stem[:-5]
        out = out_dir / (stem if stem.endswith(".json") else stem + ".json")
    out.write_text(json.dumps(compiled, indent=2) + "\n", encoding="utf-8")
    return compiled, out


def _verify_compiled(compiled, path: Path):
    lang = compiled.get("backend_lang") or ""
    backend = (compiled.get("library") or {}).get("backend")
    if lang in ("python_cleanroom", "node_cleanroom"):
        if cv is None:
            return {"skipped": True, "reason": "cleanroom_verify unavailable"}
        result = cv.verify(str(path))
        if result.get("fail"):
            raise RuntimeError("cleanroom verify failed: {}".format(result.get("errors")))
        return {"pass": result.get("pass"), "fail": 0, "kind": "cleanroom"}
    # Layer 2
    spec = vb.SpecLoader().load(path)
    try:
        lib = vb.LibraryLoader().load(spec["library"])
    except vb.LibraryNotFoundError as exc:
        return {"skipped": True, "reason": str(exc)}
    lib_version = vb._get_lib_version(spec["library"], lib)
    runner = vb.InvariantRunner()
    results = runner.run_all(spec, lib, lib_version=lib_version or "")
    failed = [r for r in results if not r.passed and not r.skip_reason]
    if failed:
        raise RuntimeError("oracle failed: {}".format(
            [(r.inv_id, r.message[:80]) for r in failed[:8]]
        ))
    return {
        "pass": sum(1 for r in results if r.passed),
        "skip": sum(1 for r in results if r.skip_reason),
        "fail": 0,
        "kind": backend or "layer2",
    }


def _skip_reason(family):
    mod = OPTIONAL_SKIP_IMPORT.get(family)
    if not mod:
        return None
    try:
        importlib.import_module(mod)
    except ImportError:
        return "module {} not installed".format(mod)
    return None


def characterize(family: str, verbose=False):
    rec = load_family(family)
    meta = rec["meta"]
    skip = _skip_reason(family)
    if skip:
        report = {
            "family": family,
            "ladder_claimed": meta.get("ladder"),
            "qualification": meta.get("qualification"),
            "ledger_items": len(rec["ledger"].get("items") or []),
            "skipped": True,
            "reason": skip,
            "steps": [],
        }
        print("skip characterize {}: {}".format(family, skip))
        return report
    steps = []
    public = _REPO_ROOT / meta["public_oracle"]
    if not public.is_file():
        raise FileNotFoundError(meta["public_oracle"])
    compiled, compiled_path = _compile(public)
    public_result = _verify_compiled(compiled, compiled_path)
    steps.append(("public_oracle", public_result))
    if public_result.get("skipped") and verbose:
        print("skip public verify:", public_result.get("reason"))

    cr = meta.get("cleanroom_oracle")
    if cr:
        cr_path = _REPO_ROOT / cr
        c_compiled, c_out = _compile(cr_path)
        steps.append(("cleanroom_oracle", _verify_compiled(c_compiled, c_out)))

    held = meta.get("held_out_oracle")
    if held:
        held_path = _REPO_ROOT / held
        h_compiled, h_out = _compile(
            held_path, "held_out_{}.zspec.json".format(family)
        )
        steps.append(("held_out_oracle", _verify_compiled(h_compiled, h_out)))
        if held_out_guard is not None and cr:
            leaks = held_out_guard.check(_REPO_ROOT / cr, held_path)
            if leaks:
                raise RuntimeError("held-out tokens leaked: {}".format(leaks))
            steps.append(("held_out_guard", {"pass": 1, "fail": 0}))

    if rec["probes"] is not None:
        if public_result.get("skipped"):
            steps.append(("live_probes", {
                "skipped": True,
                "reason": public_result.get("reason"),
            }))
        else:
            probe_result = live_probe.run_file(rec["probes"])
            if probe_result["fail"]:
                bad = [p for p in probe_result["probes"] if not p["passed"]]
                raise RuntimeError("live probes failed: {}".format(
                    [(p["id"], p["message"]) for p in bad]
                ))
            steps.append(("live_probes", {"pass": probe_result["pass"], "fail": 0}))

    report = {
        "family": family,
        "ladder_claimed": meta.get("ladder"),
        "qualification": meta.get("qualification"),
        "ledger_items": len(rec["ledger"].get("items") or []),
        "steps": [{"name": name, "result": result} for name, result in steps],
    }
    if verbose:
        print(json.dumps(report, indent=2))
    else:
        print("characterize {}: {} ledger items, {} steps".format(
            family, report["ledger_items"], len(steps)
        ))
    return report


def characterization_record(family):
    """Map a gold-set family onto the characterization-record schema (ADR 0006)."""
    rec = load_family(family)
    meta = rec["meta"]
    probes = None
    if rec["probes"] is not None:
        probes = "gold/{}/probes.yaml".format(family)
    return {
        "schema_version": "1.0",
        "kind": "characterization_record",
        "family": family,
        "authority": "gold/{}/package.md".format(family),
        "public_oracle": meta.get("public_oracle"),
        "cleanroom_oracle": meta.get("cleanroom_oracle"),
        "held_out_oracle": meta.get("held_out_oracle"),
        "implementation": meta.get("implementation"),
        "uncertainty_ledger": "gold/{}/uncertainty.yaml".format(family),
        "probes": probes,
        "blocks": meta.get("blocks"),
        "exports": list(meta.get("exports") or []),
        "ladder": meta.get("ladder"),
        "qualification": meta.get("qualification") or "none",
        "docs": list(meta.get("docs") or []),
        "rfcs": list(meta.get("rfcs") or []),
    }


def list_families():
    names = []
    if not GOLD_ROOT.is_dir():
        return names
    for path in sorted(GOLD_ROOT.iterdir()):
        if path.is_dir() and (path / "package.md").is_file():
            names.append(path.name)
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description="Characterization loop for a gold-set family")
    parser.add_argument("family", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for name in list_families():
            print(name)
        return 0
    families = list_families() if args.all else ([args.family] if args.family else [])
    if not families:
        parser.error("provide FAMILY or --all")
    failed = []
    for family in families:
        try:
            characterize(family, verbose=args.verbose)
        except Exception as exc:
            failed.append((family, str(exc)))
            print("FAIL {}: {}".format(family, exc), file=sys.stderr)
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
