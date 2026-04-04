# Theseus

> *You start with a ship. You replace the planks. You replace the mast. You replace the hull. At what point does it become a different ship? Theseus answered this question by not caring and sailing anyway.*

**Theseus** is a toolchain for normalizing package recipes from [Nixpkgs](https://github.com/NixOS/nixpkgs) and [FreeBSD Ports](https://github.com/freebsd/freebsd-ports) into a shared canonical intermediate representation — a common schema that lets you compare, rank, and reason about packages across ecosystems without losing track of where they came from.

## Features

### Package recipe pipeline

- **Canonical JSON schema** (`schema/package-recipe.schema.json`) — covers identity, dependencies, build system, sources, patches, platforms, features, tests, and provenance
- **Bootstrap importer** (`tools/bootstrap_canonical_recipes.py`) — walks Nixpkgs and FreeBSD Ports trees and emits canonical records into a snapshot directory
- **Overlap report** (`tools/overlap_report.py`) — identifies packages present in both ecosystems, present only in one, and those with version skew
- **Candidate ranker** (`tools/top_candidates.py`) — scores packages as first candidates for downstream extraction using heuristics: dual-ecosystem presence, provenance confidence, dependency count, test coverage, patch complexity
- **Phase Z extractor** (`tools/extract_candidates.py`) — takes the ranked candidate list and produces one merged record per top-N package: unified dependencies, maintainers, sources, and a structured analysis section covering version agreement, confidence, license agreement, and deprecation status across ecosystems; auto-injects `behavioral_spec` for any candidate that has a matching Z-spec
- **Record validator** (`tools/validate_record.py`) — validates canonical records against schema rules; reports type errors, missing fields, and out-of-range confidence scores; runs the behavioral spec harness for records with a `behavioral_spec` field
- **Snapshot diff** (`tools/diff_snapshots.py`) — compares two snapshot directories and classifies every package as added, removed, version-changed, or unchanged; tracks ecosystem drift between bootstrap runs

### Z-layer behavioral spec system

- **18 behavioral specs** (`zspecs/*.zspec.zsdl`) — machine-readable contracts covering zlib, hashlib, base64, json, struct, datetime, pathlib, re, sqlite3, openssl, curl, semver, ajv, uuid, minimist, urllib_parse, difflib, zstd; compiled to `_build/zspecs/`
- **Verification harness** (`tools/verify_behavior.py`) — runs every invariant against the real installed library; supports ctypes (C shared libs), python_module (Python stdlib/packages), and cli (subprocesses + Node.js npm packages) backends
- **Spec validator** (`tools/validate_zspec.py`) — validates spec files against `zspecs/schema/behavioral-spec.schema.json`
- **Batch runner** (`tools/verify_all_specs.py`) — runs all specs and writes a JSON results file for CI dashboards and regression tracking
- **Coverage reporter** (`tools/spec_coverage.py`) — shows which extracted candidates have a behavioral spec and which are gaps
- **Watch mode** (`--watch`) — polls the spec file and reruns on every save for TDD-style authoring
- **Baseline/diff mode** (`--baseline`) — diffs a run against a saved results file, reports regressions

## Quick Start

### Requirements

- Python 3.9+
- Node.js 22+ and npm (for Node.js-backed Z-specs: semver, ajv, uuid, minimist)
- `pytest` for running the test suite
- `packaging` (optional; improves `spec_for_versions` range checking — usually already installed with pip)

### Install

```bash
git clone https://github.com/jordanhubbard/Theseus
cd Theseus
pip install pytest   # needed for make test
npm install          # installs semver, ajv, uuid, minimist (needed for Node.js Z-specs)
make                 # verifies Python version, prints usage
```

### Typical workflow

**1. Bootstrap** canonical records from source trees:

```bash
python3 tools/bootstrap_canonical_recipes.py \
  --nixpkgs /path/to/nixpkgs \
  --ports /path/to/freebsd-ports \
  --out ./snapshots/$(date +%Y-%m-%d)
```

**2. Generate overlap report:**

```bash
make report SNAPSHOT=./snapshots/2026-03-26
```

**3. Generate candidate ranking:**

```bash
make candidates SNAPSHOT=./snapshots/2026-03-26
```

**4. Extract top candidates (phase Z):**

```bash
make extract SNAPSHOT=./snapshots/2026-03-26
```

Reports land in `reports/`. Extractions land in `reports/extractions/`, one JSON per package plus a `manifest.json`.

**5. Run behavioral spec verification** (optional but recommended):

```bash
make verify-all-specs            # run all 15 specs, text summary
make verify-all-specs-json       # same, writes JSON results file
python3 tools/verify_behavior.py _build/zspecs/zlib.zspec.json --watch   # TDD mode
```

**6. Check which candidates have behavioral specs:**

```bash
make spec-coverage EXTRACTION_DIR=reports/extractions/
```

## Project Layout

```
theseus/
  theseus/        — Python package: core importer logic (theseus/importer.py)
  tools/          — CLI analysis and verification scripts
    bootstrap_canonical_recipes.py  — entry-point shim (logic in theseus/importer.py)
    overlap_report.py               — compare ecosystems
    top_candidates.py               — rank packages by score
    extract_candidates.py           — phase Z: merge top candidates
    validate_record.py              — validate canonical records
    diff_snapshots.py               — diff two snapshot directories
    verify_behavior.py              — Z-spec harness: run invariants against library
    validate_zspec.py               — Z-spec static schema validator
    verify_all_specs.py             — run all specs, write JSON results
    spec_coverage.py                — report covered vs gap candidates
  schema/         — JSON Schema for canonical package recipe records
  zspecs/         — Z-layer spec sources (*.zspec.zsdl) and schema (schema/)
  _build/zspecs/  — compiled spec files (*.zspec.json, build artifacts — not in git)
    schema/       — JSON Schema for Z-spec files (behavioral-spec.schema.json)
  examples/
    freebsd_ports/ — Sample FreeBSD Ports canonical records (curl, openssl, zlib)
    nixpkgs/       — Sample Nixpkgs canonical records (curl, openssl, zlib)
  snapshots/      — Generated: importer output (one subdirectory per run)
  reports/        — Generated: overlap reports, rankings, extractions
  tests/          — Test suite (1025 tests)
  docs/           — Architecture and design documentation
```

## Schema

The canonical schema (`schema/package-recipe.schema.json`) captures:

| Field | Purpose |
|-------|---------|
| `identity` | Canonical name/ID, ecosystem, ecosystem-specific ID, version |
| `descriptive` | Summary, homepage, license, categories |
| `sources` | Download URLs and types |
| `dependencies` | Build, host, runtime, and test dependency lists |
| `build` | Build system kind and flags |
| `features` | Optional feature flags / knobs |
| `platforms` | Include/exclude platform lists |
| `patches` | Applied patches with reasons |
| `tests` | Test phase presence and structure |
| `provenance` | Source path, commit, importer, confidence score, warnings, unmapped fields |
| `extensions` | Ecosystem-specific extra fields (passthrough, no normalization) |
| `behavioral_spec` | Optional: repo-relative path to a matching `_build/zspecs/*.zspec.json` (auto-injected by extractor) |

The schema is intentionally modest. It captures enough structure to compare ecosystems, rank packages, and feed later extraction phases while preserving provenance and lossiness signals. It is not a full semantic model of Nix or FreeBSD Ports.

## Development

```bash
make test     # run the test suite
make start    # run analysis on examples/ as a quick demo
make clean    # remove generated artifacts
```

## Configuration

No runtime configuration is required. The schema version is embedded in each record (`schema_version`). Tool behavior is controlled entirely by command-line arguments.

## Deployment

Theseus is a local analysis toolchain. There is no server component and no deployment step. Run it anywhere Python 3.9+ is available.

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
