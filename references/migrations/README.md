# SquidSquad migrations

Per-version migration files for the installer's **migration walk** (INSTALLER-ARCH §10).

This directory is **empty of migration files by design** until the first release that
breaks existing on-disk schema (config.md fields, `.squidsquad/project/` L4 files, vault
store shape, etc.). Until then the migration walk finds no files and is a no-op — existing
installs simply re-stamp the current version and continue.

## When to add a migration file

Add one **only** when a release changes existing on-disk state in a way the standard
install phases would not otherwise reconcile. If a release adds new scaffold paths only
(no change to existing content), **no migration file is needed** — the walk skips that
version step silently.

Writing migration files is the responsibility of whoever ships SquidSquad releases (for
this self-dev repo, L4 DM) — **operators on consuming installs never write them** (§10.5);
they consume them as part of the source pull during an installer re-run.

## File naming

One file per version step that breaks schema:

```
references/migrations/v<N-1>-to-v<N>.md
```

e.g. `v1.4-to-v1.5.md`. The walk (`wizard.py select_migration_chain`) parses the `from`
and `to` versions from the filename and applies, in version order, every file whose target
version is newer than the installed version and no newer than the installer version. A
version step with no file is skipped silently (§10.4).

## File format

Migration files are **prose for the installer's LLM to consume**, not structured rules.
A single file may mix **mechanical** changes (deterministic renames, additive defaults —
applied straight through) and **judgment-call** changes (slot retirements, rule re-routing —
the LLM surfaces options to the operator and waits for a choice). Example:

```markdown
# Migration: v1.4 → v1.5

## config.md changes

- The `Iteration_Interval` field was renamed to `Iteration Interval` (underscore → space).
  If the operator's config has the underscore form, change the key spelling, value
  untouched. Mechanical; apply deterministically.

## L4 changes

- The `## Vault` slot is now L1-exclusive (per #10372). If any L4 file has a `## Vault` H2,
  surface to the operator: "this rule no longer maps to anything in the new framework.
  Options: convert to `## Project Context` append, file as upstream feature request, or
  delete." Judgment call; await operator choice.
```

A migration file MUST NOT modify the `- **SquidSquad Version**:` stamp in config.md — the
installer stamps that itself after a successful walk (`wizard.py stamp-version`, §10 step 4).

## Three-gate application

Each migration file is applied under the §10 three-gate model (the WIZARD.md Step 0b
runbook drives this; the LLM applies prose, `wizard.py` only selects the chain):

1. **DeepSeek audit** — a deepseek-class model reviews the planned writes against the
   migration prose's stated intent (mechanical flagged if non-deterministic; judgment-call
   flagged if the option-surfacing dialog is missing).
2. **Mini-CQ** — one plain-language confirmation to the operator summarizing the file's
   changes; rejection aborts that step with no write.
3. **Compose dry-run** — `compose.py deploy-all --check` validates the migrated tree
   composes cleanly before any write.

A file's changes apply atomically (all or none). Failure at any gate aborts the walk
cleanly at that step; earlier steps' writes persist, the version stamp is **not** advanced,
and the next installer run resumes at the failed step.
