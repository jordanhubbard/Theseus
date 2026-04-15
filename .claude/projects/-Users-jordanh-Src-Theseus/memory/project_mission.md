---
name: Theseus project mission and scope
description: What Theseus is, its four ecosystems, and the proof-of-concept goals
type: project
---

Theseus normalizes package recipes from 4 ecosystems (Nixpkgs, FreeBSD Ports, PyPI, npm) into a canonical JSON schema, ranks/extracts top candidates, and verifies behavioral contracts (Z-specs) against real installed libraries.

**Why:** npm (2M+ packages) and PyPI (500k+ packages) are the most relevant modern ecosystems; Nix and FreeBSD Ports are important but narrower. All four are now first-class citizens.

**Open proof-of-concept:** validate the other side of the contract — given a Z-spec, can we actually fetch source, build from scratch, and have the spec pass? The end-to-end harness (`tools/build_and_verify.py`, `make validate-e2e`) was built to prove this.

**How to apply:** When the user talks about "validating the contract" or "proving the concept works," they mean running `make validate-e2e` against a real package on linux (jkh@ubuntu.local), FreeBSD (jkh@freebsd.local), and macOS (host).
