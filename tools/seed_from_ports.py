#!/usr/bin/env python3
"""
seed_from_ports.py

Scan a freebsd_ports snapshot and produce package seed lists for PyPI and npm
importers.

PyPI seeds: py-* ports whose MASTER_SITES is PYPI (source url == "PYPI").
npm seeds:  A curated list of the most-depended-upon npm packages by download
            count (the FreeBSD ports tree has too few node-* ports to seed from).
            Extend with --npm-extra FILE to append additional names.

Usage:
    python3 tools/seed_from_ports.py SNAPSHOT_DIR/freebsd_ports
        [--pypi-out FILE]    (default: reports/pypi-seed.txt)
        [--npm-out  FILE]    (default: reports/npm-seed.txt)
        [--npm-extra FILE]   (optional extra npm names, one per line)
        [--npm-top N]        (how many curated npm packages to emit, default: 100)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Curated top npm packages by reverse-dep count (stable, well-known list).
# Source: npm "most depended upon" as of early 2026.
# ---------------------------------------------------------------------------
_TOP_NPM = [
    "lodash", "chalk", "commander", "axios", "react", "express", "moment",
    "underscore", "request", "async", "debug", "bluebird", "uuid", "semver",
    "dotenv", "yargs", "glob", "minimatch", "mkdirs", "rimraf", "through2",
    "readable-stream", "inherits", "once", "wrappy", "graceful-fs", "abbrev",
    "nopt", "npmlog", "ansi-regex", "strip-ansi", "supports-color", "has-flag",
    "color-convert", "color-name", "escape-string-regexp", "ansi-styles",
    "ms", "depd", "bytes", "on-finished", "finalhandler", "serve-static",
    "etag", "fresh", "range-parser", "content-type", "content-disposition",
    "vary", "accepts", "mime-types", "mime-db", "negotiator", "qs",
    "parseurl", "path-to-regexp", "methods", "type-is", "body-parser",
    "raw-body", "iconv-lite", "unpipe", "destroy", "setprototypeof",
    "statuses", "toidentifier", "http-errors", "proxy-addr", "forwarded",
    "ipaddr.js", "cookie", "cookie-signature", "merge-descriptors",
    "safe-buffer", "string_decoder", "util-deprecate", "isarray",
    "process-nextick-args", "core-util-is", "inflight", "balanced-match",
    "brace-expansion", "concat-map", "fs.realpath", "path-is-absolute",
    "fill-range", "to-regex-range", "is-number", "picomatch", "readdirp",
    "anymatch", "normalize-path", "fsevents", "chokidar", "webpack",
    "typescript", "jest", "mocha", "eslint", "prettier", "babel-core",
    "rollup", "vite", "esbuild", "postcss", "tailwindcss", "next",
    "vue", "svelte", "rxjs", "mobx", "redux", "zustand", "immer",
    "zod", "joi", "yup", "ajv", "fast-json-stringify", "pino",
    "winston", "morgan", "helmet", "cors", "compression", "multer",
    "socket.io", "ws", "node-fetch", "got", "superagent", "cheerio",
]


# ---------------------------------------------------------------------------
# PyPI seeder
# ---------------------------------------------------------------------------

def seed_pypi(snapshot_dir: Path) -> list[str]:
    """Walk freebsd_ports snapshot and return PyPI package names."""
    names: list[str] = []
    seen: set[str] = set()

    for path in sorted(snapshot_dir.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        identity = rec.get("identity", {})
        eco_id = identity.get("ecosystem_id", "")  # e.g. "devel/py-requests"
        canonical = identity.get("canonical_name", "")

        # Only py-* ports whose MASTER_SITES = PYPI
        is_py_port = "/py-" in eco_id or eco_id.startswith("py-")
        has_pypi_site = any(
            s.get("url", "").upper() == "PYPI"
            for s in rec.get("sources", [])
        )

        if not (is_py_port and has_pypi_site):
            continue

        # The canonical_name already has py- stripped by the importer
        pypi_name = canonical.lower().replace("_", "-")
        if pypi_name and pypi_name not in seen:
            seen.add(pypi_name)
            names.append(pypi_name)

    return sorted(names)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate PyPI and npm seed lists from FreeBSD ports snapshot.")
    ap.add_argument("snapshot_dir", type=Path,
                    help="freebsd_ports snapshot directory")
    ap.add_argument("--pypi-out", type=Path, default=Path("reports/pypi-seed.txt"),
                    help="Output file for PyPI package names (default: reports/pypi-seed.txt)")
    ap.add_argument("--npm-out", type=Path, default=Path("reports/npm-seed.txt"),
                    help="Output file for npm package names (default: reports/npm-seed.txt)")
    ap.add_argument("--npm-extra", type=Path, default=None,
                    help="Optional file of additional npm package names (one per line)")
    ap.add_argument("--npm-top", type=int, default=100,
                    help="How many curated npm packages to include (default: 100)")
    args = ap.parse_args(argv)

    if not args.snapshot_dir.is_dir():
        print(f"Error: {args.snapshot_dir} is not a directory", file=sys.stderr)
        return 1

    # PyPI seed
    pypi_names = seed_pypi(args.snapshot_dir)
    args.pypi_out.parent.mkdir(parents=True, exist_ok=True)
    args.pypi_out.write_text(
        "# PyPI packages seeded from FreeBSD py-* ports (MASTER_SITES=PYPI)\n"
        + "\n".join(pypi_names) + "\n",
        encoding="utf-8",
    )
    print(f"PyPI seed: {len(pypi_names)} packages → {args.pypi_out}")

    # npm seed
    npm_names: list[str] = list(_TOP_NPM[:args.npm_top])
    if args.npm_extra and args.npm_extra.is_file():
        for line in args.npm_extra.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line and line not in npm_names:
                npm_names.append(line)

    args.npm_out.parent.mkdir(parents=True, exist_ok=True)
    args.npm_out.write_text(
        "# npm packages (curated top-N by reverse-dep count)\n"
        + "\n".join(npm_names) + "\n",
        encoding="utf-8",
    )
    print(f"npm seed:  {len(npm_names)} packages → {args.npm_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
