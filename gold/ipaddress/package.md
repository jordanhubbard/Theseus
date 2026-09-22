---
family: ipaddress
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - IPv4Address
  - IPv6Address
  - IPv4Network
  - ip_address
  - ip_network
public_oracle: zspecs/ipaddress.zspec.zsdl
blocks: ipaddress
cleanroom_oracle: zspecs/theseus_ipaddress_q.zspec.zsdl
held_out_oracle: gold/ipaddress/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_ipaddress_q
docs:
  - "https://docs.python.org/3/library/ipaddress.html"
rfcs:
  - "RFC 791"
  - "RFC 1918"
  - "RFC 4291"
  - "RFC 8200"
---

# ipaddress

IPv4/IPv6 address and network objects. Constructors parse textual forms; is_private follows RFC 1918; packed is the network-order bytes. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/ipaddress.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

IPv4Address/IPv6Address string roundtrip, RFC 1918 private, loopback, unspecified, packed length, factory ip_address/ip_network, AddressValueError on bad octets, ValueError on host bits when strict.

## What is not in scope

Interface objects, scoped IPv6 zone ids, reverse pointer generation, collapse_addresses.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
