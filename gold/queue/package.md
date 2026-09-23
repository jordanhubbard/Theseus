---
family: queue
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - Queue
public_oracle: zspecs/theseus_queue_q.zspec.zsdl
blocks: queue
cleanroom_oracle: zspecs/theseus_queue_q.zspec.zsdl
held_out_oracle: gold/queue/held_out.zspec.zsdl
implementation: cleanroom/python/theseus_queue_q
docs:
  - "https://docs.python.org/3/library/queue.html"
rfcs:
  []
---

# queue

Queue() starts empty. empty() is true when no items have been put. qsize() is the number of items. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle.

## Public surface

Exports listed in the frontmatter are the characterization surface.

## What is in scope

Queue() starts empty. empty() is true when no items have been put. qsize() is the number of items.

## What is not in scope

Joining worker threads, blocking timeouts, and priority or LIFO queues.

## Characterization loop

Draft from public docs. Confirm expected values with a live probe against the installed library. Do not read implementation source into a generation prompt. Passing the public oracle is **not** qualification (ADR 0001).

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
