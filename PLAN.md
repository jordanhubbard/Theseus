# Theseus Clean-Room Rewrite Initiative — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Theseus from a behavioral spec verification system (which wraps existing packages) into a clean-room package synthesis engine that produces fully self-contained, dependency-clean reimplementations of OSS packages — no cross-language wrappers, no runtime dependencies on the original package.

**Architecture:** Each target package gets a ZSDL behavioral spec expressing what it must do (invariants, input/output contracts), then a clean-room implementation written entirely in the target language (Python for Python packages, Node.js for Node.js packages, etc.) that satisfies all invariants without importing the original library. Only other Theseus-rewritten packages may be used as dependencies.

**Tech Stack:** Python 3.9+, ZSDL spec language, existing synthesize_waves.py pipeline, pytest for verification, Node.js for JS targets.

---

## Foundational Principles

These are non-negotiable constraints for every task in this plan:

1. **No cross-language boundaries.** A Python package is reimplemented in Python. A Node.js package in Node.js. Never call into another runtime.
2. **No wrapping the original.** The reimplementation must not `import` the original library at any point — not in tests, not in the implementation, not via subprocess.
3. **No external OSS dependencies** except other Theseus-rewritten packages (tracked in `theseus_registry.json`).
4. **Spec-first.** The behavioral spec (ZSDL) is written and reviewed before any implementation begins.
5. **Invariant-complete.** A package is not "done" until all spec invariants pass against the clean-room implementation — not the original.

---

## Phase 0: Audit and Remediation

### Task 0.1: Audit existing Rust specs for wrapper pattern

**Files:**
- Read: `reports/synthesis/wave_state.json`
- Read: `zspecs/*_rust.zspec.zsdl` (sample)
- Create: `reports/audit/wrapper_audit.md`

- [ ] **Step 1: Identify all Rust specs that are wrappers**

Run:
```bash
python3 - <<'EOF'
import json, glob, re

wrapper_specs = []
for path in glob.glob("zspecs/*_rust.zspec.zsdl"):
    text = open(path).read()
    if re.search(r'(Expose|wrapper|calls?|delegates?)', text, re.IGNORECASE):
        wrapper_specs.append(path)

print(f"Potential wrapper specs: {len(wrapper_specs)}")
for s in sorted(wrapper_specs)[:20]:
    print(f"  {s}")
EOF
```

- [ ] **Step 2: Categorize by remediation path**

For each spec, classify as:
- `clean_rewrite_needed` — has a real implementation to do (math, string ops, data structures)
- `stdlib_only` — wraps Python stdlib; descope or rewrite as a Theseus stdlib subset
- `infeasible` — requires OS resources that cannot be clean-room replicated

Write `reports/audit/wrapper_audit.md` with the categorized list.

- [ ] **Step 3: Commit audit**

```bash
git add reports/audit/wrapper_audit.md
git commit -m "audit: categorize existing Rust specs by wrapper pattern"
```

---

## Phase 1: New Spec Format — Clean-Room Backends

### Task 1.1: Define the `python_cleanroom` and `node_cleanroom` backends

**Files:**
- Create: `docs/cleanroom-spec-format.md`

New ZSDL backend declarations:
```
backend: python_cleanroom(package_name)   # pure Python rewrite
backend: node_cleanroom(package_name)     # pure JS rewrite
```

Rules:
- Python implementations live at `cleanroom/python/<name>/__init__.py`
- Node.js implementations live at `cleanroom/node/<name>/index.js`
- The test runner adds only `cleanroom/<lang>/` to the module path; site-packages are excluded
- If the original package is importable, the test FAILS immediately (isolation violation)

- [ ] **Step 1: Write `docs/cleanroom-spec-format.md` with annotated example spec**

