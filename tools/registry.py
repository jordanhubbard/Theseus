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
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = _REPO_ROOT / "theseus_registry.json"


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
    reg = load()
    reg["packages"][name] = {
        "cleanroom_path": cleanroom_path,
        "spec": spec,
        "status": status,
    }
    _save(reg)
    print(f"Registered: {name} ({status})")


def mark_verified(name: str) -> None:
    reg = load()
    if name not in reg["packages"]:
        raise KeyError(f"{name} not in registry — register it first")
    reg["packages"][name]["status"] = "verified"
    _save(reg)
    print(f"Verified: {name}")


def list_packages(status_filter: str | None = None) -> list[dict]:
    reg = load()
    pkgs = []
    for name, info in reg["packages"].items():
        if status_filter is None or info.get("status") == status_filter:
            pkgs.append({"name": name, **info})
    return pkgs


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
        register(args.name, args.cleanroom_path, args.spec, args.status)
        return 0

    if args.cmd == "verify":
        mark_verified(args.name)
        return 0

    if args.cmd == "check":
        ok = is_allowed(args.name)
        print(f"{args.name}: {'verified' if ok else 'NOT verified'}")
        return 0 if ok else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
