# Theseus — System Specification

## 1. Purpose and Scope

Theseus is a clean-room package synthesis engine with three integrated capabilities:

1. **Provenance establishment** — machine-readable documentation of what public sources a software specification was derived from, and what implementation sources it was explicitly NOT derived from.
2. **Behavioral verification** — running a precise contract (a *spec*) against a real installed library to prove the contract is accurate.
3. **Clean-room synthesis** — using only the verified contract (never the original source code) to generate a new implementation that satisfies all behavioral invariants.

The system is a batch toolchain with no server, no daemon, and no external runtime dependencies beyond Python 3.9+ stdlib. All state is in plain files on disk.

**In scope:**
- Python packages (stdlib and third-party)
- Node.js packages
- Native libraries exposed via `ctypes`
- CLI tools with stable stdout behavior

**Out of scope:**
- GUI applications
- Packages requiring GPU or hardware-specific features
- Packages with non-deterministic output that cannot be expressed as invariants
- Replacing the original package in production (the clean-room implementation is a provenance artifact, not a drop-in replacement)

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **Spec** | A `.zspec.zsdl` source file describing a library's behavior via invariants and provenance metadata. |
| **ZSDL** | Z-layer Specification Definition Language — a YAML superset with four custom binary-data tags (`!b64`, `!hex`, `!ascii`, `!tuple`). |
| **Compiled spec** | A `.zspec.json` file produced by compiling a `.zspec.zsdl` file; consumed by the verification harness. |
| **Invariant** | A zero-argument assertion about a library: call a function with fixed inputs, assert the output equals a fixed expected value. |
| **Backend** | How a spec's library is loaded: `python_module`, `python_cleanroom`, `ctypes`, `node_module`, `cli`. |
| **Clean-room implementation** | A new implementation of a library written from a spec alone, without reading the original implementation source. Lives in `cleanroom/python/<name>/` or `cleanroom/node/<name>/`. |
| **Verified package** | A clean-room implementation that has passed all invariants in an isolated environment where the original package is blocked. Registered in `theseus_registry.json` with `status: verified`. |
| **Isolation harness** | `cleanroom/python/sitecustomize.py` — Python's auto-loaded site customization file that intercepts imports and raises `ImportError` for any package named in `THESEUS_BLOCKED_PACKAGE`. |
| **Wave** | A named batch of specs processed together in one synthesis run. Wave names follow the pattern `cr1`, `cr2`, etc. |
| **Registry** | `theseus_registry.json` — the authoritative list of clean-room packages, their paths, and verification status. |

---

## 3. System Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║  LAYER 1 — Package Recipe Pipeline                                   ║
║                                                                      ║
║  Source trees (Nixpkgs, FreeBSD Ports, PyPI, npm, Cargo)            ║
║       │                                                              ║
║       ▼                                                              ║
║  snapshots/<date>/          ← one JSON file per package              ║
║       │                                                              ║
║       ├─► overlap_report.py   compare ecosystems                     ║
║       ├─► top_candidates.py   rank by synthesis suitability          ║
║       └─► extract_candidates.py  merge top-N into extractions/       ║
╚══════════════════════════════════════════════════════════════════════╝
         │
         ▼ (candidates inform which specs to write)
