# Reports

Generated tool output lives here. Most of `reports/` is gitignored.

Committed exceptions:

- `reports/synthesis/wave_state.json` — synthesis wave progress
- `reports/audit/` — corpus autopsy and factory-wrapper freeze
- `reports/qualification/` — ADR 0004 qualification receipts (`summary.json` and per-family JSON)

`make qualify-check` refreshes qualification receipts. Do not mark `qualified: true`
without two independent generations (ADR 0004 / ADR 0005).
