#!/usr/bin/env python3
"""
lint_gold_wrappers.py — Freeze legacy factory wrappers; require public-API gold-set specs.

Gold-set clean-room specs (theseus_json and theseus_*_q) must call the public
API with arguments. Legacy theseus_* factory specs are frozen: new wrapper
specs are rejected unless added to reports/audit/factory-wrapper-freeze.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for extra in (_REPO_ROOT, _REPO_ROOT / "tools"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import zsdl_compile  # noqa: E402

FREEZE_PATH = _REPO_ROOT / "reports" / "audit" / "factory-wrapper-freeze.json"
ZSPECS = _REPO_ROOT / "zspecs"


def _zero_arg_eq_count(compiled):
    n = 0
    eq = 0
    for inv in compiled.get("invariants") or []:
        kind = inv.get("kind") or "python_call_eq"
        if kind != "python_call_eq":
            continue
        eq += 1
        spec = inv.get("spec") or {}
        args = spec.get("args")
        if args in ([], None):
            n += 1
    return n, eq


def _is_gold_cleanroom(path: Path):
    name = path.name
    if name == "theseus_json.zspec.zsdl":
        return True
    return name.startswith("theseus_") and name.endswith("_q.zspec.zsdl")


def load_freeze():
    if not FREEZE_PATH.is_file():
        return {"specs": []}
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def iter_theseus_zsdl():
    return sorted(ZSPECS.glob("theseus_*.zspec.zsdl"))


def lint(write_freeze=False):
    compiler = zsdl_compile.ZSDLCompiler()
    freeze = load_freeze()
    frozen = set(freeze.get("specs") or [])
    errors = []
    gold = []
    factories = []
    for path in iter_theseus_zsdl():
        rel = "zspecs/{}".format(path.name)
        compiled = compiler.compile_file(path)
        backend = compiled.get("backend_lang") or ""
        if backend not in ("python_cleanroom", "node_cleanroom", ""):
            continue
        zeros, eq_n = _zero_arg_eq_count(compiled)
        wrapperish = eq_n > 0 and zeros >= max(1, int(0.9 * eq_n))
        if _is_gold_cleanroom(path):
            gold.append(rel)
            if zeros:
                errors.append(
                    "{} is a gold-set spec but has {} zero-arg python_call_eq invariants".format(
                        rel, zeros
                    )
                )
            continue
        factories.append(rel)
        if write_freeze:
            continue
        if wrapperish and rel not in frozen:
            errors.append(
                "{} looks like a new factory-wrapper spec; add it to {} only if it is intentionally frozen".format(
                    rel, FREEZE_PATH.relative_to(_REPO_ROOT)
                )
            )
    if write_freeze:
        payload = {
            "schema": "theseus-factory-wrapper-freeze/0.1",
            "note": "Legacy theseus_* zero-arg factory specs. Do not copy this pattern. Gold-set work uses theseus_json and theseus_*_q.",
            "specs": sorted(factories),
        }
        FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FREEZE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return [], payload
    extra_freeze = sorted(frozen - set(factories))
    return errors, {
        "gold": gold,
        "factories": factories,
        "frozen": sorted(frozen),
        "missing_freeze": sorted(set(factories) - frozen),
        "extra_freeze": extra_freeze,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    write = "--write-freeze" in argv
    errors, info = lint(write_freeze=write)
    if write:
        print("wrote {} ({} factory specs)".format(
            FREEZE_PATH, len(info.get("specs") or [])
        ))
        return 0
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print(
        "gold-set wrapper lint: {} gold public-API specs, {} frozen factory specs".format(
            len(info["gold"]), len(info["frozen"])
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