╔══════════════════════════════════════════════════════════════════════╗
║  LAYER 2 — Behavioral Specification (ZSDL)                           ║
║                                                                      ║
║  zspecs/*.zspec.zsdl        ← source specs (committed)              ║
║       │                                                              ║
║       ▼ make compile-zsdl                                            ║
║  _build/zspecs/*.zspec.json ← compiled (build artifact)             ║
║       │                                                              ║
║       ▼ make verify-behavior ZSPEC=path                              ║
║  PASS/FAIL per invariant    ← validates spec accuracy                ║
╚══════════════════════════════════════════════════════════════════════╝
         │
         ▼ (verified spec drives synthesis)
╔══════════════════════════════════════════════════════════════════════╗
║  LAYER 3 — Clean-Room Synthesis                                      ║
║                                                                      ║
║  zspecs/theseus_*.zspec.zsdl  ← clean-room specs (python_cleanroom) ║
║       │                                                              ║
║       ▼ make pipeline SYNTH_ZSDL=path                                ║
║  cleanroom/python/<name>/   ← synthesized implementation            ║
║       │                                                              ║
║       ▼ cleanroom_verify.py  (original blocked via env var)          ║
║  PASS/FAIL isolation test   ← proves no import of original          ║
║       │                                                              ║
║       ▼ registry.py verify <name>                                    ║
║  theseus_registry.json      ← verified packages                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 4. Data Formats

### 4.1 Package Record (Layer 1)

Canonical JSON stored in `snapshots/<date>/<ecosystem>/<name>.json`. Fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Package name |
| `version` | string | Current version |
| `ecosystem` | string | `nixpkgs`, `freebsd_ports`, `pypi`, `npm`, `cargo` |
| `description` | string | One-line description |
| `homepage` | string | Project URL |
| `licenses` | list[string] | SPDX license identifiers |
| `dependencies` | list[string] | Runtime dependency names |
| `build_dependencies` | list[string] | Build-time dependency names |
| `meta` | dict | Ecosystem-specific metadata |

### 4.2 ZSDL Spec Format (Layer 2)

Source format: `zspecs/<name>.zspec.zsdl`

```yaml
spec: <canonical-name>
version: "<semver-range>"
backend: <backend-expression>

docs: <primary-reference-url>
rfcs:
  - "<RFC number and title>"

provenance:
  derived_from:
    - "<public source 1>"
    - "<public source 2>"
  not_derived_from:
    - "<implementation file 1>"
    - "<implementation file 2>"
  notes: "<human explanation of clean-room boundary>"
  created_at: "<ISO 8601 timestamp>"

constants:
  <group>:
    <NAME>: {value: <int>, description: "<text>"}

invariants:
  - function: <callable-name>
    args: [<arg1>, <arg2>]
    expected: <value>
    kind: <invariant-kind>
    id: <unique-id>
    describe: "<human description>"
```

**Backend expressions:**

| Expression | Meaning |
|------------|---------|
| `python_module(<module>)` | Standard library or installed Python module |
| `python_cleanroom(<name>)` | Clean-room reimplementation (synthesis target) |
| `ctypes(<libname>)` | Native C library loaded via ctypes |
| `node_module(<module>)` | Node.js require() module |
| `cli(<command>)` | CLI tool; invariants check stdout |

**Custom YAML tags for binary data:**

| Tag | Serialized as |
|-----|---------------|
| `!b64 <base64-string>` | `{"type": "bytes_b64", "value": "..."}` |
| `!hex <hex-string>` | `{"type": "bytes_hex", "value": "..."}` |
| `!ascii <text>` | `{"type": "bytes_ascii", "value": "..."}` |
| `!tuple [...]` | `{"type": "tuple", "value": [...]}` |

**Invariant kinds:**

| Kind | Description |
|------|-------------|
| `python_call_eq` | Call function with args, assert result equals expected |
| `python_call_raises` | Call function, assert it raises the named exception |
| `python_encode_decode_roundtrip` | Encode then decode, assert equals original |
| `call_eq` | ctypes function call, assert integer return code |
| `constant_eq` | Assert a named constant equals expected value |
| `hash_known_vector` | Feed known input to hash function, assert hex digest |
| `hash_incremental` | Feed data in chunks, assert equals one-shot digest |
| `hash_object_attr` | Assert hash object attribute (digest_size, etc.) |
| `cli_stdout_eq` | Run CLI command, assert stdout equals expected |
| `node_module_call_eq` | Node.js `require(mod)[fn](...args)`, assert return value |
| `node_constructor_call_eq` | `new mod.Class(ctorArgs).method(args)`; optional `then_call: true` chains an invocation on the return |
| `node_factory_call_eq` | `m()[method](...)` — two-step factory + method (e.g. `express()`, `yargs(argv).parseSync()`) |
| `node_chain_eq` | Arbitrary `{method|get|call}` chain off an initial value (entry: `module`/`named`/`constructor`/`factory`); supports dotted names like `default.Separator` |
| `node_property_eq` | Sugar for `node_chain_eq` with a single `{get}` step — read one property after construction or a factory call |
| `node_sandbox_chain_eq` | `node_chain_eq` inside a per-invariant tempdir cwd seeded by `setup` (paths + content). For glob/fs-extra/mkdirp/rimraf/find-up. |
| `ctypes_chain_eq` | Sequence of ctypes calls threading an opaque handle/pointer; restype tokens (`c_int`/`c_char_p`/`c_void_p`/…); per-step `capture: name`; `{capture: name}`/`{errbuf: N}` arg dicts. For libpcap-style stateful C APIs. |
| `ctypes_sandbox_chain_eq` | `ctypes_chain_eq` + per-invariant tempdir seeded by `setup` with `content_b64` for binary blobs; `{sandbox_path: rel}` resolves to absolute path bytes. For libpcap/pcapng savefile-header parsing. |
| `version_prefix` | Assert version string starts with expected prefix |
| `roundtrip` | Compress then decompress, assert byte equality |
| `wire_bytes` | Assert compressed output has specific byte properties |

### 4.3 Compiled Spec Format

`_build/zspecs/<name>.zspec.json` — produced by `tools/zsdl_compile.py`:

```json
{
  "schema_version": 1,
  "identity": {
    "canonical_name": "<name>",
    "spec_for_versions": "<semver-range>",
    "public_docs_url": "<url>"
  },
  "library": {
    "backend": "<backend-type>",
    "module_name": "<name>"
  },
  "provenance": { ... },
  "constants": { ... },
  "invariants": [
    {
      "id": "<unique-id>",
      "description": "<text>",
      "kind": "<invariant-kind>",
      "spec": {
        "function": "<callable>",
        "args": [...],
        "expected": <value>
      },
      "category": "<grouping>",
      "rfc_reference": "<RFC citation or null>"
    }
  ]
}
```

### 4.4 Registry Format

`theseus_registry.json`:

```json
{
  "version": 1,
  "description": "Registry of Theseus clean-room package verification status",
  "packages": {
    "<name>": {
      "cleanroom_path": "cleanroom/python/<name>",
      "spec": "zspecs/<name>.zspec.zsdl",
      "status": "verified | pending | failed | policy_failed"
    }
  }
}
```

Only packages with `status: verified` may be imported by other clean-room implementations.

### 4.5 Clean-Room Implementation

`cleanroom/python/<name>/__init__.py` — a Python module that:
- Implements the full public API specified in the corresponding `.zspec.zsdl`
- Does NOT import the original package
- May only import from Python stdlib or from other verified Theseus packages
- Passes all invariants in `cleanroom_verify.py` with the original blocked

---

## 5. Component Specifications

### 5.1 ZSDL Compiler (`tools/zsdl_compile.py`)

**Input:** One or more `.zspec.zsdl` source files  
**Output:** Corresponding `.zspec.json` compiled files in `_build/zspecs/`  
**Guarantees:**
- Fails fast on YAML parse errors
- Custom tags (`!b64`, `!hex`, `!ascii`, `!tuple`) are resolved to typed dicts
- Table invariants are expanded into individual invariant objects
- All invariant `id` fields are globally unique within a spec

**Invocation:**
```bash
make compile-zsdl                    # all specs
make compile-zsdl ZSDL=zspecs/zlib.zspec.zsdl   # one spec
```

### 5.2 LLM Agent (`theseus/agent.py`)

**Purpose:** Provides a unified interface for all LLM synthesis backends.

**Supported providers:**

| `provider` value | Mechanism | Configuration |
|-----------------|-----------|---------------|
| `auto` | Tries CLI agents (claude → codex → droid) then OpenAI endpoint | Default |
| `claude` | Claude CLI subprocess (`claude --print -`) | Install from claude.ai/code |
| `codex` | OpenAI Codex CLI subprocess (`codex --quiet -`) | Install from github.com/openai/codex |
| `droid` | Generic CLI agent (same stdin protocol) | Set `cli_agent_command: droid` |
| `openai` | OpenAI-compatible HTTP endpoint | `openai_base_url`, `openai_model` |
| `cli_agent` | Any CLI agent reading stdin, printing to stdout | `cli_agent_command`, `cli_agent_args` |

**Invariant:** All providers receive the same prompt text and return plain text responses. No provider-specific prompt engineering is needed.

### 5.3 Verification Harness (`tools/verify_behavior.py`)

**Input:** A compiled `.zspec.json` file; the library it describes must be installed (use `make verify-behavior-docker` for on-demand installation without polluting the host)
**Output:** PASS/FAIL per invariant; aggregate count  
**Guarantees:**
- Loads the library using the backend specified in the spec
- Executes each invariant as described
- `--filter <substring>` runs only matching invariants
- `--verbose` prints pass/fail per invariant
- `--json-out <file>` writes machine-readable results
- `--list` prints invariant ids without running them

**Invocation:**
```bash
make verify-behavior ZSPEC=_build/zspecs/zlib.zspec.json
make verify-behavior ZSPEC=_build/zspecs/hashlib.zspec.json FILTER=sha256 VERBOSE=1
make verify-all-specs          # runs all; prints aggregate
```

### 5.4 Docker Verification Sandbox (`tools/verify_in_docker.py`)

**Purpose:** Run verification inside a disposable Ubuntu 26.04 container so packages are never installed on the host machine. Required for all backend types that need external installation: `python_module` (pip), `ctypes` (apt), `node_module` (npm), `rust_module` (cargo), and `cli` (apt).

**Image:** `docker/Dockerfile.verify` — Ubuntu 26.04 with Python 3, Node.js, Rust/cargo, and common C dev libraries pre-installed. Built once with `make docker-build`; reused for all subsequent verifications.

**Steps:** compile spec → build/reuse image → start container (repo mounted at `/theseus`) → install requested packages → run `verify_behavior.py` → remove container.

**Guarantees:**
- No packages installed on the host
- All backend types supported via `--pip`, `--apt`, `--npm`, `--cargo` flags
- Container is removed after each run (unless `--keep` is passed)
- The same compiled spec and verify tool are used as in direct `make verify-behavior`

**Invocation:**
```bash
make docker-build                                                    # one-time image build
make verify-behavior-docker ZSDL=zspecs/zlib.zspec.zsdl            # stdlib (no packages)
make verify-behavior-docker ZSDL=zspecs/requests.zspec.zsdl PIP=requests
make verify-behavior-docker ZSDL=zspecs/zlib_ctypes.zspec.zsdl APT=zlib1g-dev
make verify-behavior-docker ZSDL=zspecs/chalk.zspec.zsdl NPM=chalk
make verify-behavior-docker ZSDL=zspecs/serde_json_rust.zspec.zsdl CARGO=serde_json
```

### 5.6 Search Tool (`tools/search_specs.py`)

**Input:** Optional query string and filter flags  
**Output:** Table of matching specs with backend, invariant count, verification status  
**Invocation:**
```bash
make search QUERY=json
make search BACKEND=python_cleanroom VERIFIED=1
make search QUERY=zlib JSON=1
python3 tools/search_specs.py --list
```

### 5.7 Comparison Tool (`tools/compare_specs.py`)

**Input:** Two compiled `.zspec.json` files (or `.zspec.zsdl` paths auto-resolved)  
**Output:** Common invariants, invariants unique to each spec, behavioral differences  
**Invocation:**
```bash
make compare SPEC1=_build/zspecs/json.zspec.json SPEC2=_build/zspecs/simplejson.zspec.json
make compare SPEC1=zspecs/hashlib.zspec.zsdl SPEC2=zspecs/_hashlib.zspec.zsdl JSON=1
```

### 5.8 Provenance Report Tool (`tools/provenance_report.py`)

**Input:** A `.zspec.zsdl` source file  
**Output:** Markdown (default) or JSON provenance attestation  
**Content:**
- `derived_from` — public sources used to write the spec
- `not_derived_from` — implementation files explicitly excluded
- Verification status from registry
- Invariant table (the behavioral boundary)

**Invocation:**
```bash
make provenance-report SPEC=zspecs/zlib.zspec.zsdl
make provenance-report SPEC=zspecs/hashlib.zspec.zsdl PROV_OUT=reports/hashlib-provenance.md
make provenance-report SPEC=zspecs/json.zspec.zsdl JSON=1
```

### 5.9 Clean-Room Synthesis Pipeline (`tools/run_pipeline.py`)

**Input:** A `.zspec.zsdl` with `backend: python_cleanroom(...)` or `node_cleanroom(...)`  
**Steps:**
1. Compile the spec → `_build/zspecs/<name>.zspec.json`
2. Verify the spec against the real library (to confirm invariants are correct)
3. Invoke LLM to synthesize an implementation (up to `SYNTH_MAX_ITER` attempts)
4. Run isolation verification (`cleanroom_verify.py`) — original package blocked
5. On pass: register the package in `theseus_registry.json` with `status: verified`

**Invocation:**
```bash
make pipeline SYNTH_ZSDL=zspecs/theseus_json.zspec.zsdl
make pipeline SYNTH_ZSDL=zspecs/theseus_hashlib.zspec.zsdl SYNTH_MAX_ITER=5 VERBOSE=1
```

### 5.10 Isolation Mechanism

**File:** `cleanroom/python/sitecustomize.py`  
**Mechanism:** Python automatically executes this file on startup. It reads the `THESEUS_BLOCKED_PACKAGE` environment variable and installs an import hook that raises `ImportError("THESEUS ISOLATION VIOLATION: ...")` for any matching import.

```bash
THESEUS_BLOCKED_PACKAGE=json python3 -c "import theseus_json"   # must succeed
THESEUS_BLOCKED_PACKAGE=json python3 -c "import json"            # must raise ImportError
```

**Guarantee:** A clean-room implementation that passes `cleanroom_verify.py` cannot depend on the original package, even transitively through a dependency that itself imports the original.

### 5.11 Registry (`tools/registry.py`)

**File:** `theseus_registry.json`  
**Invariant:** Only packages with `status: verified` are usable as dependencies in other clean-room implementations.

```bash
python3 tools/registry.py list
python3 tools/registry.py check theseus_json          # exits 0 if verified
python3 tools/registry.py register <name> <path> <spec>
python3 tools/registry.py verify <name>               # run verifier and promote
```

---

## 6. Protocols

### 6.1 Provenance Establishment Protocol

To establish provenance for a library:

1. Identify public sources: API documentation, RFCs, header files (declarations only, not implementations).
2. Write a `.zspec.zsdl` file. Populate `provenance.derived_from` with the public sources used. Populate `provenance.not_derived_from` with the implementation source files you did not consult.
3. Write invariants that capture the library's observable behavior.
4. Compile and verify: `make compile-zsdl ZSDL=... && make verify-behavior ZSPEC=...`
5. Generate attestation: `make provenance-report SPEC=zspecs/<name>.zspec.zsdl`

The attestation is a machine-checkable document: every invariant in it can be independently re-run against the real library with `make verify-behavior`.

### 6.2 Search Protocol

To find specs for a library or ecosystem area:

```bash
make search QUERY=<name-or-keyword>    # search by name/docs
make search BACKEND=python_cleanroom   # all clean-room specs
make search VERIFIED=1                 # only verified packages
python3 tools/registry.py list         # all registered packages with status
```

### 6.3 Comparison Protocol

To compare two libraries with existing specs:

```bash
make compile-zsdl                      # ensure both are compiled
make compare SPEC1=_build/zspecs/<a>.zspec.json SPEC2=_build/zspecs/<b>.zspec.json
```

The report shows: how many invariants the two specs share by function name, what each spec covers that the other does not, and any cases where the same function has different expected values (behavioral divergence).

### 6.4 Clean-Room Synthesis Protocol

To create a new clean-room implementation:

1. Find or write the behavioral spec: `zspecs/<name>.zspec.zsdl` with `backend: python_cleanroom(<impl-name>)`.
2. Run: `make pipeline SYNTH_ZSDL=zspecs/<name>.zspec.zsdl`
3. The pipeline synthesizes an implementation in `cleanroom/python/<impl-name>/`, verifies it in isolation, and registers it.
4. Confirm: `python3 tools/registry.py check <impl-name>`

For batch synthesis of many packages: `make synthesize-waves-next`

---

## 7. Invariants and Guarantees

| Guarantee | How enforced |
|-----------|-------------|
| Spec accuracy | `make verify-behavior` passes against real library |
| Clean-room isolation | `cleanroom_verify.py` with `THESEUS_BLOCKED_PACKAGE` set |
| No wrapper patterns | `tools/lint_cleanroom.py` (run in CI via `make test`) |
| Dependency integrity | Registry gate: only `status: verified` packages may be imported |
| Provenance traceability | Every spec has a `provenance` block; `make provenance-report` generates attestation |

---

## 8. Limitations and Non-Goals

- **LLM synthesis is non-deterministic.** The pipeline re-runs up to `SYNTH_MAX_ITER` times; some specs may require manual authoring of complex algorithms.
- **Invariants do not cover the full API surface.** A verified package passes all specified invariants, but unspecified behaviors may differ from the original.
- **The clean-room implementation is not a drop-in replacement.** It is a provenance artifact demonstrating that a correct implementation can be written from public specifications alone.
- **The system does not generate legal opinions.** Provenance attestations document the engineering process; consult legal counsel for IP determinations.
- **Native C libraries (`ctypes`) cannot be clean-room reimplemented in Python** by this system (out of scope for Layer 3 synthesis).
