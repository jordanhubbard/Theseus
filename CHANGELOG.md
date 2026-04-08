# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.2] - 2026-04-08

### Fixed
- detect python binary path rather than symlinking in FreeBSD CI
- symlink python3.11 → python3 in FreeBSD CI
- skip platform-specific and version-gated invariants in CI
- install all spec libraries in CI so behavioral tests can run
- CI was failing on all jobs — add pyyaml dep, bump cross-platform-actions

### Other
- fix README inaccuracies
- update README with accurate ecosystem descriptions and dedicated Z-Specs/ZSDL section
- Initial plan
- Update README to include PyPi and NPM in toolchain
- Fix three accuracy issues found in documentation review
- Add AGENTS.md, update README, and publish user guide to GitHub Pages

## [0.0.1] - 2026-04-05

### Other
- Add express, lodash, prettier to npm dependencies
- Add make release target with scripts/release.sh and CHANGELOG.md
- Makefile: clean also removes verify_all_specs_out.json
- gitignore: exclude .claude/worktrees/
- Update PLAN.md: 100% pipeline coverage milestone, full cycle history through Cycle 16
- Cycle 16: dns, networkx, tornado, zope_interface, fontTools, protobuf, lodash, prettier — 100% pipeline coverage
- Cycle 15: distro, docutils, isodate, markdown, stevedore (62 specs · 999 invariants · 84% pipeline)
- Cycle 14: pathspec, filelock, traitlets, tomlkit, defusedxml (57 specs · 928 invariants · 74% pipeline)
- spec_coverage: add package alias dict for PyPI name → spec file stem mismatches
- Cycle 13: certifi, colorama, more_itertools, fsspec, dotenv (52 specs · 858 invariants · 62% pipeline)
- Cycle 12: setuptools, typing_extensions, tzdata, wrapt, pluggy (47 specs · 797 invariants · 52% pipeline)
- Cycle 11: six, decorator, idna, platformdirs, pytz specs (42 specs · 732 invariants · 44% pipeline coverage)
- Update PLAN.md for Cycle 10
- Add attrs, chardet, pyparsing, tomli/tomllib specs (Cycle 10)
- Update PLAN.md for Cycle 9
- Add pcre2, markupsafe, msgpack specs (Cycle 9)
- gitignore verify_all_specs_out.json
- Update PLAN.md for Cycle 8 — all planned specs complete
- Add lz4 and express specs; register new kinds (Cycle 8)
- Update PLAN.md for Cycle 7
- Add lxml, packaging, pillow, psutil, pygments specs (Cycle 7)
- Update PLAN.md for Cycle 6 completion
- Add spec vector coverage tool and bump schema to v0.2 (items C + D)
- Add numpy, pyyaml, urllib3 specs and update PLAN.md (Cycle 6)
- Add chalk and libcrypto specs; ESM node backend support
- Implement all four infrastructure items (B/C/D/E)
- Move generated JSON specs to _build/zspecs/ (never committed)
- Convert all 15 remaining hand-crafted specs to ZSDL
- Add ZSDL compiler: YAML authoring language for Z-layer behavioral specs
- Add urllib_parse, difflib, zstd specs; extend hashlib to 41 invariants
- Update all documentation to reflect Z-layer implementation
- Add --watch mode, FreeBSD CI job, and complete all 6 planned items
- Add spec_coverage report and verify_all_specs JSON export (items 4 and 5)
- Add datetime/pathlib/ajv specs, method chaining, and spec_for_versions enforcement
- Update PLAN.md: reflect completed work, set next 7 steps
- Add re and sqlite3 Z-specs; verify-all-specs; auto-inject behavioral_spec
- Add uuid and minimist Z-layer specs; fix node_module_call_eq JSON comparison (issue #6)
- Add --baseline / --diff mode to verify_behavior.py (issue #7)
- Add macOS to CI matrix, Node.js setup, and npm dependencies (issue #5)
- Update architecture.md: slave port support was already implemented (closes #4)
- Add curl Z-layer spec with offline-safe invariants (issue #3)
- Connect Z-specs to package recipe records (issue #2)
- Add Z-spec static schema validator (issue #1)
- Add PLAN.md: next steps roadmap
- Add node_module_call_eq kind and semver Z-layer spec
- Add CLI/subprocess backend and openssl Z-layer spec
- Add base64/json/struct Z-layer specs and general Python-module pattern handlers
- Add hashlib Z-layer spec and extend harness to support Python-module backend
- Add Z-layer behavioral spec and verification harness (zlib pilot)
- Add ubuntu.local sync target; schema 0.2 fixes and slave port support
- Move bootstrap_canonical_recipes.py to tools/; update all references
- Add top-100 PyPI and top-36 npm canonical specs (232 total)
- Filter Makefile variable artifacts from PyPI seed list
- Add PyPI and npm importers, drivers, and seed tool (480 tests)
- Add top-100 canonical specs from bulk_build pipeline
- Fix Makefile: bulk-build expands snapshot into ecosystem subdirs, fix broken echo
- Add bulk_build.py pipeline tool with tests and Makefile target
- Switch filldeps to batched eval with per-package fallback
- Wire three-worker topology and cache_generated_sources config option
- Add rank_by_deps tool and specs/ directory
- Fix filldeps: use --strict to force dep evaluation before JSON serialization
- Add make sync target and document rsync snapshot exclusion
- Phase 2 complete: driver system, remote dispatch, artifact store, dep fill
- Add schema/package-recipe.schema.json (was never committed from starter bundle)
- Add overlap_report.py and top_candidates.py (were never committed from starter bundle)
- Add conftest.py to fix ModuleNotFoundError on pytest 9.x / FreeBSD
- Fix README install steps: add pip install pytest, correct repo case
- Add CI, expand builder coverage, document schema evolution and slave ports
- Complete project: validator, snapshot diff, overlapping examples
- Fix four pre-deploy gaps: importer, gitignore, Python version, license
- Bootstrap Theseus: README, Makefile, tests, docs, PROVENANCE Part 6
- Initial commit

