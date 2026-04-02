# Schema Evolution

The canonical record schema (`schema/package-recipe.schema.json`) is versioned via the `schema_version` field present in every record. The current version is **`0.2`**.

## Compatibility rules

Theseus follows a simple two-rule policy:

1. **Additive changes are backward-compatible.** New optional fields may be added to any object. Existing tools ignore fields they do not read (`additionalProperties: true` is set on all sub-objects for this reason).
2. **Removals and renames require a version bump.** Any change that removes or renames a required field, or changes a field's type, must increment `schema_version`.

This means:
- Tools written against 0.1 records will continue to work when new optional fields appear in 0.2 records.
- Tools must not assume records they load are always the current version. When strict compatibility matters, check `schema_version` before processing.

## Version history

| Version | Changes |
|---------|---------|
| 0.2 | Promoted `maintainers` (list of strings) into `descriptive`. Added `deprecated` (bool) and `expiration_date` (string, ISO-8601) to `descriptive`. Added `conflicts` (list of package name strings) as a required top-level field. Added `behavioral_spec` (string, optional) — repo-relative path to a matching Z-layer behavioral spec file. |
| 0.1 | Initial schema. All top-level required fields established. |

## When a version bump is needed

Before bumping the version:

1. Document the change in this file under a new row in the version history table.
2. Update `SCHEMA_VERSION` in `tools/bootstrap_canonical_recipes.py`.
3. Update `validate_record.py` if the new version adds required fields or changes type rules.
4. Add or update example records in `examples/` to reflect the new schema.
5. Run `make test` and `make validate`.

## Forward compatibility fields

Three fields in `provenance` were designed to carry information that doesn't yet have a home in the schema:

- **`unmapped`** — field names the importer saw in the source but could not normalize. If the same field name appears frequently across many records in `unmapped`, it is a signal that the schema should grow to include it.
- **`warnings`** — importer-generated notes about parse quality or known lossiness. Downstream tools should treat high warning counts as a signal to re-import with a better parser rather than to add schema fields.
- **`extensions`** — ecosystem-specific fields that have no canonical equivalent. These are preserved verbatim and never read by the analysis tools. A field that migrates from `extensions.nixpkgs.X` into the top-level schema is a typical version-bump scenario.

## Known future candidates (not yet in schema)

These fields appear in `unmapped` or `extensions` across real records and may be promoted in a future version:

| Field | Ecosystem | Notes |
|-------|-----------|-------|
| `outputs` | nixpkgs | Multi-output derivations (dev, lib, doc, etc.) |
| `passthru` | nixpkgs | Arbitrary attrs passed to dependents |
| `PKGORIGIN` | freebsd_ports | Category/portname, useful for deduplication |

---

## Z-Layer Behavioral Spec Schema

The behavioral spec system has its own schema, separate from the package recipe schema. It lives in `zspecs/schema/behavioral-spec.schema.json` and is also versioned.

| Version | Changes |
|---------|---------|
| 0.1 | Initial schema. Defines `identity`, `provenance`, `library`, `constants`, `types`, `functions`, `invariants`, `wire_formats`, `error_model`. Invariant `kind` enum covers 30 execution patterns across ctypes, python_module, cli, and node backends. |

The Z-spec schema uses `additionalProperties: true` on most sub-objects so that spec authors can annotate invariants with `rfc_reference`, `skip_if`, or other metadata without requiring a schema bump. A bump is needed only if the `kind` enum, required invariant fields, or required top-level fields change.

When adding a new invariant `kind`:
1. Add it to the `kind` enum in `zspecs/schema/behavioral-spec.schema.json`.
2. Add it to `KNOWN_KINDS` in `tools/verify_behavior.py` and `tools/validate_zspec.py` (kept in sync by comment).
3. Implement a `_<kind>` handler method in `PatternRegistry`.
4. Write tests in the appropriate `tests/test_verify_behavior_*.py` file.
