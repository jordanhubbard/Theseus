---
family: urllib_parse
version: "0.2.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - urlparse
  - urljoin
  - quote
  - unquote
  - urlencode
  - parse_qs
  - urlunparse
public_oracle: zspecs/urllib_parse.zspec.zsdl
blocks: urllib.parse
cleanroom_oracle: zspecs/theseus_urllib_parse_q.zspec.zsdl
held_out_oracle: gold/urllib_parse/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_urllib_parse_q
docs:
  - https://docs.python.org/3/library/urllib.parse.html
rfcs:
  - "RFC 3986"
  - "RFC 1808"
---

# urllib_parse

URL parsing and quoting per RFC 3986 as implemented by urllib.parse. ParseResult fields are accessed after construction. This file is the **authority** for the gold-set family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/urllib_parse.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

scheme/netloc/path/query/fragment, userinfo, quoting with safe=/, urljoin, parse_qs multi-value, RFC 3986 example host.

## What is not in scope

IRI (RFC 3987), WHATWG URL parser differences, idna encoding of hosts.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
