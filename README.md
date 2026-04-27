# Theseus

> *You start with a ship. You replace the planks. You replace the mast. You replace the hull. At what point does it become a different ship? Theseus answered this question by not caring and sailing anyway.*

[![CI](https://github.com/jordanhubbard/Theseus/actions/workflows/ci.yml/badge.svg)](https://github.com/jordanhubbard/Theseus/actions/workflows/ci.yml)

> ### **2,295 source specs · 16,683 invariants · 1,091 npm packages · libpcap + pcapng covered**

📖 **[Full User Guide →](https://jordanhubbard.github.io/Theseus/)** — installation, pipeline walkthrough, spec authoring, language reference. The full list of covered libraries lives in the user guide [Index](https://jordanhubbard.github.io/Theseus/#covered-library-index).

---

## What Theseus is

**Theseus** is a clean-room package synthesis engine plus a behavioral spec verifier. Given a machine-readable description of what a software package must do, Theseus (a) verifies the description against the real, installed library on every CI run, and (b) can synthesize a complete reimplementation that satisfies the description without runtime dependence on the original — no wrapping, no cross-language call-backs, no shimming. Python packages are reimplemented in Python; Node.js packages in JavaScript. Only other Theseus-verified packages may serve as dependencies, forming a self-contained ecosystem rooted in `theseus_registry.json`.

**Theseus** also provides a toolchain for normalizing package recipes from four ecosystems into a shared canonical schema, so packages can be compared, ranked, and reasoned about across ecosystems without losing the provenance of each claim.

Three ecosystems are first-class citizens on Linux and macOS:
- [**Nixpkgs**](https://github.com/NixOS/nixpkgs) — traversed via `--nixpkgs`, dependency graphs filled by `fill_nixpkgs_deps.py`
- [**PyPI**](https://pypi.org/) — imported via the PyPI JSON API (`make import-pypi`); source repositories backtracked to GitHub via `project_urls`
- [**npm**](https://www.npmjs.com/) — imported via the npm registry API (`make import-npm`); source repositories backtracked to GitHub via the `repository` field

[**FreeBSD Ports**](https://github.com/freebsd/freebsd-ports) is supported as a **build recipe source** — its 20,000+ port Makefiles complement Nixpkgs as input. FreeBSD itself is not a CI target platform.

---

## Vocabulary

Terms used throughout the project, defined here before they appear in the rest of the README:

- **Behavioral spec** — a machine-readable file declaring what a software package must do (its observable invariants), independent of the original's source code. Every spec lives at `zspecs/<name>.zspec.zsdl`.
- **Z-spec** / **zspec** — synonym for behavioral spec; the "Z" was chosen for being terminal (Z is the last letter — after Z, only verification remains).
- **ZSDL** — *Z-Spec Definition Language*. The YAML-flavoured surface syntax of `.zspec.zsdl` files. Compiles to JSON via `make compile-zsdl`. Full grammar: [docs/zsdl-design.md](docs/zsdl-design.md).
- **Invariant** — one falsifiable claim about behaviour (e.g. *"`semver.valid('1.2.3')` returns `'1.2.3'`"*). The verification harness asserts each invariant against the real installed library and reports pass/fail.
- **Compiled bundle** — the compiler emits one `.zspec.json` per source `.zsdl`. The current corpus has 2,295 source specs totalling 16,683 invariants.
- **Backend** — how the spec runner loads the library under test: `ctypes` (C shared libraries via `ctypes.CDLL`), `python_module` (`importlib.import_module`), `node` (CJS or ESM via `node -e`), `cli` (`subprocess.run`).
- **Clean-room package** — a Theseus reimplementation registered in `theseus_registry.json` that satisfies its spec without importing the original library.

---

### Core Principles

- **No wrapping.** A clean-room implementation must not `import` (or `require`) the original package.
- **No cross-language boundaries.** Python packages → Python. Node.js packages → JavaScript.
- **Spec-first.** Every package has a behavioral spec before any implementation begins.
- **Isolation-verified.** Invariants are verified with the original package actively blocked via `THESEUS_BLOCKED_PACKAGE`.
- **Registry-only dependencies.** Only Theseus-verified packages (in `theseus_registry.json`) may be imported.

### Clean-Room Packages (verified)

| Package | Language | Invariants | Replaces |
|---|---|---|---|
| `theseus_json` | Python | 3/3 | `json` |
| `theseus_re` | Python | 3/3 | `re` |
| `theseus_pathlib` | Python | 3/3 | `pathlib` / `os.path` |
| `theseus_path_node` | Node.js | 3/3 | Node `path` |

---

## Z-Specs and ZSDL

### What is a Z-spec?

A **Z-spec** (behavioral specification) is a machine-readable contract that describes how an OSS library actually behaves at its public API boundary. Each spec:

- Is derived **only from public documentation** — API docs, RFCs, man pages — never from library source code
- Defines **invariants**: testable assertions about exact behavior (e.g., `crc32(0, NULL, 0) must return 0`, `json.loads('null') is None`)
- Is **verified against the real installed library** on every CI run across macOS, Linux, and FreeBSD
- Includes a **provenance block** that explicitly records what documentation was and was not read — establishing a clean-room boundary

The clean-room provenance model matters because it ensures specs can be used as a trustworthy behavioral baseline independent of any particular implementation. If a spec value can only be known by reading source code, it doesn't belong in the spec.

### What is ZSDL?

**ZSDL** (Z-Spec Definition Language) is a YAML-based authoring format that compiles to the existing Z-spec JSON format:

- Reduces a typical 300-line JSON spec to ~75 lines with zero information lost
- Provides a table syntax for grouping repeated test vectors compactly
- Auto-generates `description` and `id` fields where they are mechanical
- Source files live in `zspecs/*.zspec.zsdl` — **committed to git**
- Compiled JSON lives in `_build/zspecs/*.zspec.json` — **build artifact, never committed**
- The compiler is `tools/zsdl_compile.py`, invoked via `make compile-zsdl`

### Backends

Each spec targets one backend that loads the library under test:

| Backend | ZSDL header | How it loads the library |
|---------|-------------|--------------------------|
| `ctypes` | `ctypes(zlib)` | `ctypes.CDLL` via `ctypes.util.find_library` |
| `python_module` | `python_module(hashlib)` | `importlib.import_module` |
| `cli` | `cli(curl)` | `subprocess.run` |
| `node/CJS` | `node(semver)` | `node -e "require('semver')..."` |
| `node/ESM` | `node(chalk)` + `esm: true` | `node -e "await import('chalk')..."` |

### Authoring workflow

```bash
# Edit or create a spec
$EDITOR zspecs/mylib.zspec.zsdl

# Compile one spec
make compile-zsdl ZSDL=zspecs/mylib.zspec.zsdl

# Compile all specs
make compile-zsdl

# Verify against the installed library
make verify-behavior ZSPEC=_build/zspecs/mylib.zspec.json
```

---

## Quick Start

### Requirements

- Python 3.9+
- Node.js 22+ and npm (for Node.js-backed specs: ajv, chalk, express, lodash, minimist, prettier, semver, uuid)
- `pytest` (for `make test`)

### Install

```bash
git clone https://github.com/jordanhubbard/Theseus
cd Theseus
pip install pytest pyyaml
npm install
make
```

### Run the test suite

```bash
make test
```

### Demo on built-in examples

```bash
make start        # runs analysis on examples/ — no snapshot needed
```

### Verify behavioral specs

```bash
make compile-zsdl              # compile ZSDL sources to _build/zspecs/
make verify-all-specs          # run all 2,295 compiled specs; print text summary
make verify-all-specs-json     # same, write JSON results
make verify-behavior ZSPEC=_build/zspecs/zlib.zspec.json  # single spec
```

---

## Project Layout

```
theseus/        Python package: importer, drivers, remote, store, agent, config
tools/          CLI analysis and verification scripts
zspecs/         Z-spec sources (*.zspec.zsdl) — committed
_build/zspecs/  Compiled specs (*.zspec.json) — build artifact, not committed
schema/         JSON Schema for canonical package records
zspecs/schema/  JSON Schema for Z-spec files
examples/       Sample canonical records (curl, openssl, zlib)
specs/          Canonical package records (232 packages)
docs/           Architecture, ZSDL design, spec-authoring guide
docs/guide/     User guide source (built to GitHub Pages)
tests/          Test suite (13,900+ tests)
scripts/        Release automation
```

---

## Makefile Targets

```
make / make all          Check Python version, print usage
make start               Run analysis on SNAPSHOT= or demo on examples/
make test                Validate Z-specs then run test suite
make compile-zsdl        Compile zspecs/*.zspec.zsdl → _build/zspecs/*.zspec.json
make verify-all-specs    Run every spec; text summary
make verify-all-specs-json  Run every spec; write JSON results
make verify-behavior     Run one spec (ZSPEC=path)
make validate-e2e        Build from source + verify spec end-to-end (E2E_RECORD=, E2E_ZSPEC=)
make import-pypi         Fetch PyPI metadata with source_repository backtracking
make import-npm          Fetch npm metadata with source_repository backtracking
make spec-coverage       Coverage report (EXTRACTION_DIR= required)
make validate-zspecs     Validate Z-spec JSON files against schema
make clean               Remove build artifacts
make release             Cut a release (BUMP=major|minor|patch)
make help                Full target and variable reference
```

---

## Schema

The canonical record format (`schema/package-recipe.schema.json`) captures identity, dependencies, build system, sources, patches, platforms, features, tests, provenance, and an optional `behavioral_spec` pointer. See [docs/architecture.md](docs/architecture.md) for the full design.

---

## CI

GitHub Actions runs on every push and pull request to `main`:

- **Matrix job:** ubuntu-latest + macos-latest × Python 3.9–3.12 × Node 22

The ubuntu/Python-3.12 job uploads `verify-all-specs-results.json` as an artifact.

---

## Development

```bash
make test           # run the full test suite
make clean          # remove _build/, .pytest_cache, *.pyc
make validate       # validate records in examples/ (or PATHS=dir)
make sync           # rsync to SYNC_TARGETS (excludes snapshots/)
```

No runtime configuration is required. All behavior is controlled by command-line arguments and Makefile variables.

---

## License

[BSD 2-Clause](LICENSE)

---

## The Totally True and Not At All Embellished History of Theseus

### The continuing adventures of Jordan Hubbard and Sir Reginald von Fluffington III

> *Part 6 of an ongoing chronicle. [← Part 5: WebMux](https://github.com/jordanhubbard/webmux#the-totally-true-and-not-at-all-embellished-history-of-webmux)*
> *Sir Reginald von Fluffington III appears throughout. He does not endorse any of it.*

The programmer had been staring at two package trees for what Sir Reginald would later log under "an unreasonable number of mornings." On one screen: Nixpkgs, a sprawling functional graph of derivations, each one a pure function whose output was theoretically reproducible and in practice slightly different on every machine the programmer owned. On the other: FreeBSD Ports, a directory tree of Makefiles with the texture of sedimentary rock — ancient, load-bearing, and not especially interested in being modernized.

Both described the same software. Neither agreed with the other about what that software was.

"The problem," the programmer announced to Sir Reginald, who was at that moment sitting on the FreeBSD documentation and had no intention of moving, "is that there's no canonical form. Every ecosystem speaks its own dialect. You can't compare them. You can't rank them. You can't even tell if they're talking about the same package without reading both in full."

Sir Reginald opened one eye. This was not, his posture communicated, his problem.

"What I need," the programmer continued, rotating slightly in his chair so as to address the room at large, "is a schema. A modest one — nothing grandiose. Just enough structure to say: here is a package, here is what it depends on, here is where it came from, and here, crucially, is how confident I am that I understood any of that correctly."

Sir Reginald relocated from the FreeBSD documentation to the keyboard. The programmer chose to interpret this as a sign of interest.

The schema took shape over several days. It had identity fields — canonical name, ecosystem ID, version — and dependency arrays divided into build, host, runtime, and test. It had a build section that named the build system kind without attempting to capture its full complexity, on the grounds that full complexity was a trap the programmer had fallen into before. It had a provenance object that tracked not just where a record came from, but how much the importer trusted its own interpretation. The `confidence` field was, the programmer felt, the most honest thing he had ever put in a JSON schema. Most schemas pretended to certainty. This one admitted, in a structured and machine-readable way, that some of it was guesswork. He described this as "elegant." Sir Reginald, in response, stepped directly onto the Enter key and submitted a half-written email.

The project was called Theseus. The programmer had considered several names and discarded them. "CanonPkg" was too clinical. "Bridger" was too aspirational. "Theseus" was correct: you take a ship built by one civilization, replace every plank with one from another civilization, and ask whether it is still the same ship. The answer, the programmer believed, was "mostly, with appropriate provenance metadata." This was also, he noted, roughly his answer to most philosophical questions.

The bootstrap importer walked both source trees and emitted records into a snapshot directory, one JSON file per package per ecosystem. The overlap tool read those records and sorted them into categories: present in both ecosystems, present only in Nixpkgs, present only in FreeBSD Ports, and present in both but disagreeing about which version was current. The programmer found the version skew list particularly interesting. It turned out that `zlib` had an opinion about itself. So did `curl`. So, with some conviction, did `openssl`. None of their opinions were the same.

The candidate ranker applied heuristics to the overlap set and produced a scored list. The weights were documented in the source and the programmer made no attempt to obscure them: dual-ecosystem presence added twenty-five points, confidence scaled linearly, fewer dependencies scored higher, patches subtracted. "Provisional," the programmer acknowledged, to Sir Reginald, who had moved to the windowsill and was watching a bird with the focused attention he otherwise reserved for the programmer's longest explanations. The weights would change as more data arrived.

The schema grew three example records — `zlib`, `curl`, `openssl` — written by hand and cross-checked against both source trees. They were, the programmer believed, accurate. He had believed this about previous things with a frequency that reality did not consistently reward.

What happens after the ranking — the extraction phase the tools called "Z," a letter chosen for its quality of being terminal — is documented elsewhere. What mattered here was the foundation: a schema modest enough to be correct, tools simple enough to trust, and a snapshot format that preserved the provenance of every claim rather than discarding it for the sake of a cleaner output. The programmer had, for once in this project's young life, built something that admitted its own limitations as a structured field rather than a comment that no one would read.

Sir Reginald sat down on the printed schema. He had no notes. His position on the matter was architectural.

As of this writing, Theseus has been used in production by exactly one person, who also wrote it. Sir Reginald continues to withhold his endorsement across all 6 projects, citing "procedural concerns," "insufficient tuna," "a general atmosphere of hubris," and a documented skepticism toward confidence fields that score their own uncertainty higher than 0.9 while the author admits he might be wrong.
