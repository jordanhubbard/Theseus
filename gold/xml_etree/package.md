---
family: xml_etree
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - fromstring
public_oracle: zspecs/theseus_xml_etree_q.zspec.zsdl
blocks: xml
cleanroom_oracle: zspecs/theseus_xml_etree_q.zspec.zsdl
held_out_oracle: gold/xml_etree/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_xml_etree_q
docs:
  - "https://docs.python.org/3/library/xml.etree.elementtree.html"
rfcs:
  []
---

# xml.etree

fromstring(text) parses one XML element. The text attribute is the character data inside that element. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

fromstring(text) parses one XML element. The text attribute is the character data inside that element.

## What is not in scope

Writing XML, namespaces, and iteration.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
