---
family: hmac
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - new
  - digest
  - compare_digest
  - HMAC
public_oracle: zspecs/hmac.zspec.zsdl
blocks: hmac
cleanroom_oracle: zspecs/theseus_hmac_q.zspec.zsdl
held_out_oracle: gold/hmac/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_hmac_q
docs:
  - https://docs.python.org/3/library/hmac.html
rfcs:
  - "RFC 2104"
  - "RFC 4231"
  - "FIPS 198-1"
---

# hmac

Keyed-hash message authentication (HMAC) over SHA-2 families. compare_digest is a constant-time equality helper. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/hmac.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

RFC 4231 test cases 1 and 2, compare_digest on strings, digest_size/block_size, TypeError on mixed compare_digest types.

## What is not in scope

Timing guarantees beyond 'use compare_digest', OpenSSL HMAC internals, SHA-384/512 RFC 4231 cases not yet listed.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
