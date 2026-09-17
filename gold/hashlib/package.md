---
family: hashlib
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - sha256
  - sha512
  - sha1
  - md5
  - sha3_256
  - blake2b
  - algorithms_guaranteed
public_oracle: zspecs/hashlib.zspec.zsdl
docs:
  - https://docs.python.org/3/library/hashlib.html
rfcs:
  - "FIPS 180-4"
  - "RFC 1321"
  - "FIPS 202"
---

# hashlib

Cryptographic hashes from FIPS 180-4 / 202 and RFC 1321, exposed as hashlib constructors that return objects with hexdigest/digest/update. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/hashlib.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Empty and 'abc' KATs for SHA-256/512/1, MD5, SHA3-256; algorithms_guaranteed membership; copy independence.

## What is not in scope

OpenSSL engine selection, usedforsecurity FIPS enforcement, shake XOF length variants beyond documented digest_size.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
