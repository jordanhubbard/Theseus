---
family: binascii
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - crc32
  - hexlify
  - unhexlify
  - Error
public_oracle: zspecs/binascii.zspec.zsdl
docs:
  - https://docs.python.org/3/library/binascii.html
rfcs:
  - "ISO/IEC 3309"
---

# binascii

Low-level binary-to-ASCII helpers. crc32 implements the ISO 3309 / ITU-T V.42 polynomial; hexlify is lowercase hex. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/binascii.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

crc32 empty and ITU V.42 check string, hexlify lengths and values, unhexlify odd-length Error.

## What is not in scope

a2b_base64 wrapping, uu, qp, signed-vs-unsigned crc32 on Python 2.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
