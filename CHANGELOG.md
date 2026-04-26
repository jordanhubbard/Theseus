# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- ZSDL `node_chain_eq` kind for fluent builder APIs that need 3+ chained method/property/call steps off an initial value (entry: `module` / `named` / `constructor` / `factory`). Unblocks commander, builder-style CLIs, and stateful npm packages whose APIs don't fit the existing single-call/two-step kinds.
- ZSDL `node_property_eq` kind — sugar for "construct/call, then read one property". Used for ora, inquirer's `Separator`, meow's `cli.flags`/`cli.input`.
- ZSDL `node_sandbox_chain_eq` kind — same chain semantics but the script runs in a fresh tempdir cwd seeded by `setup`. Used for filesystem packages (glob, fs-extra, mkdirp, rimraf, find-up).
- ZSDL `ctypes_chain_eq` kind — handle-threading for stateful C libraries; per-step `function`/`args`/`arg_types`/`restype` plus `capture: name` for output, `{capture: name}`/`{errbuf: N}` for inputs.
- ZSDL `ctypes_sandbox_chain_eq` kind — ctypes chain + per-invariant tempdir seeded by `setup` with `content_b64` for binary blobs; chain references files via `{sandbox_path: rel}`. Used for libpcap and pcapng to read synthesized savefile/section headers without root or hardware.
- All chain kinds support dotted member paths (e.g. `class: default.Separator`) for ESM packages with nested default exports. JS chains that legitimately return `undefined` map to JSON `null` so YAML `~` works.
- Batches 112–115 — CLI core (commander, yargs, ora, inquirer, meow), pure functions (moment, cheerio, handlebars, js-yaml, underscore), helpers (dotenv, tslib, zod, joi, lru-cache), filesystem (glob, fs-extra, mkdirp, rimraf, find-up): 20 specs, ~255 invariants total.
- Batches 116–122 — markdown/docs (markdown-it, gray-matter, highlight.js, markdown-table, front-matter), pure functions (nanoid, parse5, csv-parse, csv-stringify, bcryptjs), date/time + JSON helpers (luxon, moment-timezone, parse-json, jsonpointer, fast-json-parse), encoding (msgpack-lite, cbor, pako, ieee754, base32-decode), URL/network (whatwg-url, netmask, cidr-tools, ip-regex, parse-domain), text utilities (html-entities, wcwidth, strip-final-newline, figlet, unidecode), diff/templating (diff-match-patch, fast-diff, fuzzysort, liquidjs, eta): 35 specs, ~330 invariants.
- Batches 123–132 — config formats (@iarna/toml, xml-js, plist, jsesc, url-template), color manipulation (chroma-js, color, d3-color, color-string, color-name), bit-twiddling/immutable/hashing (bit-twiddle, immutable, sha.js, pbkdf2, base-x), misc helpers (semver-diff, escape-goat, clone-deep, detect-indent, ansi-regex), specialized parsers (cronstrue, ua-parser-js, mime-db, aes-js, set-cookie-parser), geographic (haversine-distance, proj4, d3-geo, turf-helpers, linkify-it), identity validators (libphonenumber-js, email-validator, card-validator, isemail, xregexp), specialized math/data (ml-matrix, fft-js, bezier-easing, geographiclib-geodesic, delaunator), caching/equality/URI/formatting/fp-ts (quick-lru, fast-equals, fast-uri, pretty-format, fp-ts/Option), graph/levenshtein/passwords/shell-parsing/words (graphlib, levenshtein-edit-distance, password-validator, string-argv, to-words): 50 specs, ~500 invariants.
- Two small chain-helper mode extensions for static-data and module-as-constructor patterns: `entry: bare` (use module object directly without invoking) and `class: ""` (when the module export IS the constructor — linkify-it / password-validator pattern).
- libpcap and pcapng zspecs (35 invariants combined) — pure helpers + offline savefile/section-header readers, derived entirely from the IETF drafts (draft-ietf-opsawg-pcap, draft-ietf-opsawg-pcapng, draft-ietf-opsawg-pcaplinktype). Live capture remains out of scope.
- Batches 133–146 — compression/encoding (fflate, jschardet, lzutf8, smaz, utf8), DNS/IP/JS-parsers (dns-packet, ip-address, uri-templates, jsbi, random-seed; acorn, meriyah, espree, @babel/parser, estraverse), search/conversion/markup (lunr, convert-units, string-strip-html, slice-ansi, strip-bom), validation (z-schema, jsonschema, aggregate-error, es6-error, verror), HTML parsing (htmlparser2, domhandler, domutils, css-what, dom-serializer), Markdown ecosystem (micromark, mdast-util-to-string, github-slugger, remove-markdown, vfile), small utilities (env-paths, string-template, eventemitter3, detect-newline, transliterate; log-symbols, cli-spinners, figures, sparkline, strnum; nanoid-dictionary, prepend-http, string-format, emoji-regex), async/concurrency (p-limit, p-queue, p-retry, delay, bottleneck), auth/IDs/validation (jsonwebtoken, ulid, hyperid, yup, short-uuid), glob/crypto/zip (fast-glob, globby, node-forge, tweetnacl, jszip), templating + small utils (pug, mitt, node-cache, html-tags, svg-tags): ~70 additional specs, ~700 invariants.
- Chain method steps now accept `tap: true` — calls the method for its side effect without reassigning the threaded value. Needed for builder/mutator APIs (node-cache .set/.mset, etc.) where the method returns a status (boolean, count) instead of the receiver.

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

