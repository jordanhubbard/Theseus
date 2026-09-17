---
family: pcapng
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - pcap_open_offline
  - pcap_major_version
  - pcap_datalink
public_oracle: zspecs/pcapng.zspec.zsdl
docs:
  - https://datatracker.ietf.org/doc/html/draft-ietf-opsawg-pcapng
rfcs:
  - "draft-ietf-opsawg-pcapng"
---

# pcapng

PCAP Next Generation files as read by libpcap. Empty SHB+IDB files distinguish pcapng (major=1) from classic pcap (major=2). This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/pcapng.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

SHB version 1.0, IDB linktypes, snaplen, byte-order magic, truncated/empty/garbage rejection.

## What is not in scope

Enhanced Packet Block payloads, options TLVs, live capture.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
