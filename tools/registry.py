#!/usr/bin/env python3
"""
registry.py — Theseus clean-room package registry.

Only packages registered here with status="verified" may be used as
dependencies in other Theseus clean-room reimplementations.

Usage:
  python3 tools/registry.py list
  python3 tools/registry.py register theseus_json cleanroom/python/theseus_json zspecs/theseus_json.zspec.zsdl
  python3 tools/registry.py verify theseus_json
  python3 tools/registry.py check theseus_json   # exits 0 if verified, 1 if not
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

REGISTRY_PATH = _REPO_ROOT / "theseus_registry.json"
_VALID_REGISTER_STATUSES = {"pending", "failed"}


def load() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def _save(reg: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2) + "\n")


def is_allowed(name: str) -> bool:
    """Return True if name is a verified Theseus package."""
    reg = load()
    pkg = reg["packages"].get(name)
    return pkg is not None and pkg.get("status") == "verified"


def register(name: str, cleanroom_path: str, spec: str, status: str = "pending") -> None:
    if status not in _VALID_REGISTER_STATUSES:
        raise ValueError(
            "register status must be one of "
            f"{', '.join(sorted(_VALID_REGISTER_STATUSES))}; "
            "use 'verify' to promote a package"
        )
    reg = load()
    reg["packages"][name] = {
        "cleanroom_path": cleanroom_path,
        "spec": spec,
        "status": status,
    }
    _save(reg)
    print(f"Registered: {name} ({status})")


def mark_verified(name: str, *, verbose: bool = False) -> None:
    reg = load()
    if name not in reg["packages"]:
        raise KeyError(f"{name} not in registry — register it first")
    info = reg["packages"][name]
    spec_path = _resolve_repo_path(info.get("spec", ""))
    cleanroom_path = _resolve_repo_path(info.get("cleanroom_path", ""))

    if not spec_path.is_file():
        raise FileNotFoundError(f"spec file not found for {name}: {spec_path}")
    if not cleanroom_path.exists():
        raise FileNotFoundError(
            f"cleanroom path not found for {name}: {cleanroom_path}"
        )

    from tools.cleanroom_verify import verify as cleanroom_verify

    result = cleanroom_verify(str(spec_path), verbose=verbose)
    if result.get("fail", 0) or result.get("error"):
        errors = result.get("errors", [])
        first_error = ""
        if errors:
            first_error = f": {errors[0].get('error', '')[:200]}"
        raise RuntimeError(
            f"{name} failed clean-room verification "
            f"({result.get('pass', 0)}/{result.get('pass', 0) + result.get('fail', 0)} passed)"
            f"{first_error}"
        )

    reg["packages"][name]["status"] = "verified"
    reg["packages"][name]["verified_pass_count"] = result.get("pass", 0)
    reg["packages"][name]["verified_total"] = result.get("pass", 0) + result.get("fail", 0)
    reg["packages"][name].pop("policy_error", None)
    _save(reg)
    print(
        f"Verified: {name} "
        f"({reg['packages'][name]['verified_pass_count']}/{reg['packages'][name]['verified_total']})"
    )


def list_packages(status_filter: str | None = None) -> list[dict]:
    reg = load()
    pkgs = []
    for name, info in reg["packages"].items():
        if status_filter is None or info.get("status") == status_filter:
            pkgs.append({"name": name, **info})
    return pkgs


def _resolve_repo_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else _REPO_ROOT / p


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Theseus clean-room package registry")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list")

    p_reg = sub.add_parser("register")
    p_reg.add_argument("name")
    p_reg.add_argument("cleanroom_path")
    p_reg.add_argument("spec")
    p_reg.add_argument("--status", default="pending")

    p_ver = sub.add_parser("verify")
    p_ver.add_argument("name")

    p_chk = sub.add_parser("check")
    p_chk.add_argument("name")

    args = parser.parse_args()

    if args.cmd == "list":
        pkgs = list_packages()
        if not pkgs:
            print("Registry is empty.")
        for p in pkgs:
            print(f"  [{p['status']:8}] {p['name']}  →  {p['cleanroom_path']}")
        return 0

    if args.cmd == "register":
        try:
            register(args.name, args.cleanroom_path, args.spec, args.status)
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "verify":
        try:
            mark_verified(args.name)
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "check":
        ok = is_allowed(args.name)
        print(f"{args.name}: {'verified' if ok else 'NOT verified'}")
        return 0 if ok else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
