# Prioritized dependency scans

Theseus refreshes existing recipes with `make refresh`. To discover gaps instead,
use the dependency frontier:

```sh
make scan-queue
make scan SCAN_LIMIT=20
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

Batches are finite, execute in reference order, and skip packages already covered
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
read-only mount must be updated outside the container, then imported. The OSRB
Compose variant uses `THESEUS_HOST_PATH`. These settings describe the repository's
supported paths, not a claim that a particular deployment has imported this batch.

Both `specs/` recipes and fabric fingerprints are produced by the scanner so the
existing importer can consume new packages without a submodule or importer change.

## Recorded verification (2026-10-20)

Two finite batches added 20 missing Python and 20 missing npm packages, including
SciPy, `@types/node` and `@babel/core`; one explicit scan refreshed existing NumPy.
The fabric validates all 272 fingerprints. The refreshed frontier has 643 pending
registry entries and 278 manual entries; covered entries are skipped on resume.
Those are snapshot counts, not a maintained reverse index or a promise of complete
OSS coverage.

The queue/fabric/refresh/ranking tests pass all 100 cases; strict documentation
build passes. The existing oss-tracker importer accepted all 272 canonical recipes
without errors in a disposable in-memory database, including NumPy and SciPy. No
oss-tracker deployment or application database was changed.

The full local suite has the same six historical characterization/qualification
failures as the baseline: 4880 passed and 913 optional skips after this work,
compared with 4866 passed and 913 skips before it. They are tracked by
[Theseus #11](https://github.com/jordanhubbard/Theseus/issues/11); the separate
[repair PR #12](https://github.com/jordanhubbard/Theseus/pull/12) still has failing
Linux/FreeBSD CI. This queue work does not modify research authorities to bypass
those gates. The repository's no-failing-test-push rule keeps this change local
until that baseline is repaired.