```yaml
spec: theseus_json
version: ">=3.9"
backend: python_cleanroom(theseus_json)

# No 'import json' allowed anywhere in the implementation.
# Standard library string/bytes ops only.

invariant theseus_json.loads_basic:
  description: "loads('{\"a\": 1}')[\"a\"] == 1"
  kind: python_call_eq
  function: json_loads_key
  args: ['{"a": 1}', "a"]
  expected: 1

invariant theseus_json.round_trip:
  description: "loads(dumps(obj)) == obj"
  kind: python_call_eq
  function: json_round_trip
  args: [{"x": [1, 2, 3]}]
  expected: true
```

- [ ] **Step 2: Commit**

```bash
git add docs/cleanroom-spec-format.md
git commit -m "docs: define clean-room backend spec format"
```

---

### Task 1.2: Update ZSDL compiler to support cleanroom backends

**Files:**
- Modify: `tools/zsdl_compile.py`
- Modify: `tools/synthesize_waves.py`
- Create: `tests/test_cleanroom_backend.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cleanroom_backend.py
import subprocess, json, os

def test_python_cleanroom_backend_compiles(tmp_path):
    spec = tmp_path / "sample.zspec.zsdl"
    spec.write_text("""
spec: sample_cr
version: ">=3.9"
backend: python_cleanroom(sample_cr)

invariant sample_cr.always_true:
  description: "always true"
  kind: python_call_eq
  function: always_true
  args: []
  expected: true
""")
    result = subprocess.run(
        ["python3", "tools/zsdl_compile.py", str(spec)],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    assert result.returncode == 0
    out = json.load(open(f"_build/zspecs/sample_cr.zspec.json"))
    assert out["backend_lang"] == "python_cleanroom"
    assert out["cleanroom_path"] == "cleanroom/python/sample_cr"
```

- [ ] **Step 2: Run, verify it fails**

```bash
pytest tests/test_cleanroom_backend.py -v
# Expected: FAIL — backend_lang not recognized
```

- [ ] **Step 3: Implement in `zsdl_compile.py`**

Add parsing for `backend: python_cleanroom(name)` and `backend: node_cleanroom(name)`. Set:
```python
compiled["backend_lang"] = "python_cleanroom"  # or node_cleanroom
compiled["cleanroom_path"] = f"cleanroom/python/{name}"
```

- [ ] **Step 4: Run, verify it passes**

```bash
pytest tests/test_cleanroom_backend.py -v
# Expected: PASS
```

- [ ] **Step 5: Add wave discovery in `synthesize_waves.py`**

Wave `cr1` selects specs where `backend_lang in ("python_cleanroom", "node_cleanroom")`.

- [ ] **Step 6: Commit**

```bash
git add tools/zsdl_compile.py tools/synthesize_waves.py tests/test_cleanroom_backend.py
git commit -m "feat: python_cleanroom and node_cleanroom backend support in compiler"
```

---

## Phase 2: Isolation Harness

### Task 2.1: Build the clean-room isolation verifier

**Files:**
- Create: `tools/cleanroom_verify.py`
- Create: `cleanroom/python/sitecustomize.py`
- Create: `tests/test_cleanroom_isolation.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cleanroom_isolation.py
import subprocess, os

def test_blocker_prevents_original_import():
    env = {**os.environ,
           "PYTHONPATH": "cleanroom/python",
           "PYTHONNOUSERSITE": "1",
           "THESEUS_BLOCKED_PACKAGE": "json"}
    result = subprocess.run(
        ["python3", "-c", "import json"],
        capture_output=True, env=env
    )
    assert result.returncode != 0
    assert b"THESEUS ISOLATION VIOLATION" in result.stderr
```

- [ ] **Step 2: Run, verify it fails (json is importable)**

```bash
pytest tests/test_cleanroom_isolation.py -v
```

- [ ] **Step 3: Write `cleanroom/python/sitecustomize.py`**

```python
import sys, os

_blocked = os.environ.get("THESEUS_BLOCKED_PACKAGE", "")

if _blocked:
    class _Blocker:
        def find_module(self, name, path=None):
            if name == _blocked or name.startswith(_blocked + "."):
                raise ImportError(
                    f"THESEUS ISOLATION VIOLATION: attempted to import blocked "
                    f"package '{name}'. Clean-room implementations must not "
                    f"import the original package."
                )
    sys.meta_path.insert(0, _Blocker())
```

