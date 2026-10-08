# Theseus

> *You start with a ship. You replace the planks. You replace the mast. You replace the hull. At what point does it become a different ship? Theseus answered this question by not caring and sailing anyway.*

[![CI](https://github.com/jordanhubbard/Theseus/actions/workflows/ci.yml/badge.svg)](https://github.com/jordanhubbard/Theseus/actions/workflows/ci.yml)

> ### **OSS knowledge fabric · git is the database · characterization is supporting evidence**
>
> Theseus fingerprints packages: provenance, repository, license, and bidirectional dependencies, stored as committed JSON under `fabric/packages/`. Spec-driven recreation was attempted and did not scale; regenerative replacement is not the shipping claim ([ADR 0005](docs/decisions/0005-characterization-is-the-product.md), [ADR 0007](docs/decisions/0007-knowledge-fabric.md)). `make fabric-stats` is the coverage dashboard.

📖 **[Full User Guide →](https://jordanhubbard.github.io/Theseus/)** — installation, pipeline walkthrough, spec authoring, language reference. The full list of covered libraries lives in the user guide [Index](https://jordanhubbard.github.io/Theseus/#covered-library-index).

---

## What Theseus is

**Theseus** is a git-backed **OSS knowledge fabric**. It fingerprints open-source packages so we can answer: where did this come from, which repository is it, what license does it carry, what does it depend on, and what depends on it. The committed tree under [`fabric/packages/`](fabric/packages/) is the database — not SQLite, not a server. See [docs/knowledge-fabric.md](docs/knowledge-fabric.md) and [ADR 0007](docs/decisions/0007-knowledge-fabric.md).

Package recipes from four ecosystems feed that fabric:

- [**Nixpkgs**](https://github.com/NixOS/nixpkgs) — traversed via `--nixpkgs`, dependency graphs filled by `fill_nixpkgs_deps.py`
- [**PyPI**](https://pypi.org/) — imported via the PyPI JSON API (`make import-pypi`); source repositories backtracked to GitHub via `project_urls`
- [**npm**](https://www.npmjs.com/) — imported via the npm registry API (`make import-npm`); source repositories backtracked via the `repository` field
- [**FreeBSD Ports**](https://github.com/freebsd/freebsd-ports) — build-recipe source (20,000+ port Makefiles). FreeBSD is not a CI target platform.

Behavioral specs (Layer 2) remain as optional evidence attached to a fingerprint when they exist. Clean-room recreation from those specs was attempted; it is brittle, few components can be built entirely from a spec, and replacement is not the shipping claim ([ADR 0005](docs/decisions/0005-characterization-is-the-product.md)). Isolation is not API parity.

---

## Vocabulary

Terms used throughout the project, defined here before they appear in the rest of the README:

- **Fingerprint** — one committed JSON file under `fabric/packages/` recording a package's identity, provenance, repository, license, ecosystem sightings, and outbound dependencies. Reverse dependencies are derived from that graph.
- **Knowledge fabric** — the set of fingerprints plus the queries over them (`show`, `deps`, `rdeps`, `query`, `stats`). Git history is the audit trail.
- **Package recipe** — a Layer 1 canonical record (`specs/`, `examples/`) used as ingest input. Schema: `schema/package-recipe.schema.json`.
- **Behavioral spec** — optional Layer 2 evidence: a machine-readable file declaring observable invariants. Lives at `zspecs/<name>.zspec.zsdl`. Linked from a fingerprint when present.
- **Z-spec** / **zspec** — synonym for behavioral spec; the "Z" was chosen for being terminal (Z is the last letter — after Z, only verification remains).
- **ZSDL** — *Z-Spec Definition Language*. The YAML-flavoured surface syntax of `.zspec.zsdl` files. Compiles to JSON via `make compile-zsdl`. Full grammar: [docs/zsdl-design.md](docs/zsdl-design.md).
- **Invariant** — one falsifiable claim about behaviour (e.g. *"`semver.valid('1.2.3')` returns `'1.2.3'`"*). The verification harness asserts each invariant against the real installed library and reports pass/fail.
- **Compiled bundle** — the compiler emits one `.zspec.json` per source `.zsdl`. Depth and quality vary; see the [corpus autopsy](reports/audit/corpus-autopsy.md).
- **Backend** — how the spec runner loads the library under test: `ctypes` (C shared libraries via `ctypes.CDLL`), `python_module` (`importlib.import_module`), `node` (CJS or ESM via `node -e`), `cli` (`subprocess.run`).
- **Clean-room package** — a historical Theseus reimplementation registered in `theseus_registry.json`. `status=verified` means **legacy isolation**, not `qualified` replacement. Ladder: [ADR 0001](docs/decisions/0001-verification-ladder.md).

---

### Core Principles

- **Git is the database.** Fingerprints are committed files. Queries read the tree (or `git show <rev>:…`). No parallel SQL store.
- **Know before recreating.** Provenance, repository, license, and bidirectional dependencies are the product. Specs are evidence, not the goal.
- **Admit uncertainty.** Repository URLs and license SPDX IDs carry confidence. Ambiguous GitHub hits stay in `candidates`, not `url`.
- **Derive reverse edges.** Store outbound `depends_on` only; `rdeps` is computed so inbound links cannot drift.
- **No wrapping** (Layer 3 research only). A clean-room implementation must not `import` (or `require`) the original package.
- **Isolation-verified** (Layer 3 research only). Invariants run with the original blocked via `THESEUS_BLOCKED_PACKAGE`. `status=verified` is legacy isolation, not qualification.

### Knowledge fabric (the product)

```bash
make fabric-stats                 # coverage: repos, licenses, graph
make fabric-show PKG=requests     # one fingerprint
make fabric-deps PKG=requests     # outbound dependencies
make fabric-rdeps PKG=urllib3     # who depends on urllib3
make fabric-query FABRIC_LICENSE=MIT
make fabric-query FABRIC_REPO=github.com/psf
make refresh                      # restock specs/ from live upstreams, then ingest
make reingest                     # alias for make refresh
make fabric-ingest                # rebuild fabric/packages/ from already-committed recipes
```

Each package is `fabric/packages/<name>.json`. `git log -- fabric/packages/requests.json` is that row's history. Details: [docs/knowledge-fabric.md](docs/knowledge-fabric.md).

### Clean-room packages (historical research — not the product)

The packages below passed the old isolation harness. None are `qualified` under ADR 0001. `theseus_json` is the ADR 0002 gold-set spike: public `dumps`/`loads` oracle plus a held-out file the synthesizer never sees. Gold-set families have reviewed uncertainty ledgers ([ADR 0003](docs/decisions/0003-characterization-loop.md)) and a qualification protocol ([ADR 0004](docs/decisions/0004-qualification-protocol.md)). One hundred two Python families were attempted; 102 (`adler32`, `array`, `ast`, `b16encode`, `base64`, `binascii`, `bisect`, `bisectleft`, `calendar`, `category`, `ceil`, `chainmap`, `cleandoc`, `close_matches`, `cmath`, `cmd`, `codecs`, `collections`, `colorsys`, `comb`, `contextlib`, `copy`, `copysign`, `csv`, `ctxvar`, `datamode`, `datetime`, `decimal`, `deque`, `difflib`, `dist`, `email_utils`, `fabs`, `floor`, `fnmatch`, `fnmatchcase`, `fractions`, `getopt`, `gettext`, `glob`, `hashlib`, `heapq`, `hexlify`, `hmac`, `html`, `http_cookies`, `hypot`, `indent`, `io`, `ipaddress`, `isqrt`, `itertools`, `json`, `keyword`, `lcm`, `loggername`, `math`, `medianlow`, `mimetypes`, `nlargest`, `ntpath`, `operator`, `optionxform`, `ordereddict`, `pathlib`, `perm`, `pickle`, `posixpath`, `pprint`, `prod`, `pyuuid`, `queue`, `quopri`, `quoteplus`, `re`, `reprlib`, `secrets`, `semaphore`, `shlex`, `shorten`, `stat`, `statistics`, `string`, `stringio`, `struct`, `tarinfo`, `tdelta`, `template`, `textwrap`, `threadlock`, `time`, `trunc`, `types`, `unhexlify`, `unicodedata`, `unquote`, `urllib_parse`, `usagefmt`, `wsgiref`, `xml_etree`, `zipinfo`, `zlib`) have dual-generation receipts. The numeric kill gate is no longer fired. ADR 0005 is not superseded, so replacement is not the product claim. The characterization cohort under `gold/<family>/` covers high-feasibility Layer 2 specs and the medium public-API families whose oracles pass the installed library, without claiming qualification.

| Package | Language | Isolation invariants | Replaces (claim withdrawn) |
|---|---|---|---|
| `theseus_json` | Python | 26 public-API (`dumps`/`loads`) | `json` |
| `theseus_re` | Python | 3/3 | `re` |
| `theseus_pathlib` | Python | 3/3 | `pathlib` / `os.path` |
| `theseus_path_node` | Node.js | 3/3 | Node `path` |

Full withdrawn list: [`reports/audit/withdrawn-verified.json`](reports/audit/withdrawn-verified.json) (396 packages).

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
- Node.js 22+ and npm (for Node.js-backed specs declared in `package.json`)
- Python tooling from `requirements.txt` (pytest, PyYAML, MkDocs Material)

### Install

```bash
git clone https://github.com/jordanhubbard/Theseus
cd Theseus
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm install
make
```

Dependency evidence for OSS review lives in
[`docs/dependency-evidence.md`](docs/dependency-evidence.md). It records the
Python manifests, npm lockfile, pinned GitHub Actions, Docker base-image digest,
license metadata, and scanner scope for ephemeral agent worktrees.

### Run the test suite

```bash
make test
```

### Demo on the committed fabric

```bash
make start        # fabric coverage, then analysis on examples/
make fabric-stats
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
fabric/         Git-backed knowledge fabric (packages/*.json) — the database
theseus/        Python package: fabric, importer, drivers, remote, store, agent
tools/          CLI: fabric.py plus recipe, spec, and research scripts
specs/          Canonical package recipes (ingest source, 232 packages)
examples/       Hand-written sample recipes (curl, openssl, zlib)
schema/         JSON Schema (fingerprints + package recipes)
zspecs/         Optional Layer 2 Z-spec sources (*.zspec.zsdl)
_build/zspecs/  Compiled specs — build artifact, not committed
docs/           Architecture, fabric, ZSDL, spec-authoring guide
docs/guide/     User guide source (built to GitHub Pages)
tests/          Test suite
scripts/        Release automation
```

---

## Makefile Targets

```
make / make all          Check Python version, print usage
make start               Fabric stats, then analysis on SNAPSHOT= or examples/
make fabric-stats        Coverage of the committed knowledge fabric
make fabric-show         One fingerprint (PKG=name)
make fabric-deps         Outbound dependencies (PKG=name)
make fabric-rdeps        Reverse dependencies (PKG=name)
make fabric-query        Filter by FABRIC_LICENSE=, FABRIC_REPO=, FABRIC_ECOSYSTEM=, FABRIC_NAME=
make refresh             Restock specs/ from live PyPI/npm/Nixpkgs/Ports, then ingest
make reingest            Alias for make refresh
make fabric-ingest       Rebuild fabric/packages/ from specs/ + examples/
make fabric-validate     Validate committed fingerprints
make test                Validate Z-specs then run test suite
make compile-zsdl        Compile zspecs/*.zspec.zsdl → _build/zspecs/*.zspec.json
make verify-behavior     Run one spec (ZSPEC=path)
make import-pypi         Fetch PyPI metadata with source_repository backtracking
make import-npm          Fetch npm metadata with source_repository backtracking
make validate-zspecs     Validate Z-spec JSON files against schema
make clean               Remove build artifacts
make help                Full target and variable reference
```

---

## Schema

Fingerprints (`schema/fingerprint.schema.json`) capture identity, repository, license, ecosystems, outbound dependencies, evidence links, and provenance. Package recipes (`schema/package-recipe.schema.json`) remain the ingest format (identity, build, sources, patches, platforms, tests, provenance, optional `behavioral_spec`). See [docs/knowledge-fabric.md](docs/knowledge-fabric.md) and [docs/architecture.md](docs/architecture.md).

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

Track work with [GitHub Issues](https://github.com/jordanhubbard/Theseus/issues) (`gh issue list`). Do not use Beads or Dolt.

---

## License

[BSD 2-Clause](LICENSE)

---

## The Totally True and Not At All Embellished History of Theseus

### The continuing adventures of Jordan Hubbard and Sir Reginald von Fluffington III

> *Part 12 of an ongoing chronicle. [← Part 11: usdagent](https://github.com/jordanhubbard/usdagent#the-totally-true-and-not-at-all-embellished-history-of-usdagent) | [Part 13: agentOS →](https://github.com/jordanhubbard/agentos#the-totally-true-and-not-at-all-embellished-history-of-agentos)*
> *[Chronicle index](https://github.com/jordanhubbard/ai-template/blob/main/CHRONICLE.md) · Ordered by first recorded AI-assisted commit.*
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

Years later the programmer returned to the ship with a larger crew of language models and a troubling inventory: hundreds of planks labeled "verified" that, on inspection, were three coats of varnish on the original hull. Sir Reginald, who had been napping inside a held-out crate the synthesizers were forbidden to open, declined to move. The crew wrote down what the libraries actually *did*, checked those notes against the real fittings, and attempted ten replica keels in an empty dry dock. None of the keels were laid twice by independent shipwrights, so none were certified to sail. The programmer announced that the product was the notes. The crew then catalogued fifteen more fittings that had always been honest Layer 2 oracles and still were not ships. Sir Reginald's tail, hanging out of the crate, was recorded as an abstention.

Later still the programmer admitted the notes-as-product story had the same shape as the replica-keel story: a lot of ceremony around a thing almost nobody could actually *build*. Sir Reginald, who had relocated from the held-out crate to the `.git` directory and was shedding on the objects, suggested an alternative so obvious it was slightly insulting. Stop asking whether the ship can be rebuilt from a description of how it sails. Ask whether you know whose ship it is, where the plans live, what license is painted on the transom, and which other vessels are lashed to it. Put each answer in a file. Let git be the harbourmaster's ledger. The programmer called this a "knowledge fabric," which was a grand name for a directory of JSON, and Sir Reginald called it "finally writing things down in the one database that was already there." He did not get up.

The docks, of course, refused to stay still. PyPI renamed a tarball. npm shipped a patch. Nixpkgs moved a derivation two directories to the left and called it `by-name`. The programmer, who had previously restocked the ledger by rummaging for a snapshot directory that git was specifically instructed to forget, added a tide table: `make refresh`. Sir Reginald described this as "asking the harbour what is actually tied up today, rather than what was tied up in March," and returned to the objects.

As of this writing, Theseus has been used in production by exactly one person, who also wrote it. Sir Reginald continues to withhold his endorsement across the chronicle, citing "procedural concerns," "insufficient tuna," "a general atmosphere of hubris," and a documented skepticism toward confidence fields that score their own uncertainty higher than 0.9 while the author admits he might be wrong.
