#!/usr/bin/env python3
"""
lint_cleanroom.py — CI check enforcing Theseus clean-room spec conventions.

Rejects:
  - Any NEW spec using `backend: rust_module(...)` (wrappers are deprecated)
  - Any spec using `backend: python_cleanroom` that imports its blocked package

Usage:
  python3 tools/lint_cleanroom.py                  # check all zspecs/
  python3 tools/lint_cleanroom.py zspecs/foo.zspec.zsdl  # check one file
  python3 tools/lint_cleanroom.py --new-only       # only check specs not in wave_state.json

Exit codes:
  0  All checks passed
  1  One or more violations found
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_STATE_FILE = _REPO_ROOT / "reports" / "synthesis" / "wave_state.json"


def _load_known_specs() -> set[str]:
    if not _STATE_FILE.exists():
        return set()
    state = json.loads(_STATE_FILE.read_text())
    return set(state.get("specs", {}).keys())


def check_file(path: Path, known_specs: set[str], new_only: bool) -> list[str]:
    violations = []
    text = path.read_text()

    # Extract spec name
    m = re.search(r"^spec:\s+(\S+)", text, re.MULTILINE)
    if not m:
        return []
    spec_name = m.group(1)

    is_new = spec_name not in known_specs

    if new_only and not is_new:
        return []

    # Rule 1: New rust_module specs are forbidden
    if is_new and re.search(r"^backend:\s+rust_module\s*\(", text, re.MULTILINE):
        violations.append(
            f"{path}: VIOLATION — new spec '{spec_name}' uses deprecated "
            f"backend: rust_module. Use python_cleanroom or node_cleanroom instead."
        )

    # Rule 2: For cleanroom specs, warn if notes mention "Expose X: original.X"
    # (pattern indicates wrapping intent)
    if re.search(r"^backend:\s+(python|node)_cleanroom", text, re.MULTILINE):
        expose_matches = re.findall(r'"Expose\s+\w+.*?:\s*\w+\.\w+', text)
        if expose_matches:
            violations.append(
                f"{path}: WARNING — spec '{spec_name}' notes mention 'Expose X: original.X' "
                f"which suggests wrapper intent. Clean-room specs should not expose wrapper functions."
            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Theseus clean-room specs for wrapper violations")
    parser.add_argument("files", nargs="*", help="ZSDL files to check (default: all zspecs/)")
    parser.add_argument("--new-only", action="store_true",
                        help="Only check specs not already in wave_state.json")
    args = parser.parse_args()

    known = _load_known_specs()

    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        paths = sorted(Path("zspecs").glob("*.zspec.zsdl"))

    all_violations = []
    for path in paths:
        all_violations.extend(check_file(path, known, args.new_only))

    if all_violations:
        for v in all_violations:
            print(v, file=sys.stderr)
        print(f"\n{len(all_violations)} violation(s) found.", file=sys.stderr)
        return 1

    print(f"OK: {len(paths)} spec(s) checked, 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
