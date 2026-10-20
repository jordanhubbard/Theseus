# Prioritized dependency scans

Theseus refreshes existing recipes with `make refresh`. To discover gaps instead,
use the dependency frontier:

```sh
make scan-queue
make scan SCAN_LIMIT=20 SCAN_JOBS=4
make scan SCAN_ECOSYSTEM=pypi SCAN_LIMIT=20
```

The queue is `reports/scan-queue.json`; the latest batch report is
`reports/scan-results.json`. Both are gitignored, reproducible operational
artifacts. Recipes under `specs/` and fingerprints under `fabric/packages/` remain
the committed database. There is no authoritative reverse-dependency index.

Priority is descending **distinct consuming canonical packages** in the local
recipe/fingerprint corpus, with stable name/ecosystem ties. A package counts once
per dependency regardless of scope or duplicate recipe sightings. Registry
namespaces are separate; PyPI spellings normalize and scoped npm identifiers are
preserved. Counts are catalog references, not download counts, global popularity,
or references measured in oss-tracker's project database. Each plan carries a
source digest, exact referrers and covered/pending/manual states.

Batches are finite, fetch metadata with bounded concurrency (1–16 workers), commit recipes in reference order, and skip packages already covered
when resuming an older queue. Registry failures preserve prior evidence and fail
the command visibly; successful items are still ingested. Recipes use atomic
replacement. Scoped npm registry IDs map to Theseus's filesystem-safe canonical
names. Unknown native recipe paths and unsupported registries remain manual;
the scanner does not guess a PyPI/npm counterpart. Newly scanned packages can
introduce new references, so a growing frontier does not mean completed scans
were lost.

To explicitly refresh an already-covered example:

```sh
python3 tools/scan_queue.py run --refresh-covered --package pypi:numpy --limit 1
python3 tools/scan_queue.py plan
```

Metadata is fetched from public PyPI/npm registry APIs through the existing
importers. It is not a behavioral/source-security scan or legal approval. No
implementation source is fetched or executed. Optional behavioral evidence stays
separate. Failed or absent metadata is never labeled scanned successfully.

## oss-tracker consumption

oss-tracker does **not** contain Theseus as a Git submodule. Its existing backend
has an independent catalog checkout/import pipeline:

1. `app.services.theseus_sync_service.sync_theseus_once` uses `THESEUS_LOCAL_PATH`
   (default `/data/theseus`). If `THESEUS_GIT_URL` is set, it clones or fetches
   `THESEUS_GIT_REF` (default `main`) into that separate checkout and selects the
   fetched commit. Configure a dedicated checkout: the sync command changes its
   selected Git revision.
2. `app.services.theseus_importer.import_theseus` imports canonical **`specs/`**
   recipes into oss-tracker's `TheseusPackage` SQL table. Optional compiled
   `_build/zspecs/` evidence augments the rows. It does **not** directly mount or
   query Theseus's `fabric/packages/` as its application database.
3. The `db` provider queries the imported table; existing import conflict rules
   preserve newer application edits. A changed Theseus working tree alone does
   not update the application's imported rows.

From oss-tracker's backend directory, the existing explicit commands are:

```sh
# Import a local checkout, without fetching or changing its Git revision:
python -m scripts.import_theseus --path /path/to/theseus
# Fetch the configured dedicated checkout and import it:
python -m scripts.sync_theseus
```

Recurring source sync is opt-in: `THESEUS_SYNC_ENABLED=true`, with
`THESEUS_SYNC_INTERVAL_SECONDS` defaulting to 86400, through the existing
scheduled automation. Defaults have sync disabled and no Git URL. Deployment
Compose mounts `${DEPLOY_STATE_DIR}/theseus` read-only at `/data/theseus`; a
read-only mount must be updated outside the container, then imported. A deployment
that supports a configurable `THESEUS_LOCAL_PATH` can instead select a dedicated
writable checkout under its existing persistent storage mount (for example
`/data/storage/theseus-git`), set `THESEUS_GIT_URL` to the catalog repository and
`THESEUS_GIT_REF=main`, and enable the existing recurring sync. Do not point it
at an operator development checkout. The OSRB
Compose variant uses `THESEUS_HOST_PATH`. These settings describe the repository's
supported paths, not a claim that a particular deployment has imported this batch.

Both `specs/` recipes and fabric fingerprints are produced by the scanner so the
existing importer can consume new packages without a submodule or importer change.

## Recorded verification (2026-10-20)

Three finite batches added 20 missing Python and 40 missing npm packages,
including SciPy, `@types/node`, `@babel/core`, Chai and Vitest; one explicit scan
refreshed NumPy. A metadata repair refreshed all 117 PyPI recipes without registry
failures. The fabric validates 292 fingerprints. The latest derived frontier has
846 pending registry entries, 187 covered targets and 278 manual entries. Scanning
new packages exposes further references; these are snapshot counts, not a promise
of complete OSS coverage.

The published CI repair branch is included, together with corrections to public
API contracts that previously pinned Python 3.14/macOS observations. The local
suite passes 4902 tests with 913 optional dependency skips. Clean Linux containers
pass the full available corpus on Python 3.9 and 3.12; explicit availability gates
cover versioned APIs without disabling the corpus check. Hosted matrix and FreeBSD
CI remain the merge authority. Structured fixture regression tests cover module
references, callable inputs, None-valued attributes, dotted membership, FreeBSD
platform normalization and C version-function arguments.

oss-tracker's existing importer accepted all 292 canonical recipes without failures
in a disposable in-memory database (0.184 seconds including schema setup), including
NumPy 2.5.4 and SciPy 1.18.1. Production Git sync must
be verified against the exact merged main commit; local catalog changes alone do
not establish deployment or application import success.

## Ingestion throughput and metadata limits

`SCAN_JOBS` defaults to four at the CLI. At most that many requests/results are
retained concurrently; writes stay serialized and atomic in priority order.
The scanner ingests the catalog once after a batch, rather than rebuilding it
for each fetched package. Timestamp-only fabric rewrites are avoided. Existing
recipe refresh already supports parallel requests through `--jobs`.

PyPI JSON does not establish build requirements: the importer leaves build
edges empty and records this limitation instead of assigning setuptools/wheel
to every package. Original `requires_dist`, SPDX `license_expression` and legacy
license text are retained for audit. Runtime edges remain a simplified registry
projection; conditional markers and extras require the retained raw metadata.
No package source is downloaded to infer missing facts.

The next throughput limits remain distinct from registry fetching: plans read the
catalog to derive reference counts, fabric ingestion validates the full batch,
and optional behavioral qualification starts many library/Node processes. Keep
those expensive behavioral gates separate from ordinary metadata ingestion.
Use a fresh compilation directory for corpus qualification: an existing ignored
`_build/zspecs` directory can retain JSON for removed source files (12 stale files
were present in the inspected development checkout). Hosted jobs use clean
checkouts. No compiler output or behavioral report is an authoritative package
recipe, and a missing library stays explicitly skipped rather than passing.

Corpus failures print their invariant IDs and messages in the CI log as well as
writing JSON. This makes failures inside the FreeBSD guest diagnosable even when
its temporary pytest artifacts are unavailable to the host upload step. Platform
checks use explicit Linux, Darwin and FreeBSD contracts; floating-point identities
allow documented double-precision rounding rather than host-specific last bits.