- [ ] **Step 4: Run, verify test passes**

```bash
pytest tests/test_cleanroom_isolation.py -v
```

- [ ] **Step 5: Write `tools/cleanroom_verify.py`**

```python
#!/usr/bin/env python3
"""Verify a clean-room implementation satisfies all spec invariants in isolation."""
import sys, json, subprocess, os
from pathlib import Path

def verify(spec_path: str) -> dict:
    spec = json.load(open(spec_path))
    name = spec["spec"]
    lang = spec.get("backend_lang", "")

    if lang == "python_cleanroom":
        return _verify_python(spec, name)
    elif lang == "node_cleanroom":
        return _verify_node(spec, name)
    else:
        return {"error": f"Unknown cleanroom backend: {lang}"}

def _verify_python(spec, name):
    env = {
        **os.environ,
        "PYTHONPATH": str(Path("cleanroom/python").resolve()),
        "PYTHONNOUSERSITE": "1",
        "THESEUS_BLOCKED_PACKAGE": name,
    }
    passed, failed, errors = 0, 0, []
    for inv in spec["invariants"]:
        fn   = inv["function"]
        args = json.dumps(inv["args"])
        exp  = json.dumps(inv["expected"])
        code = (
            f"from {name} import {fn}\n"
            f"import json\n"
            f"result = {fn}(*json.loads('{args}'))\n"
            f"assert result == json.loads('{exp}'), f'got {{result!r}}'\n"
            f"print('OK')\n"
        )
        r = subprocess.run(["python3", "-c", code], capture_output=True, text=True, env=env)
        if r.returncode == 0:
            passed += 1
        else:
            failed += 1
            errors.append({"invariant": inv["id"], "error": r.stderr.strip()})
    return {"pass": passed, "fail": failed, "errors": errors}
```

- [ ] **Step 6: Commit**

```bash
git add tools/cleanroom_verify.py cleanroom/python/sitecustomize.py tests/test_cleanroom_isolation.py
git commit -m "feat: isolation harness for clean-room invariant verification"
```

---

## Phase 3: Clean-Room Synthesis Engine

### Task 3.1: LLM-driven clean-room synthesis

**Files:**
- Create: `tools/synthesize_cleanroom.py`

- [ ] **Step 1: Write `tools/synthesize_cleanroom.py`**

```python
#!/usr/bin/env python3
"""
Clean-room synthesis: given a compiled spec with backend_lang=python_cleanroom,
ask the LLM to produce a complete implementation, then verify with cleanroom_verify.
"""
import json, sys
from pathlib import Path
from tools.cleanroom_verify import verify

SYSTEM_PROMPT = """
You are implementing a Python package from a behavioral specification.

HARD RULES — any violation causes immediate rejection:
1. Do NOT import the package being replaced. If the spec is for `requests`, do NOT `import requests`.
2. Do NOT import any third-party library. Only Python standard library is allowed.
3. Exception: you MAY import other Theseus-verified packages listed in theseus_registry.json.
4. Do NOT use subprocess to call external tools.
5. The implementation must be entirely self-contained.

You will receive the spec invariants. Produce a complete __init__.py that exports the required functions.
"""

def build_prompt(spec: dict) -> str:
    invs = "\n".join(
        f"  - {i['function']}({i.get('args', [])}) == {i['expected']}"
        for i in spec["invariants"]
    )
    return (
        f"Package: {spec['spec']}\n"
        f"Notes: {chr(10).join(spec.get('notes', []))}\n\n"
        f"Invariants:\n{invs}\n\n"
        f"Write cleanroom/python/{spec['spec']}/__init__.py exporting all required functions."
    )

def synthesize(spec_json_path: str, max_iterations: int = 3) -> bool:
    spec = json.load(open(spec_json_path))
    name = spec["spec"]
    out_dir = Path("cleanroom/python") / name
    out_dir.mkdir(parents=True, exist_ok=True)

    for iteration in range(1, max_iterations + 1):
        # Call LLM (same Azure endpoint as synthesize_waves.py)
        impl = _call_llm(SYSTEM_PROMPT, build_prompt(spec))
        (out_dir / "__init__.py").write_text(impl)

        result = verify(spec_json_path)
        if result["fail"] == 0:
            print(f"  {name}: success ({result['pass']}/{result['pass']} invariants)")
            return True
        else:
            print(f"  {name}: iteration {iteration} — {result['fail']} failing")

    print(f"  {name}: FAILED after {max_iterations} iterations")
    return False
```

