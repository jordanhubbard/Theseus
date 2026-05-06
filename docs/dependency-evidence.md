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

`node-forge@1.4.0` is a direct dependency. The lockfile records its license as
`(BSD-3-Clause OR GPL-2.0)`; Theseus uses the BSD-3-Clause license option.

## Python Dependencies

The core Python runtime remains stdlib-only. Python packages used for local
tooling, tests, docs, and CI are declared explicitly:

- `requirements.txt` covers local test, ZSDL compilation, and docs tooling.
- `requirements-ci.txt` extends `requirements.txt` with optional third-party
  libraries used by behavior-spec tests in GitHub Actions.

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

## Scanner Scope

`.claude/worktrees/` is ignored by git and is not part of the dependency
inventory. Those directories are ephemeral agent working copies and should be
excluded from OSS dependency scanning.
