---
family: semaphore
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Semaphore
public_oracle: zspecs/theseus_semaphore_q.zspec.zsdl
blocks: threading
cleanroom_oracle: zspecs/theseus_semaphore_q.zspec.zsdl
held_out_oracle: gold/semaphore/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_semaphore_q
docs:
  - "https://docs.python.org/3/library/threading.html"
rfcs:
  []
---

# threading

Semaphore(value) starts with a counter. acquire() takes one permit. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

acquire() returns true and decreases the counter when the counter is positive. acquire(false) returns false immediately when the counter is already zero.

## What is not in scope

timeouts, release, and threads.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
