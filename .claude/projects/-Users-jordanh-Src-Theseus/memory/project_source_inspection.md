---
name: Source code inspection policy
description: Rules for when AI agents may clone and read package source code
type: project
---

Agents may clone and read source code for packages licensed under BSD (any clause), MIT, Apache 2.0, ISC, or similar permissive licenses.

**Prohibited:** GPL, LGPL, AGPL, and any dual-licensed package where GPL is one option. Do not `git clone`, `make extract`, `nix build`, or otherwise access implementation source for these.

**Codified in:** AGENTS.md "Source Code Inspection Policy" section (added 2026-04-08).

**How to check:** `descriptive.license` in the canonical record, or `extensions.npm.source_repository` / `extensions.pypi.source_repository` for ecosystem records.

**Why:** User explicitly released this constraint on 2026-04-08, specifying BSD/MIT/Apache as permissible and explicitly excluding all GPL variants including dual-licensed.
