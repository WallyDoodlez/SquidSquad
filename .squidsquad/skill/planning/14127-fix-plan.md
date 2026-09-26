# Fix plan -- #14127

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`wizard.install_vault_engine` step 4 seeds `.squidsquad/vault/vault-schema.json`
only when absent (`not schema.exists()`), so an existing install's schema is
frozen at whatever it was first seeded with. After #13858/#13860 the shipped
default (`references/vault-schema-default.json`) carries a `rule` type and a
`dedupThreshold`. An upgraded install gets neither: `vault_entity` refuses
`type: rule` and the rules lane consults an empty set.

## Intended direction

- Add `wizard.merge_vault_schema_defaults(schema, default)`: an additive merge
  that adds only absent top-level keys, absent `types` entries, and absent
  sub-keys of dict settings. It never changes a present value, never edits a
  user or overridden type, and rewrites the file only when something was added.
- Call it from the same step when the schema exists. An upgrade is a re-run of
  the same installer flow (INSTALLER-ARCH §2 commitment 3), so every upgrade
  runs it. A broken file is reported, never replaced.
- Document it in VAULT-ARCH §3.1 and in the existing v0.45.0-to-v0.46.0
  migration file. No new migration file, so installer-files.txt is unchanged
  (AC4).

## Impact

- `references/scripts/wizard.py` (installer), the docs above, and a new test
  file. Consuming installs pick it up on their next installer re-run. This
  repo's own vault is migrated by #13862 (frozen until M4), and this change
  does not touch it.

## Vault context consumed

- [[learning-atomic-migration-strategy]] -- the merge is idempotent and self-contained in one installer step; a re-run converges, nothing is left half-applied
- [[pattern-verify-new-shipped-file-in-installer-manifest]] -- no new shipped file (the merge lives in wizard.py, the note in the existing migration file), so the installer manifest needs no entry

## Applicable rules

- None matched (searched rules lane: vault, installer, schema, upgrade)
