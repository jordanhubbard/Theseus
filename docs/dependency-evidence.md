# Dependency Evidence

Theseus keeps dependency evidence in committed manifests so OSS reviewers can
reproduce the dependency surface without reading CI logs.

## Project License

The project license is BSD-2-Clause:

- `LICENSE` contains the BSD 2-Clause text.
- `README.md` links to the BSD 2-Clause license.
- `package.json` and the root package entry in `package-lock.json` declare
  `BSD-2-Clause`.
- GitHub reports `jordanhubbard/Theseus` as BSD-2-Clause as of 2026-05-06.

## JavaScript Dependencies

Node.js dependencies are declared in `package.json` and locked in
`package-lock.json`. The lockfile is the source of truth for the npm transitive
closure.

The committed lockfile was refreshed on 2026-05-28 with:

```bash
npm_config_cache=/tmp/theseus-npm-cache npm update --package-lock-only
npm_config_cache=/tmp/theseus-npm-cache npm audit --omit=dev --json
```

That refresh records npm license metadata for every direct dependency except
`svg-tags@1.0.0`, whose old npm metadata uses the legacy `licenses` array
instead of the modern `license` field. The registry metadata still declares MIT
for `svg-tags`.

Direct dependency license evidence:

| Package | Locked Version | License Evidence |
| --- | --- | --- |
| `ajv` | `8.20.0` | `MIT` in `package-lock.json` |
| `chalk` | `5.6.2` | `MIT` in `package-lock.json` |
| `cross-spawn` | `7.0.6` | `MIT` in `package-lock.json` |
| `esbuild` | `0.28.0` | `MIT` in `package-lock.json` |
| `execa` | `9.6.1` | `MIT` in `package-lock.json` |
| `express` | `4.22.2` | `MIT` in `package-lock.json` |
| `html-tags` | `5.1.0` | `MIT` in `package-lock.json` |
| `jszip` | `3.10.1` | `(MIT OR GPL-3.0-or-later)` in `package-lock.json`; Theseus uses the MIT option |
| `lodash` | `4.18.1` | `MIT` in `package-lock.json` |
| `minimist` | `1.2.8` | `MIT` in `package-lock.json` |
| `ms` | `2.1.3` | `MIT` in `package-lock.json` |
| `node-forge` | `1.4.0` | `(BSD-3-Clause OR GPL-2.0)` in `package-lock.json`; Theseus uses the BSD-3-Clause option |
| `prettier` | `3.8.3` | `MIT` in `package-lock.json` |
| `semver` | `7.8.1` | `ISC` in `package-lock.json` |
| `svg-tags` | `1.0.0` | `MIT` in npm registry `licenses[].type`; legacy metadata does not populate a lockfile `license` field |
| `ulid` | `3.0.2` | `MIT` in `package-lock.json` |
| `uuid` | `13.0.2` | `MIT` in `package-lock.json` |

`node-forge@1.4.0` is present with integrity
`sha512-LarFH0+6VfriEhqMMcLX2F7SwSXeWwnEAJEsYm5QKWchiVYVvJyV9v7UDvUv+w5HO23ZpQTXDv/GxdDdMyOuoQ==`.
After the 2026-05-28 lockfile refresh, `npm audit --omit=dev --json` reports
zero vulnerabilities for the committed production npm tree and does not report a
`node-forge` advisory.

## Python Dependencies

The core Python runtime remains stdlib-only. Python packages used for local
tooling, tests, docs, and CI are declared explicitly:

- `requirements.txt` covers local test, ZSDL compilation, and docs tooling.
- `requirements-ci.txt` extends `requirements.txt` with optional third-party
  libraries used by behavior-spec tests in GitHub Actions.

These requirements intentionally use bounded ranges instead of a committed
transitive lock. They are a cross-version tooling/test matrix, not a production
runtime environment, and the Theseus runtime itself has no third-party Python
dependency. For a point-in-time scanner snapshot, install `requirements-ci.txt`
in the target Python version and capture `python -m pip freeze`.

Use:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

CI installs:

```bash
python -m pip install -r requirements-ci.txt
```

## GitHub Actions

Workflow files are committed under `.github/workflows/`. Third-party actions are
pinned to commit SHAs, not mutable version tags. The pins were resolved from the
upstream tags on 2026-05-06:

| Action | Tag | Commit |
| --- | --- | --- |
| `actions/checkout` | `v4` | `34e114876b0b11c390a56381ad16ebd13914f8d5` |
| `actions/setup-python` | `v5` | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| `actions/setup-node` | `v4` | `49933ea5288caeca8642d1e84afbd3f7d6820020` |
| `actions/upload-artifact` | `v4` | `ea165f8d65b6e75b540449e92b4886f43607fa02` |
| `actions/upload-pages-artifact` | `v3` | `56afc609e74202658d3ffba0e8f6dda462b719fa` |
| `actions/deploy-pages` | `v4` | `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e` |
| `cross-platform-actions/action` | `v0.32.0` | `492b0c80085400348c599edace11141a4ee73524` |

## Docker Verification Sandbox

`docker/Dockerfile.verify` uses the official Ubuntu 26.04 image pinned by digest:

```text
ubuntu:26.04@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64
```

The Docker Hub manifest inspected on 2026-05-06 reports official Ubuntu 26.04
image annotations with `org.opencontainers.image.created: 2026-04-21T00:00:00Z`.

The apt package list in `docker/Dockerfile.verify` intentionally keeps comments
outside the continued `apt-get install` list. This avoids weak dependency
scanners interpreting comment words as package names.

Refresh the base-image pin only as an intentional review step. Suggested refresh
process:

```bash
docker buildx imagetools inspect ubuntu:26.04
# update docker/Dockerfile.verify and this evidence note together
make docker-build
```

Record the new digest, manifest inspection date, and image-created annotation in
this section when the pin changes.

## Rust/Cargo Dependencies

Theseus does not have a root Rust crate, so there is no committed `Cargo.toml`
or `Cargo.lock` for project dependencies. Cargo appears in the Docker sandbox
only as an optional verifier installer for specs invoked with
`tools/verify_in_docker.py --cargo <crate>`. Those crates are per-run inputs, not
part of the committed Theseus dependency graph.

If a root Rust crate is added later, commit its `Cargo.lock` alongside the
manifest.

## Scanner Scope

`.claude/worktrees/` is ignored by git and is not part of the dependency
inventory. Those directories are ephemeral agent working copies and should be
excluded from OSS dependency scanning.
