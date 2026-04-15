---
name: End-to-end validation harness (added 2026-04-08)
description: New files and capabilities added for source-fetch → build → verify pipeline
type: project
---

**New/modified files:**
- `tools/build_and_verify.py` — main harness: license gate → source fetch → build → install → verify
- `theseus/remote.py` — extended with `build_from_source_on_target()`, `SourceBuildResult`, `_BUILD_SYSTEM_COMMANDS`
- `tools/verify_behavior.py` — added `--lib-dir PATH` flag to prepend custom directory to ctypes search
- `Makefile` — added `validate-e2e` target (E2E_RECORD=, E2E_ZSPEC=, E2E_TARGET=, E2E_JSON_OUT=)
- `theseus/importer.py` — added `_normalize_github_url()`, `_pypi_source_repo()`, `_license_is_permissive()`; npm/PyPI records now include `extensions.npm.source_repository` and `extensions.pypi.source_repository`

**Usage:**
```bash
make validate-e2e E2E_RECORD=specs/zlib.json E2E_ZSPEC=_build/zspecs/zlib.zspec.json
make validate-e2e E2E_RECORD=specs/zlib.json E2E_ZSPEC=_build/zspecs/zlib.zspec.json E2E_TARGET=ubuntu.local
```

**Test targets:** jkh@ubuntu.local (Linux/nixpkgs via Docker), jkh@freebsd.local (FreeBSD Ports), macOS local.

**Why:** Proves the Z-specs correctly describe packages that can be built from source, not just packages that happen to be installed.