- [ ] **Step 2: Wire into wave runner**

In `synthesize_waves.py`, when `backend_lang == "python_cleanroom"`, call `synthesize_cleanroom.synthesize(spec_json_path)` instead of the Rust path.

- [ ] **Step 3: Commit**

```bash
git add tools/synthesize_cleanroom.py
git commit -m "feat: LLM-driven clean-room synthesis engine"
```

---

## Phase 4: Theseus Package Registry

### Task 4.1: Create `theseus_registry.json`

**Files:**
- Create: `theseus_registry.json`
- Create: `tools/registry.py`

- [ ] **Step 1: Initialize registry**

```bash
cat > theseus_registry.json << 'EOF'
{
  "version": 1,
  "description": "Registry of Theseus clean-room verified packages. Only packages listed here may be used as dependencies in other Theseus packages.",
  "packages": {}
}
EOF
```

- [ ] **Step 2: Write `tools/registry.py`**

```python
import json
from pathlib import Path

REGISTRY = Path("theseus_registry.json")

def load() -> dict:
    return json.load(open(REGISTRY))

def is_allowed(name: str) -> bool:
    r = load()
    return name in r["packages"] and r["packages"][name]["status"] == "verified"

def register(name: str, cleanroom_path: str, spec: str, status: str = "pending"):
    r = load()
    r["packages"][name] = {
        "cleanroom_path": cleanroom_path,
        "spec": spec,
        "status": status,
    }
    json.dump(r, open(REGISTRY, "w"), indent=2)

def mark_verified(name: str):
    r = load()
    if name not in r["packages"]:
        raise KeyError(f"{name} not in registry")
    r["packages"][name]["status"] = "verified"
    json.dump(r, open(REGISTRY, "w"), indent=2)
```

- [ ] **Step 3: Commit**

```bash
git add theseus_registry.json tools/registry.py
git commit -m "feat: Theseus clean-room package registry"
```

---

## Phase 5: First Clean-Room Packages

### Task 5.1: `theseus_json` — clean-room JSON codec

No `import json`. Pure Python recursive descent parser + serializer.

**Files:**
- Create: `zspecs/theseus_json.zspec.zsdl`
- Create: `cleanroom/python/theseus_json/__init__.py` (synthesized)
- Create: `tests/cleanroom/test_theseus_json.py`

- [ ] **Step 1: Write spec**

```yaml
spec: theseus_json
version: ">=3.9"
backend: python_cleanroom(theseus_json)

provenance:
  notes:
    - "Clean-room JSON codec. No import of json or simplejson allowed."
    - "json_loads(s) parses a JSON string and returns a Python object."
    - "json_dumps(obj) serializes a Python object to a JSON string."

invariant theseus_json.loads_int:
  description: "loads('{\"a\": 1}')[\"a\"] == 1"
  kind: python_call_eq
  function: json_loads_int
  args: []
  expected: 1

invariant theseus_json.dumps_basic:
  description: "dumps({'a': 1}) is valid JSON containing 'a'"
  kind: python_call_eq
  function: json_dumps_has_key
  args: []
  expected: true

invariant theseus_json.round_trip:
  description: "loads(dumps({'x': [1,2,3]}))['x'] == [1,2,3]"
  kind: python_call_eq
  function: json_round_trip
  args: []
  expected: true
```

- [ ] **Step 2: Compile spec**

