---
family: elementtree
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - fromstring
  - tostring
  - Element
  - SubElement
  - ParseError
public_oracle: zspecs/elementtree.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/xml.etree.elementtree.html"
rfcs:
  []
---

# xml.etree.ElementTree

Lightweight XML tree API. fromstring parses a string to an Element; tag/text/attrib/findtext are the documented accessors; invalid XML raises ParseError. This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/elementtree.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

fromstring tag/text/findtext, ParseError on malformed markup, Element constructor tag.

## What is not in scope

XPath beyond simple child paths, XMLParser/TreeBuilder, write() to files, namespace Clark notation tables.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
