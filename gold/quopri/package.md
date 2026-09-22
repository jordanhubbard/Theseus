---
family: quopri
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - encodestring
  - decodestring
  - encode
  - decode
public_oracle: zspecs/quopri.zspec.zsdl
blocks: quopri
cleanroom_oracle: zspecs/theseus_quopri_q.zspec.zsdl
held_out_oracle: gold/quopri/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_quopri_q
docs:
  - "https://docs.python.org/3/library/quopri.html"
rfcs:
  - RFC 2045
---

# quopri

Quoted-printable encoding (RFC 2045 §6.7). encodestring/decodestring operate on bytes. =3D decodes to '='. Printable ASCII without '=' is unchanged. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/quopri.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

decodestring of plain ASCII, empty, and =3D; encodestring of hello.

## What is not in scope

Stream encode/decode file objects; quoted-printable soft line breaks at 76 columns.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
