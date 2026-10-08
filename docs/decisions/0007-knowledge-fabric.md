# ADR 0007: The Product Is an OSS Knowledge Fabric

- Status: Accepted
- Date: 2026-10-07
- Decision owners: Theseus maintainers
- Depends on: [ADR 0005](0005-characterization-is-the-product.md)
- Supersedes (product claim only): ADR 0005

## Context

Theseus began as a package-recipe normalizer, then attempted clean-room
recreation from behavioral specs. Spec-driven synthesis proved brittle:
few components can be built entirely from a spec, qualification was
withdrawn as a shipping claim (ADR 0005), and characterization became
the interim product.

The durable thing Theseus already had — and the thing the spec process
never scaled — is *identity knowledge*: where a package came from, which
repository it lives in, what license it carries, and how it is wired to
other packages in both directions.

Recreation from spec remains a research protocol. It is not the reason
to run Theseus.

## Decision

Theseus's **product** is a git-backed OSS knowledge fabric.

A fingerprint records, for one canonical package:

- provenance of every claim (which recipe, which importer, source path, source commit, confidence)
- tracking (maintainers, categories, distributions, dropped dependency tokens)
- source repository, when it can be stated with confidence
- license (raw tokens plus a light SPDX mapping)
- outbound dependencies with resolved vs dangling edges (runtime / build / host / test)
- ecosystem sightings (Nixpkgs, FreeBSD Ports, PyPI, npm, …)

Ingest priority is provenance, tracking, and dependencies. Recreation-from-spec
stays linked as `evidence.recreation: secondary` when a ZSDL file exists. Recipes
are converted in parallel (`tools/fabric.py ingest --jobs`).

Reverse dependencies are **derived** from the committed outbound graph,
not stored as a second source of truth.

**Git is the database.** Each fingerprint is a file under
`fabric/packages/`. The working tree is the current snapshot. `git log`
is the audit trail. `git show <rev>:fabric/packages/<name>.json` is a
point-in-time read. There is no SQL store.

Layer 1 package recipes are the ingest source. Layer 2 behavioral specs
are optional evidence attached to a fingerprint when they exist. Layer 3
clean-room artifacts remain in-tree as historical research; they do not
define success.

ADR 0005 still stands for its kill-gate conclusion: regenerative
replacement is not a shipping claim. This ADR changes what *is* the
shipping claim: coverage and fidelity of the identity graph, not
characterization depth and not qualified reimplementations.

## Consequences

- README, AGENTS.md, PLAN.md, architecture, and the user guide describe
  the fabric first.
- `make start` reports fabric coverage.
- `make refresh` / `make reingest` restock committed recipes from live
  upstreams and rebuild fingerprints. Keeping the fabric current does not
  require a prior `snapshots/` directory.
- New work prefers ingesting, querying, and tightening fingerprints
  over expanding synthesis waves.
- A later reversal requires a superseding ADR.

## Rejected alternatives

- Keep characterization as the product and treat identity metadata as
  a Layer 1 implementation detail.
- Store the graph in SQLite / Postgres “and also commit JSON.” That
  splits the source of truth.
- Persist reverse-edge indexes as canonical data. They drift.
