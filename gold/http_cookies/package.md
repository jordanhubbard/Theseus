---
family: http_cookies
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - SimpleCookie
public_oracle: zspecs/theseus_http_cookies_q.zspec.zsdl
blocks: http.cookies
cleanroom_oracle: zspecs/theseus_http_cookies_q.zspec.zsdl
held_out_oracle: gold/http_cookies/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_http_cookies_q
docs:
  - "https://docs.python.org/3/library/http.cookies.html"
rfcs:
  []
---

# http.cookies

SimpleCookie(header).output() returns a Set-Cookie line for a single name=value pair. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

SimpleCookie(header).output() returns a Set-Cookie line for a single name=value pair.

## What is not in scope

Morsel attributes such as Path, Expires, and multiple cookies.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
