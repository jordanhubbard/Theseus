---
family: base64
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - b64encode
  - b64decode
  - urlsafe_b64encode
  - urlsafe_b64decode
  - b32encode
  - b16encode
public_oracle: zspecs/base64.zspec.zsdl
blocks: base64
cleanroom_oracle: zspecs/theseus_base64_q.zspec.zsdl
held_out_oracle: gold/base64/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_base64_q
docs:
  - https://docs.python.org/3/library/base64.html
rfcs:
  - "RFC 4648"
---

# base64

Base64/32/16 codecs as specified by RFC 4648. Python functions take and return bytes (decode also accepts ASCII str). This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/base64.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

RFC 4648 §10 encode/decode vectors, URL-safe alphabet, validate=True errors.

## What is not in scope

legacy capt80, a85encode, wrapping newlines on b64encode(altchars).

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
