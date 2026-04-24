# Theseus — User Guide

## Table of Contents

1. [What Theseus Is](#1-what-theseus-is)
2. [Installation and Setup](#2-installation-and-setup)
3. [Quick Start](#3-quick-start)
4. [Establishing Provenance](#4-establishing-provenance)
5. [Searching for Packages](#5-searching-for-packages)
6. [Comparing Packages](#6-comparing-packages)
7. [Building in a Clean Room](#7-building-in-a-clean-room)
8. [Recreating a Package from Its Specification](#8-recreating-a-package-from-its-specification)
9. [Writing Your Own Specifications](#9-writing-your-own-specifications)
10. [Reference: All Commands](#10-reference-all-commands)

---

## 1. What Theseus Is

Theseus is a toolchain for documenting, verifying, and re-creating open source software behavior without using the original implementation source code.

It answers four questions:

1. **Where does this library's behavior come from?** — Provenance: which RFCs, public docs, and header files were consulted to describe it.
2. **Is my specification accurate?** — Verification: run the spec's invariants against the real installed library.
3. **How does library A differ from library B?** — Comparison: compare two specs to find common behavior and divergences.
4. **Can I build a correct implementation from the spec alone?** — Synthesis: LLM-generate an implementation that satisfies every invariant, with the original package blocked during testing.

The system requires **Python 3.9+** and has **no external runtime dependencies** (pure stdlib). LLM synthesis requires either the `claude` CLI or an OpenAI-compatible endpoint configured in `config.yaml`.

---

## 2. Installation and Setup

### 2.1 Prerequisites

```bash
python3 --version   # must be 3.9 or later
```

No `pip install` is needed. Theseus uses Python stdlib only.

To verify specs against libraries that are not installed on your host, Docker is required:

```bash
docker --version    # any recent Docker Engine or Docker Desktop
```

Build the verification sandbox image once after cloning:

```bash
make docker-build
```

This creates a local `theseus-verify:latest` image (Ubuntu 26.04 with Python, Node.js, Rust, and common C dev libraries). The image is reused for all subsequent `make verify-behavior-docker` calls.

### 2.2 Verify the installation

```bash
make
```

Expected output:
```
Theseus is ready. No runtime dependencies to install (stdlib only).
Run 'make test' to verify. Run 'make start' for a quick demo on examples/.
```

### 2.3 Run the test suite

```bash
make test
```

This compiles all specs and runs the pytest suite. All tests should pass before doing any other work.

### 2.4 Configure LLM access (for synthesis only)

Synthesis (Sections 7 and 8) requires an LLM. Three categories of provider are supported:

**CLI coding agents (easiest if you already have one installed):**

| Agent | Install | `provider` value |
|-------|---------|-----------------|
| Claude CLI | https://claude.ai/code | `claude` (or `auto`) |
| OpenAI Codex CLI | https://github.com/openai/codex | `codex` (or `auto`) |
| Droid or other | any CLI that reads stdin, prints to stdout | `cli_agent` |

With `provider: auto` Theseus tries `claude`, then `codex`, then `droid` in PATH order, then falls back to an OpenAI endpoint.

**OpenAI-compatible HTTP endpoint (most flexible):**

```yaml
ai:
  provider: openai
  openai_base_url: "http://localhost:11434/v1"   # Ollama
  openai_model: "llama3.2"
```

Works with Ollama, LM Studio, OpenRouter, the real OpenAI API, or any other server that speaks the `/v1/chat/completions` protocol.

**Generic CLI agent:**

```yaml
ai:
  provider: cli_agent
  cli_agent_command: "droid"   # or any other command name
  cli_agent_args: ["-"]        # args passed to the command; "-" = read stdin
```

The command must accept the prompt on stdin and print the response to stdout.

Verification, search, comparison, and provenance reports do **not** require LLM access.

---

## 3. Quick Start

Run the demo to see what ecosystem analysis looks like:

```bash
make start
```

This produces two reports in `reports/`:
- `reports/demo-overlap/` — overlap between Nixpkgs and FreeBSD Ports
- `reports/demo-candidates.json` — ranked list of synthesis candidates

To see all available commands:

```bash
make help
```

---

## 4. Establishing Provenance

Provenance is the documented audit trail of what sources were consulted when writing a behavioral specification. Theseus makes this machine-readable and independently verifiable.

### 4.1 Understanding the provenance block

Every `.zspec.zsdl` file has a `provenance:` block. Here is the one from `zspecs/zlib.zspec.zsdl`:

```yaml
provenance:
  derived_from:
    - "RFC 1950 — ZLIB Compressed Data Format Specification (May 1996)"
    - "RFC 1951 — DEFLATE Compressed Data Format Specification (May 1996)"
    - "https://zlib.net/manual.html — zlib API manual (public documentation)"
    - "https://zlib.net/zlib.h — public header file (API declarations only)"
  not_derived_from:
    - "zlib/deflate.c"
    - "zlib/inflate.c"
    - "Any other zlib C implementation source file"
  notes: "This spec constitutes the clean-room boundary. The implementation
          team reads this spec only."
  created_at: "2026-03-30T00:00:00Z"
```

The `derived_from` list documents what you read. The `not_derived_from` list documents what you explicitly did not read — this is the clean-room boundary.

### 4.2 Generate a provenance report

```bash
make provenance-report SPEC=zspecs/zlib.zspec.zsdl
```

This produces a Markdown attestation that includes:
- What sources the spec was derived from
- What sources it was explicitly not derived from
- Whether a clean-room implementation has been verified in isolation
- The full list of behavioral invariants (the testable boundary)

Save the report to a file:

```bash
make provenance-report SPEC=zspecs/zlib.zspec.zsdl PROV_OUT=reports/zlib-provenance.md
```

Get JSON output (for programmatic use):

```bash
make provenance-report SPEC=zspecs/zlib.zspec.zsdl JSON=1
```

### 4.3 Validate the provenance claims

The behavioral invariants in a provenance report are independently verifiable. To re-run them against the real library:

```bash
make compile-zsdl ZSDL=zspecs/zlib.zspec.zsdl
make verify-behavior ZSPEC=_build/zspecs/zlib.zspec.json VERBOSE=1
```

**If the library is not installed on your system,** use the Docker sandbox instead. It starts a disposable Ubuntu 26.04 container, installs the package inside the container, runs verification, and removes the container — nothing is installed on the host:

```bash
# Build the sandbox image once (reused for all subsequent verifications):
make docker-build

# Python package from PyPI:
make verify-behavior-docker ZSDL=zspecs/requests.zspec.zsdl PIP=requests

# Specific version:
make verify-behavior-docker ZSDL=zspecs/pydantic.zspec.zsdl PIP="pydantic>=2"

# Native C library (ctypes backend):
make verify-behavior-docker ZSDL=zspecs/zlib.zspec.zsdl APT=zlib1g-dev

# Node.js package (node backend):
make verify-behavior-docker ZSDL=zspecs/chalk.zspec.zsdl NPM=chalk

# Rust crate (rust_module backend):
make verify-behavior-docker ZSDL=zspecs/serde_json_rust.zspec.zsdl CARGO=serde_json

# stdlib / cleanroom specs (no install needed):
make verify-behavior-docker ZSDL=zspecs/json.zspec.zsdl

# Keep container after run to inspect what happened:
make verify-behavior-docker ZSDL=zspecs/json.zspec.zsdl KEEP=1
```

The container is removed after each run. The repo is mounted read-write inside the container at `/theseus`, so the same compiled spec and verification harness are used as in a direct `make verify-behavior` call. This approach covers all backend types: Python, ctypes, Node.js, Rust, and CLI.

Every PASS means the library's actual behavior matches what the spec says. Every invariant that passes is a concrete, machine-checked datum that anchors the provenance claim.

To verify across all specs at once:

```bash
make verify-all-specs
```

Output example (only specs whose libraries are installed on your system will fully pass):
```
--- _build/zspecs/hashlib.zspec.json ---
PASS
--- _build/zspecs/json.zspec.json ---
PASS
...
=== verify-all-specs: 1228 specs, N passed, M failed ===
```

Note: many specs cover third-party libraries that may not be installed. Run `make verify-behavior ZSPEC=_build/zspecs/<name>.zspec.json` to verify individual specs whose libraries you have installed.

### 4.4 Verifying isolation of a clean-room implementation

For packages with `status: verified` in the registry, isolation has already been confirmed. To re-verify manually:

```bash
# Verify that theseus_json works without the json module available
THESEUS_BLOCKED_PACKAGE=json PYTHONPATH=cleanroom/python python3 -c "
import theseus_json
result = theseus_json.json_loads_int()
print('loads_int:', result)
"
```

If this succeeds (no ImportError), the implementation is genuinely independent of the original.

Check registry status for any package:

```bash
python3 tools/registry.py check theseus_json
```

Output:
```
theseus_json: verified
```
Exit code is `0` for verified, `1` for not verified (suitable for use in CI).

List all verified packages:

```bash
python3 tools/registry.py list
```

---

## 5. Searching for Packages

### 5.1 Search by name or keyword

Find all specs related to JSON:

```bash
make search QUERY=json
```

Output:
```
V  backend                inv      spec name
--------------------------------------------
   python_module           22 inv  json
   python_module           17 inv  json_decoder
   python_module           10 inv  json_encoder
✓  python_cleanroom         3 inv  theseus_json
✓  python_cleanroom         3 inv  theseus_json_cr
...
18 spec(s) found.  ✓ = verified clean-room implementation in registry.
```

The `✓` column shows which packages have a verified clean-room implementation.

### 5.2 Filter by backend type

Find all clean-room specs (synthesis targets):

```bash
make search BACKEND=python_cleanroom
```

Find all ctypes specs (native C library wrappers):

```bash
make search BACKEND=ctypes
```

Find all Python module specs:

```bash
make search BACKEND=python_module
```

### 5.3 Show only verified packages

```bash
make search VERIFIED=1
```

This is equivalent to asking: "which packages have a clean-room implementation that has been isolated-verified?"

### 5.4 List all specs

```bash
make search LIST=1
```

### 5.5 Machine-readable output

```bash
make search QUERY=hashlib JSON=1
```

Returns a JSON array where each element has:
```json
{
  "file": "zspecs/hashlib.zspec.zsdl",
  "name": "hashlib",
  "backend": "python_module",
  "docs": "https://docs.python.org/3/library/hashlib.html",
  "invariant_count": 47,
  "verified": false
}
```

### 5.6 Search the registry directly

```bash
python3 tools/registry.py list
```

Shows all registered packages with their status:
```
  [verified ] theseus_abc_cr  →  cleanroom/python/theseus_abc_cr
  [verified ] theseus_json    →  cleanroom/python/theseus_json
  [pending  ] theseus_foo     →  cleanroom/python/theseus_foo
  ...
```

---

## 6. Comparing Packages

Comparison answers: "How do two libraries differ in their specified behavior?"

### 6.1 Compile the specs first

Comparison works on compiled specs. Always compile first:

```bash
make compile-zsdl
```

Or compile just the two you need:

```bash
make compile-zsdl ZSDL=zspecs/json.zspec.zsdl
make compile-zsdl ZSDL=zspecs/theseus_json.zspec.zsdl
```

### 6.2 Compare two specs

```bash
make compare SPEC1=_build/zspecs/json.zspec.json SPEC2=_build/zspecs/theseus_json.zspec.json
```

Output:
```
Comparing specs:
  A: json  (backend: python_module, 22 invariants)
  B: theseus_json  (backend: python_cleanroom, 3 invariants)

Summary:
  Common invariants        : 0
  Only in A                : 22
  Only in B                : 3
  Behavioral differences   : 0

Only in 'json':
  json.dumps.null  →  'null'  [python_call_eq]
  json.dumps.true  →  'true'  [python_call_eq]
  json.loads.object  →  "{'a': 1}"  [python_call_eq]
  ...

Only in 'theseus_json':
  theseus_json.round_trip  →  'True'  [python_call_eq]
  ...
```

### 6.3 You can also pass .zsdl paths directly

```bash
make compare SPEC1=zspecs/hashlib.zspec.zsdl SPEC2=zspecs/_hashlib.zspec.zsdl
```

Theseus resolves `.zsdl` paths to their compiled `.zspec.json` equivalents automatically (requires prior `make compile-zsdl`).

### 6.4 Compare an original library spec to its clean-room version

This is the most common comparison use case — confirming that the clean-room spec covers the same behaviors:

```bash
make compare \
  SPEC1=_build/zspecs/hashlib.zspec.json \
  SPEC2=_build/zspecs/theseus_hashlib_cr.zspec.json
```

Behavioral differences indicate places where the clean-room spec was written to different values than what the real library returns. These must be investigated — they either represent bugs in the clean-room spec or intentional API differences.

### 6.5 Compare two third-party alternatives

```bash
make compile-zsdl ZSDL=zspecs/json_rust.zspec.zsdl
make compile-zsdl ZSDL=zspecs/orjson_rust.zspec.zsdl
make compare \
  SPEC1=_build/zspecs/json_rust.zspec.json \
  SPEC2=_build/zspecs/orjson_rust.zspec.json
```

### 6.6 Machine-readable output

```bash
make compare \
  SPEC1=_build/zspecs/json.zspec.json \
  SPEC2=_build/zspecs/theseus_json.zspec.json \
  JSON=1
```

Returns a JSON object with `summary`, `common_invariants`, `only_in_a`, `only_in_b`, and `behavioral_differences`.

---

## 7. Building in a Clean Room

Clean-room building means: write an implementation that satisfies a behavioral spec without reading the original source code.

### 7.1 Prerequisites

- A `.zspec.zsdl` file with `backend: python_cleanroom(<impl-name>)`
- LLM access configured in `config.yaml` (see Section 2.4)
- The original library installed (to verify the spec before synthesis)

### 7.2 Find an existing clean-room spec

```bash
make search BACKEND=python_cleanroom
```

Pick one that is not yet verified (no `✓`), or start from one that is verified to understand the pattern.

Look at a simple example — `zspecs/theseus_json.zspec.zsdl`:

```bash
cat zspecs/theseus_json.zspec.zsdl
```

```yaml
spec: theseus_json
version: ">=3.9"
backend: python_cleanroom(theseus_json)

docs: https://www.json.org/json-en.html

provenance:
  derived_from:
    - "https://www.json.org/json-en.html — JSON.org specification"
    - "RFC 8259 — The JavaScript Object Notation (JSON) Data Interchange Format"
  not_derived_from:
    - "CPython source: Lib/json/__init__.py"
    - "CPython source: Lib/json/decoder.py"
    - "CPython source: Lib/json/encoder.py"

invariants:
  - id: theseus_json.loads_int
    kind: python_call_eq
    describe: "json_loads_int() returns 1"
    spec:
      function: json_loads_int
      args: []
      expected: 1

  - id: theseus_json.dumps_has_key
    kind: python_call_eq
    describe: "json_dumps_has_key() returns True"
    spec:
      function: json_dumps_has_key
      args: []
      expected: True

  - id: theseus_json.round_trip
    kind: python_call_eq
    describe: "json_round_trip() returns True"
    spec:
      function: json_round_trip
      args: []
      expected: True
```

Note that the invariant functions are **zero-argument wrappers** that return a hardcoded expected value. This is the required pattern for clean-room synthesis — see Section 9 for details.

### 7.3 Run the full pipeline

```bash
make pipeline SYNTH_ZSDL=zspecs/theseus_json.zspec.zsdl
```

The pipeline does five things:
1. Compiles the spec to `_build/zspecs/theseus_json.zspec.json`
2. Verifies the spec against the real `json` module (sanity check)
3. Asks the LLM to write an implementation satisfying all invariants
4. Runs `cleanroom_verify.py` with `THESEUS_BLOCKED_PACKAGE=json` — the real `json` module is blocked
5. If all invariants pass in isolation: registers the package in `theseus_registry.json`

On success:
```
✓ theseus_json: verified (3/3 invariants pass in isolation)
Registered: theseus_json (verified)
```

On failure (LLM produced code that imports json):
```
ISOLATION VIOLATION: theseus_json — attempt 1/3
Retrying ...
```

The pipeline retries up to `SYNTH_MAX_ITER` times (default: 3). Increase for harder specs:

```bash
make pipeline SYNTH_ZSDL=zspecs/theseus_re_cr5.zspec.zsdl SYNTH_MAX_ITER=10
```

### 7.4 Run synthesis waves (for batch processing)

The wave system processes groups of related specs in order. List available waves:

```bash
make synthesize-waves-list
```

Check which waves are complete:

```bash
make synthesize-waves-status
```

Run the next pending wave:

```bash
make synthesize-waves-next
```

This command is **resumable**: if interrupted, it picks up where it left off (wave state is saved in `reports/synthesis/wave_state.json`).

### 7.5 Inspect the result

Once synthesis succeeds, inspect the generated implementation:

```bash
cat cleanroom/python/theseus_json/__init__.py
```

Confirm registration:

```bash
python3 tools/registry.py check theseus_json
```

Re-run isolation verification manually:

```bash
python3 tools/cleanroom_verify.py theseus_json
```

### 7.6 Lint the clean-room code

```bash
make lint-cleanroom
```

This checks that:
- No implementation imports the package it is replacing
- No implementation uses cross-language wrappers (e.g., calling `subprocess` to invoke the original binary)
- No new `rust_module` backend specs have been introduced

---

## 8. Recreating a Package from Its Specification

This section walks through the complete workflow: starting from a behavioral spec for an existing library, and ending with a new implementation that can be verified to be behaviorally equivalent — without ever touching the original source code.

The example uses `hashlib` (Python's cryptographic hash library).

### 8.1 Find the spec

```bash
make search QUERY=hashlib
```

Output includes:
```
   python_module           47 inv  hashlib
   python_module            4 inv  _hashlib
✓  python_cleanroom         3 inv  theseus_hashlib_cr
```

`hashlib.zspec.zsdl` — the behavioral spec for the real `hashlib` module.  
`theseus_hashlib_cr.zspec.zsdl` — the clean-room synthesis spec.

### 8.2 Review the behavioral contract

```bash
make provenance-report SPEC=zspecs/hashlib.zspec.zsdl
```

This tells you:
- The spec was derived from public Python documentation and RFC 1321 (MD5) etc.
- It was NOT derived from CPython's `Lib/hashlib.py` or `Modules/_hashopenssl.c`
- There are 41 invariants covering SHA-256, SHA-512, MD5, SHA-1, and their properties

To see the invariants without running them:

```bash
make compile-zsdl ZSDL=zspecs/hashlib.zspec.zsdl
python3 tools/verify_behavior.py _build/zspecs/hashlib.zspec.json --list
```

Output:
```
hashlib.sha256.empty        [known_vector]  hash_known_vector: hashlib.sha256.empty
hashlib.sha256.abc          [known_vector]  hash_known_vector: hashlib.sha256.abc
hashlib.sha256.fips_message2 [known_vector]  hash_known_vector: hashlib.sha256.fips_message2
hashlib.sha1.empty          [known_vector]  hash_known_vector: hashlib.sha1.empty
hashlib.md5.empty           [known_vector]  hash_known_vector: hashlib.md5.empty
hashlib.md5.abc             [known_vector]  hash_known_vector: hashlib.md5.abc
...
```

### 8.3 Validate the spec against the real library

```bash
make verify-behavior ZSPEC=_build/zspecs/hashlib.zspec.json VERBOSE=1
```

Expected output (all 47 invariants should pass):
```
PASS hashlib.sha256.known_vector.abc
PASS hashlib.sha256.known_vector.empty
PASS hashlib.sha256.incremental.chunks_equal_oneshot
...
PASS (47/47)
```

This confirms the spec is accurate. Every PASS is an independently verifiable fact.

### 8.4 Review the clean-room synthesis spec

```bash
cat zspecs/theseus_hashlib_cr.zspec.zsdl
```

The clean-room spec has `backend: python_cleanroom(theseus_hashlib_cr)` and invariants that are zero-argument wrappers with hardcoded expected values:

```yaml
- id: theseus_hashlib_cr.sha256_empty
  kind: python_call_eq
  describe: "sha256_empty_hex() returns known SHA-256 of empty string"
  spec:
    function: sha256_empty_hex
    args: []
    expected: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
```

These values were taken from the authoritative spec (RFC 6234, FIPS 180-4) — not from reading the CPython implementation.

### 8.5 Synthesize the clean-room implementation

```bash
make pipeline SYNTH_ZSDL=zspecs/theseus_hashlib_cr.zspec.zsdl
```

The pipeline synthesizes `cleanroom/python/theseus_hashlib_cr/__init__.py` — a complete SHA-256/MD5 implementation derived only from the mathematical specification and the test vectors in the ZSDL file.

### 8.6 Prove the implementation is independent

The pipeline already verified isolation. To re-run the proof:

```bash
python3 tools/cleanroom_verify.py theseus_hashlib_cr
```

This runs all invariants with `THESEUS_BLOCKED_PACKAGE=hashlib` set. If any invariant fails, either:
- The implementation secretly imports `hashlib` (caught immediately by the blocker), or
- The implementation has a bug in its algorithm

Either way, the failure is definitive.

### 8.7 Compare the original and clean-room specs

```bash
make compare \
  SPEC1=_build/zspecs/hashlib.zspec.json \
  SPEC2=_build/zspecs/theseus_hashlib_cr.zspec.json
```

The comparison shows the behavioral overlap. A correct clean-room implementation should produce identical results for every invariant in the original spec that it also covers.

### 8.8 Generate the final provenance attestation

```bash
make provenance-report SPEC=zspecs/theseus_hashlib_cr.zspec.zsdl \
  PROV_OUT=reports/theseus_hashlib_cr-provenance.md
```

The resulting Markdown document:
1. Lists what the spec was derived from (RFCs, public docs — no source code)
2. Lists what it was not derived from (CPython implementation files)
3. Confirms `status: verified` in the registry
4. Lists all invariants (the testable clean-room boundary)

This document can be given to auditors or included in a legal clean-room certification package. Every claim in it can be independently re-verified by running `make verify-behavior`.

---

## 9. Writing Your Own Specifications

### 9.1 Create a behavioral spec for an existing library

Create `zspecs/mylib.zspec.zsdl`:

```yaml
spec: mylib
version: ">=1.0"
backend: python_module(mylib)

docs: https://mylib.readthedocs.io/

provenance:
  derived_from:
    - "https://mylib.readthedocs.io/ — official documentation"
  not_derived_from:
    - "mylib/core.py"
    - "mylib/utils.py"
  created_at: "2026-04-24T00:00:00Z"

invariants:
  - id: mylib.add.basic
    kind: python_call_eq
    describe: "add(1, 2) returns 3"
    spec:
      function: add
      args: [1, 2]
      expected: 3

  - id: mylib.greet.default
    kind: python_call_eq
    describe: "greet() returns 'hello'"
    spec:
      function: greet
      args: []
      expected: "hello"
```

Compile and verify:

```bash
make compile-zsdl ZSDL=zspecs/mylib.zspec.zsdl
make verify-behavior ZSPEC=_build/zspecs/mylib.zspec.json VERBOSE=1
```

### 9.2 Create a clean-room synthesis spec

Create `zspecs/theseus_mylib.zspec.zsdl`:

```yaml
spec: theseus_mylib
version: ">=1.0"
backend: python_cleanroom(theseus_mylib)

docs: https://mylib.readthedocs.io/

provenance:
  derived_from:
    - "https://mylib.readthedocs.io/ — official documentation"
  not_derived_from:
    - "mylib/core.py"
    - "mylib/utils.py"
  notes: >
    Do NOT import mylib. Implement add(a, b) as a+b.
    Implement greet() as a function returning the string literal 'hello'.
    Export: add, greet.

invariants:
  - id: theseus_mylib.add_basic
    kind: python_call_eq
    describe: "add_basic() returns 3"
    spec:
      function: add_basic
      args: []
      expected: 3

  - id: theseus_mylib.greet_default
    kind: python_call_eq
    describe: "greet_default() returns hello"
    spec:
      function: greet_default
      args: []
      expected: "hello"
```

**Critical rule:** Clean-room invariant functions must be **zero-argument wrappers** that call the real function internally and return a hardcoded expected value. The LLM synthesizes the zero-argument wrapper; the expected value comes from your knowledge of the spec (not from running the original library).

### 9.3 Synthesize the implementation

```bash
make pipeline SYNTH_ZSDL=zspecs/theseus_mylib.zspec.zsdl
```

### 9.4 Common mistakes to avoid

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Invariant function takes arguments | Synthesis fails silently | Use zero-argument wrappers only |
| Expected value copied from running the original library | Spec is accurate but not independent | Derive expected values from public docs/RFCs |
| `provenance.notes` omits "Do NOT import X" | LLM imports the original | Always tell the LLM explicitly what NOT to import |
| Wrong expected value | Pipeline fails at isolation verify | Re-check the spec's math or documentation |

For full authoring rules, see `docs/cleanroom-spec-format.md`.

---

## 10. Reference: All Commands

### Core

| Command | Description |
|---------|-------------|
| `make` | Check Python version, print usage |
| `make test` | Run test suite (compile all specs + pytest) |
| `make start` | Run demo analysis on `examples/` |
| `make clean` | Remove `_build/`, test caches |
| `make help` | Print all available targets |

### Discovery

| Command | Description |
|---------|-------------|
| `make search QUERY=<term>` | Search specs by name or keyword |
| `make search BACKEND=<type>` | Filter by backend (`python_cleanroom`, `ctypes`, etc.) |
| `make search VERIFIED=1` | Only verified clean-room packages |
| `make search LIST=1` | List all specs |
| `make search QUERY=<term> JSON=1` | Machine-readable output |
| `python3 tools/registry.py list` | All registered packages with status |
| `python3 tools/registry.py check <name>` | Exit 0 if verified, 1 if not |

### Provenance

| Command | Description |
|---------|-------------|
| `make provenance-report SPEC=<path>` | Generate Markdown attestation |
| `make provenance-report SPEC=<path> JSON=1` | JSON attestation |
| `make provenance-report SPEC=<path> PROV_OUT=<file>` | Write to file |
| `make compile-zsdl ZSDL=<path>` | Compile one spec |
| `make compile-zsdl` | Compile all specs |
| `make verify-behavior ZSPEC=<path>` | Verify spec against real library (must be installed on host) |
| `make verify-behavior ZSPEC=<path> VERBOSE=1` | Per-invariant results |
| `make verify-behavior ZSPEC=<path> FILTER=<substring>` | Run matching invariants only |
| `make docker-build` | Build the Ubuntu 26.04 verification sandbox image (one-time) |
| `make verify-behavior-docker ZSDL=<path>` | Verify in disposable Docker container |
| `make verify-behavior-docker ZSDL=<path> PIP=<pkg>` | Install Python package via pip before verify |
| `make verify-behavior-docker ZSDL=<path> APT=<pkg>` | Install Debian package via apt before verify |
| `make verify-behavior-docker ZSDL=<path> NPM=<pkg>` | Install Node.js package via npm before verify |
| `make verify-behavior-docker ZSDL=<path> CARGO=<crate>` | Install Rust crate via cargo before verify |
| `make verify-behavior-docker ZSDL=<path> KEEP=1` | Keep container after run for inspection |
| `make verify-all-specs` | Run all specs, aggregate pass/fail |

### Comparison

| Command | Description |
|---------|-------------|
| `make compare SPEC1=<path> SPEC2=<path>` | Compare two specs |
| `make compare SPEC1=<path> SPEC2=<path> JSON=1` | Machine-readable comparison |

### Synthesis

| Command | Description |
|---------|-------------|
| `make pipeline SYNTH_ZSDL=<path>` | Full pipeline: compile→verify→synthesize→register |
| `make pipeline SYNTH_ZSDL=<path> SYNTH_MAX_ITER=10` | Allow more synthesis attempts |
| `make pipeline SYNTH_ZSDL=<path> VERBOSE=1` | Verbose synthesis output |
| `make synthesize-waves-list` | List all synthesis waves and status |
| `make synthesize-waves-status` | Per-spec synthesis progress |
| `make synthesize-waves-next` | Run next pending wave (resumable) |
| `make synthesize-waves SYNTH_WAVE=<wave>` | Run a specific wave |
| `make lint-cleanroom` | Check all clean-room specs for wrapper patterns |

### Package Registry

| Command | Description |
|---------|-------------|
| `python3 tools/registry.py list` | All packages |
| `python3 tools/registry.py check <name>` | Is package verified? |
| `python3 tools/registry.py register <name> <path> <spec>` | Register a package |
| `python3 tools/registry.py verify <name>` | Mark as verified |

### Ecosystem Analysis (Layer 1)

| Command | Description |
|---------|-------------|
| `make report SNAPSHOT=<dir>` | Overlap report (Nixpkgs vs FreeBSD) |
| `make candidates SNAPSHOT=<dir>` | Rank packages by synthesis suitability |
| `make extract SNAPSHOT=<dir>` | Merge top-N candidates |
| `make diff BEFORE=<dir> AFTER=<dir>` | Diff two snapshots |
| `make import-pypi PYPI_SEED=<file>` | Fetch PyPI metadata |
| `make import-npm NPM_SEED=<file>` | Fetch npm metadata |
| `make import-cargo CARGO_SEED=<file>` | Fetch Cargo crate metadata |

---

## Appendix: How Verification Works

When you run `make verify-behavior ZSPEC=_build/zspecs/hashlib.zspec.json`, the harness (`tools/verify_behavior.py`) does the following:

1. Reads the compiled spec and determines the backend type (`python_module`, `ctypes`, etc.)
2. Loads the library using that backend (e.g., `import hashlib` for python_module)
3. For each invariant, calls the specified function with the specified arguments
4. Compares the result to the `expected` value
5. Prints PASS or FAIL per invariant, with a summary count

For `python_cleanroom` specs during synthesis, `cleanroom_verify.py` does the same, but with the original package blocked via `THESEUS_BLOCKED_PACKAGE`. If an implementation passes all invariants in isolation, it is registered as verified.

## Appendix: The Isolation Mechanism

`cleanroom/python/sitecustomize.py` is automatically executed by Python at startup when `PYTHONPATH` includes `cleanroom/python/`. It installs a custom import hook that checks every `import` statement. If the imported module name matches `THESEUS_BLOCKED_PACKAGE`, the hook raises:

```
ImportError: THESEUS ISOLATION VIOLATION: attempted to import 'hashlib'
             from a Theseus clean-room package. Use a Theseus-verified
             alternative instead.
```

This makes isolation violations loud and immediate — there is no way for a clean-room implementation to silently depend on the original library.

To test this yourself:

```bash
THESEUS_BLOCKED_PACKAGE=json PYTHONPATH=cleanroom/python python3 -c "import json"
```

Expected:
```
ImportError: THESEUS ISOLATION VIOLATION: attempted to import 'json' ...
```