```bash
python3 tools/zsdl_compile.py zspecs/theseus_json.zspec.zsdl
```

- [ ] **Step 3: Synthesize clean-room implementation**

```bash
python3 tools/synthesize_cleanroom.py _build/zspecs/theseus_json.zspec.json
```

- [ ] **Step 4: Verify in isolation**

```bash
python3 tools/cleanroom_verify.py _build/zspecs/theseus_json.zspec.json
# Expected: 3/3 pass, no isolation violations
```

- [ ] **Step 5: Register and commit**

```bash
python3 -c "from tools.registry import register, mark_verified; register('theseus_json','cleanroom/python/theseus_json','zspecs/theseus_json.zspec.zsdl'); mark_verified('theseus_json')"
git add zspecs/theseus_json.zspec.zsdl cleanroom/python/theseus_json/ theseus_registry.json
git commit -m "feat: theseus_json — clean-room JSON codec, 3/3 invariants"
```

---

### Task 5.2: `theseus_re` — clean-room regex subset

No `import re`. NFA-based regex engine, minimal but correct for the spec invariants.

**Files:**
- Create: `zspecs/theseus_re.zspec.zsdl`
- Create: `cleanroom/python/theseus_re/__init__.py` (synthesized)

Invariants: `match`, `search`, `sub` for basic patterns (`\d+`, `[a-z]+`, `.`).

---

### Task 5.3: `theseus_pathlib` — clean-room path operations

No `import pathlib`, no `import os.path`. Pure string-based path manipulation.

Invariants: `join`, `basename`, `dirname`, `splitext`, `is_absolute`.

---

## Phase 6: Node.js Clean-Room Packages

### Task 6.1: `theseus_path` — clean-room Node.js path module

No `require('path')`. Pure JavaScript string operations.

**Files:**
- Create: `zspecs/theseus_path_node.zspec.zsdl`
- Create: `cleanroom/node/theseus_path/index.js`
- Modify: `tools/synthesize_cleanroom.py` (add Node.js synthesis path)

- [ ] **Step 1: Extend `synthesize_cleanroom.py` for Node.js**

```python
def synthesize_node(spec: dict, max_iterations: int = 3) -> bool:
    name = spec["spec"]
    out_dir = Path("cleanroom/node") / name
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt = (
        f"Package: {name}\n"
        f"Invariants: ...\n\n"
        f"Write cleanroom/node/{name}/index.js. "
        f"No require() of the original package. No npm dependencies. "
        f"Pure JavaScript only."
    )
    # ... LLM call + node verify loop
```

---

## Phase 7: Deprecate All Wrapper Specs

### Task 7.1: Remove `_rust` wrapper specs from active synthesis

Once Phases 1–6 are complete:

- [ ] Mark all `*_rust.zspec.zsdl` specs with `status: deprecated` in `wave_state.json`
- [ ] Update README to reflect the new clean-room mission
- [ ] Add CI check: reject any new spec with `backend: rust_module(...)` that calls back into Python

---

## Guiding Constraints

**Always:**
- Write the spec before any implementation
- Verify isolation before marking a package verified
- Register every verified package in `theseus_registry.json`
- Run `make test` before every commit

**Ask first:**
- Adding a Theseus registry dependency (confirm it is itself verified)
- Descoping a package (document why in `reports/audit/`)
- Changing the isolation protocol

**Never:**
- Import the original package in a clean-room implementation
- Cross language boundaries in an implementation
- Use subprocess to call the original tool as a back-end
- Mark a package `verified` until all spec invariants pass under isolation

---

## Success Criteria

- [ ] `cleanroom/python/` contains ≥3 verified packages with 0 external deps each
- [ ] `cleanroom/node/` contains ≥1 verified Node.js package
- [ ] All verified packages are in `theseus_registry.json` with `status: "verified"`
- [ ] `tools/cleanroom_verify.py` rejects any implementation that imports the original
- [ ] `make test` passes with full test suite including isolation tests
- [ ] No `*_rust.zspec.zsdl` wrapper spec is presented as a clean-room implementation
