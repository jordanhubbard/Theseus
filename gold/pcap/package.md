---
family: pcap
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - pcap_open_offline
public_oracle: zspecs/libpcap.zspec.zsdl
docs:
  - https://www.tcpdump.org/manpages/pcap.3pcap.html
rfcs:
  - "draft-ietf-opsawg-pcap"
---

# pcap

Alias family for libpcap (pcap savefile format). The executable oracle is zspecs/libpcap.zspec.zsdl. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/libpcap.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

Same as libpcap.

## What is not in scope

A second zspec named pcap would duplicate the gold set.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
