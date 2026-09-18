# Characterization loop

Phase 2 of the verification-ladder refresh ([ADR 0003](decisions/0003-characterization-loop.md)).
This is how Theseus turns public documentation into a reviewed gold-set family.
It does **not** qualify a replacement.

## Artifacts

Each family lives in `gold/<family>/`:

| File | Role |
|---|---|
| `package.md` | Authority (Markdown + YAML frontmatter). Human-reviewable intent. |
| `uncertainty.yaml` | Reviewed ledger. Every item is `resolved`, `deferred`, or `held_out`. |
| `probes.yaml` | Optional live probes against the **installed** public API. |
| `held_out.zspec.zsdl` | Optional independent oracle. JSON and the Phase 3 Python gold-set families have one. Native/Node families do not. |

The executable public oracle is the Layer 2 ZSDL named in `public_oracle:` (usually `zspecs/<name>.zspec.zsdl`).

Required frontmatter keys: `family`, `public_oracle`, `ladder`, `qualification`.
`qualification` must be `none`.

## Loop

```
public docs / RFCs
        │
        ▼
gold/<family>/package.md          ← write what the package is supposed to do
zspecs/<name>.zspec.zsdl          ← executable invariants (public API + args)
        │
        ▼
tools/live_probe.py               ← confirm expected values on the installed library
gold/<family>/probes.yaml         ← keep the probes that should stay green
        │
        ▼
gold/<family>/uncertainty.yaml    ← resolve, defer, or hold out every leftover claim
        │
        ▼
tools/characterize.py <family>    ← compile + verify oracle + probes + optional held-out
```

Do **not** open implementation source (`mod.__file__`, CPython `Lib/`, npm `.js`) to fill an expected value. If a value cannot be justified from public docs plus a black-box call, put it on the ledger as `deferred` or `held_out`.

## Commands

```bash
# One family
python3 tools/live_probe.py --from gold/json/probes.yaml
python3 tools/characterize.py json

# Every gold/<family>/ tree
make characterize-gold

# Ad-hoc probe (import name, not a path)
python3 tools/live_probe.py --module json --function dumps --args '[42]'
python3 tools/live_probe.py --module hashlib --function sha256 \
  --args '[{"type":"bytes_ascii","value":""}]' --method hexdigest
```

`tomli` / `tomllib` skip on Python 3.9–3.10 (`tomllib` is 3.11+).
`libpcap` / `pcap` / `pcapng` skip when the shared library is not installed.
Skipped families are not failures.

## Ledger rules

- `reviewed: true` is required before `characterize.py` will accept the family.
- Statuses: `resolved` | `deferred` | `held_out`. No `open` on an accepted ledger.
- `held_out` items point at vectors that must not appear in a synthesis prompt.
- JSON's distinctive held-out tokens stay in `gold/json/held_out.zspec.zsdl` (ADR 0002). Layer 2 deepen must not copy them into `zspecs/json.zspec.zsdl`.

## What this does not claim

- Passing the public oracle is **oracle_bound**, not `qualified`.
- An accepted ledger is **characterized** review, not empty-workspace regeneration.
- Held-out oracles for attempted Python gold-set families live in `gold/<family>/held_out.zspec.zsdl` ([ADR 0004](decisions/0004-qualification-protocol.md)). Qualification still requires two independent generations; that has not happened ([ADR 0005](decisions/0005-characterization-is-the-product.md)).

## Alias families

| Family | Oracle |
|---|---|
| `tomllib` | `zspecs/tomli.zspec.zsdl` (stdlib name; 3.11+) |
| `pcap` | `zspecs/libpcap.zspec.zsdl` |
