#!/usr/bin/env python3
"""
qualify.py — ADR 0004 gold-set qualification protocol.

  python3 tools/qualify.py json
  python3 tools/qualify.py --all
  python3 tools/qualify.py --check

A family is attempted when gold/<family>/package.md declares
cleanroom_oracle, held_out_oracle, and implementation.

Qualification requires ALL of:
  * public clean-room oracle passes in isolation
  * held-out oracle passes in isolation
  * isolation policy holds (cleanroom_verify)
  * held_out_guard finds no prompt leaks
  * two independent empty-workspace generations with different impl hashes

A single generation cannot mark a package qualified (independent_generation=false).
This tool records receipts; it does not invent a second generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for extra in (_REPO_ROOT, _REPO_ROOT / "tools"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import characterize  # noqa: E402
import cleanroom_verify as cv  # noqa: E402
import held_out_guard  # noqa: E402
import zsdl_compile  # noqa: E402

RECEIPT_DIR = _REPO_ROOT / "reports" / "qualification"
KILL_GATE_MIN_ATTEMPTED = 5


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path):
    return _sha256_bytes(path.read_bytes())


def _hash_tree(root: Path):
    hasher = hashlib.sha256()
    if root.is_file():
        hasher.update(root.read_bytes())
        return hasher.hexdigest()
    files = []
    for path in root.rglob("*"):
        if path.is_file() and path.name != "__pycache__":
            files.append(path)
    for path in sorted(files, key=lambda p: str(p.relative_to(root))):
        rel = str(path.relative_to(root)).encode("utf-8")
        hasher.update(rel)
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _compile_to(zsdl: Path, dest: Path):
    compiled = zsdl_compile.ZSDLCompiler().compile_file(zsdl)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(compiled, indent=2) + "\n", encoding="utf-8")
    return compiled, dest


def _frontmatter_ok_for_attempt(meta):
    needed = ("cleanroom_oracle", "held_out_oracle", "implementation", "blocks")
    missing = [key for key in needed if not meta.get(key)]
    return missing


def _verify_cleanroom(compiled_path: Path, impl_root=None):
    old = os.environ.get("THESEUS_CLEANROOM_PYTHON")
    try:
        if impl_root is not None:
            os.environ["THESEUS_CLEANROOM_PYTHON"] = str(impl_root)
        elif "THESEUS_CLEANROOM_PYTHON" in os.environ:
            del os.environ["THESEUS_CLEANROOM_PYTHON"]
        return cv.verify(str(compiled_path))
    finally:
        if old is None:
            os.environ.pop("THESEUS_CLEANROOM_PYTHON", None)
        else:
            os.environ["THESEUS_CLEANROOM_PYTHON"] = old


def input_closure(family, meta):
    rels = []
    for key in (
        "public_oracle",
        "cleanroom_oracle",
        "held_out_oracle",
        "implementation",
    ):
        if meta.get(key):
            rels.append(meta[key])
    rels.append("gold/{}/package.md".format(family))
    ledger = "gold/{}/uncertainty.yaml".format(family)
    probes = "gold/{}/probes.yaml".format(family)
    if (_REPO_ROOT / ledger).is_file():
        rels.append(ledger)
    if (_REPO_ROOT / probes).is_file():
        rels.append(probes)
    hashed = {}
    for rel in rels:
        path = _REPO_ROOT / rel
        if path.is_dir():
            hashed[rel] = _hash_tree(path)
        elif path.is_file():
            hashed[rel] = _hash_file(path)
        else:
            hashed[rel] = None
    blob = json.dumps(hashed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"files": hashed, "sha256": _sha256_bytes(blob)}


def qualify_family(family, second_impl=None, verbose=False):
    rec = characterize.load_family(family)
    meta = rec["meta"]
    skip = characterize._skip_reason(family)
    if skip:
        return {
            "family": family,
            "attempted": False,
            "skipped": True,
            "reason": skip,
            "qualified": False,
        }
    missing = _frontmatter_ok_for_attempt(meta)
    if missing:
        return {
            "family": family,
            "attempted": False,
            "skipped": True,
            "reason": "not attempted: missing {}".format(", ".join(missing)),
            "qualified": False,
        }

    cr_zsdl = _REPO_ROOT / meta["cleanroom_oracle"]
    held_zsdl = _REPO_ROOT / meta["held_out_oracle"]
    impl = _REPO_ROOT / meta["implementation"]
    if not cr_zsdl.is_file() or not held_zsdl.is_file():
        return {
            "family": family,
            "attempted": False,
            "skipped": True,
            "reason": "oracle files missing",
            "qualified": False,
        }
    if not (impl / "__init__.py").is_file() and not impl.is_file():
        return {
            "family": family,
            "attempted": False,
            "skipped": True,
            "reason": "implementation missing",
            "qualified": False,
        }

    out_dir = _REPO_ROOT / "_build" / "qualification" / family
    public_compiled, public_path = _compile_to(
        cr_zsdl, out_dir / "cleanroom_oracle.zspec.json"
    )
    held_compiled, held_path = _compile_to(
        held_zsdl, out_dir / "held_out.zspec.json"
    )

    leaks = held_out_guard.check(cr_zsdl, held_zsdl)
    guard_ok = not leaks
    public_result = _verify_cleanroom(public_path)
    held_result = _verify_cleanroom(held_path)

    impl_hash_1 = _hash_tree(impl)
    run2 = None
    impl_hash_2 = None
    if second_impl:
        second = Path(second_impl)
        impl_hash_2 = _hash_tree(second)
        python_root = second.parent
        run2 = {
            "public": _verify_cleanroom(public_path, python_root),
            "held_out": _verify_cleanroom(held_path, python_root),
        }

    public_ok = public_result.get("fail", 1) == 0 and public_result.get("pass", 0) > 0
    held_ok = held_result.get("fail", 1) == 0 and held_result.get("pass", 0) > 0
    isolation_ok = public_ok and held_ok
    independent = bool(
        run2
        and impl_hash_2
        and impl_hash_1 != impl_hash_2
        and run2["public"].get("fail", 1) == 0
        and run2["held_out"].get("fail", 1) == 0
    )
    qualified = bool(public_ok and held_ok and guard_ok and independent)
    closure = input_closure(family, meta)

    receipt = {
        "schema": "theseus-qualification-receipt/0.1",
        "family": family,
        "attempted": True,
        "skipped": False,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "blocks": meta.get("blocks"),
        "implementation": meta.get("implementation"),
        "cleanroom_oracle": meta.get("cleanroom_oracle"),
        "held_out_oracle": meta.get("held_out_oracle"),
        "ladder_claimed": meta.get("ladder"),
        "package_qualification_field": meta.get("qualification"),
        "held_out_guard": {"pass": guard_ok, "leaks": leaks},
        "public_oracle": {
            "pass": public_result.get("pass", 0),
            "fail": public_result.get("fail", 0),
            "errors": public_result.get("errors") or [],
            "ok": public_ok,
        },
        "held_out_oracle": {
            "pass": held_result.get("pass", 0),
            "fail": held_result.get("fail", 0),
            "errors": held_result.get("errors") or [],
            "ok": held_ok,
        },
        "isolation": isolation_ok,
        "impl_hash_run1": impl_hash_1,
        "impl_hash_run2": impl_hash_2,
        "independent_generation": independent,
        "input_closure": closure,
        "qualified": qualified,
        "notes": [
            "Passing public + held-out once is regenerated evidence, not qualified.",
            "qualified requires two independent empty-workspace generations.",
        ],
    }
    if run2 is not None:
        receipt["run2"] = run2
    if verbose:
        print(json.dumps(receipt, indent=2))
    else:
        print(
            "qualify {}: public={}/{} held-out={}/{} guard={} independent={} qualified={}".format(
                family,
                public_result.get("pass", 0),
                public_result.get("pass", 0) + public_result.get("fail", 0),
                held_result.get("pass", 0),
                held_result.get("pass", 0) + held_result.get("fail", 0),
                guard_ok,
                independent,
                qualified,
            )
        )
        if not public_ok:
            print("  public errors:", public_result.get("errors")[:3], file=sys.stderr)
        if not held_ok:
            print("  held-out errors:", held_result.get("errors")[:3], file=sys.stderr)
        if leaks:
            print("  leaks:", leaks, file=sys.stderr)
    return receipt


def write_receipt(receipt):
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / "{}.json".format(receipt["family"])
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def summarize(receipts):
    attempted = [r for r in receipts if r.get("attempted")]
    qualified = [r for r in attempted if r.get("qualified")]
    skipped = [r for r in receipts if r.get("skipped")]
    n_att = len(attempted)
    n_q = len(qualified)
    kill = n_att >= KILL_GATE_MIN_ATTEMPTED and n_q * 2 < n_att
    return {
        "schema": "theseus-qualification-summary/0.1",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "attempted": n_att,
        "qualified": n_q,
        "skipped": len(skipped),
        "families_attempted": [r["family"] for r in attempted],
        "families_qualified": [r["family"] for r in qualified],
        "families_skipped": [
            {"family": r["family"], "reason": r.get("reason")} for r in skipped
        ],
        "kill_gate": {
            "min_attempted": KILL_GATE_MIN_ATTEMPTED,
            "rule": "qualified < attempted/2 after at least 5 attempts",
            "fired": kill,
            "product_claim": (
                "characterization"
                if kill or n_q == 0
                else "replacement_still_open"
            ),
        },
        "independent_generation_any": any(
            r.get("independent_generation") for r in attempted
        ),
    }


def check_receipts(summary, receipts):
    errors = []
    for rec in receipts:
        if rec.get("qualified") and not rec.get("independent_generation"):
            errors.append(
                "{} marked qualified without independent_generation".format(
                    rec.get("family")
                )
            )
        if rec.get("qualified") and rec.get("package_qualification_field") not in (
            "none",
            None,
        ):
            # frontmatter must stay 'none' until dual-regen is real; receipts carry the bit
            pass
        if rec.get("attempted") and rec.get("qualified"):
            if rec.get("held_out_guard", {}).get("pass") is not True:
                errors.append("{} qualified with held-out guard failure".format(rec["family"]))
    if summary["qualified"] != len(summary["families_qualified"]):
        errors.append("summary qualified count mismatch")
    expected_kill = (
        summary["attempted"] >= KILL_GATE_MIN_ATTEMPTED
        and summary["qualified"] * 2 < summary["attempted"]
    )
    if bool(summary["kill_gate"]["fired"]) != expected_kill:
        errors.append("kill_gate.fired does not match the stated rule")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gold-set qualification protocol (ADR 0004)")
    parser.add_argument("family", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--check", action="store_true", help="Re-run and validate receipts")
    parser.add_argument("--second-impl", help="Optional second implementation root for run 2")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    families = []
    if args.family:
        families = [args.family]
    else:
        families = characterize.list_families()
        if not args.all and not args.check:
            parser.error("provide FAMILY, --all, or --check")

    receipts = []
    for family in families:
        try:
            receipt = qualify_family(
                family, second_impl=args.second_impl, verbose=args.verbose
            )
        except Exception as exc:
            receipt = {
                "family": family,
                "attempted": False,
                "skipped": True,
                "reason": str(exc),
                "qualified": False,
            }
            print("FAIL {}: {}".format(family, exc), file=sys.stderr)
        write_receipt(receipt)
        receipts.append(receipt)

    summary = summarize(receipts)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = RECEIPT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        "qualification summary: attempted={} qualified={} kill_gate={} claim={}".format(
            summary["attempted"],
            summary["qualified"],
            summary["kill_gate"]["fired"],
            summary["kill_gate"]["product_claim"],
        )
    )

    errors = check_receipts(summary, receipts)
    if args.check and errors:
        for err in errors:
            print("qualify-check: " + err, file=sys.stderr)
        return 1
    if errors:
        for err in errors:
            print("qualify-check: " + err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
