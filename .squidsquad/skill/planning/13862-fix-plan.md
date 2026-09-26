# Fix plan -- #13862

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

This install's vault is still v1-shaped. Survey of 185 notes before M1:

- 165 notes carry `confidence`/`source`, and 132 carry `links`.
- 43 owner labels have drifted (`skill`, `skill-lead`, `dm-lead`, ...).
- 37 notes carry Claude-memory `name`/`description`/`metadata` keys.
- 11 notes lack status or owner; 22 lack `updated`; 2 lack tags; 1 is a `style-*` note.
- `.relevance-index.json` still exists.
- There are 54 dangling wikilinks, mostly to Claude-memory `feedback_*` names and doc/sub-skill names.

No tool existed to migrate any of this (VAULT-ARCH 10).

## Intended direction

- `references/scripts/vault_migrate.py` is the product-feature tool. It is deterministic, idempotent, dry-runnable, and runs against `--vault <dir>`. Commands:
  - `inventory` (M0);
  - `transform` (M1: 4.3 frontmatter, owner -> class, fills, style->pattern with redirect map and link rewrite, relevance index removed, changelog line citing #13862);
  - `apply-manifest` (M3: prune = `status: archived`, merge = `superseded` plus the target's merged draft, hub links, new hubs, link fixes, tag adds; nothing deleted; an invalid manifest is refused whole);
  - `reconcile` (M3 gates: M0 count = sum of dispositions, `vault_check` validate, zero broken links).
- Rehearsal first (10.1): the full M0 -> M1 -> M2 -> apply -> reconcile walk ran on a scratch copy. It PASSED: 185 = 170 keep + 5 merge + 10 prune, validate clean, zero broken links.
- M2 was produced by 5 sonnet subagents, one per topical cluster, under the aggressive directive. The manifest adds 3 new hubs (verification, delivery, agent-runtime) and extends the 7 existing hub knowledge maps. It is filed for operator review (M3 HITL). Live M1 and M3 apply run only after approval.
- Out of scope here: M4 (compose default flip, v1 machinery deletion, `references/migrations/` entry, #13854 doc reconciliation).

## Impact

- M0 freezes vault writes (`Vault Remember > Writes Per Cycle: 0` on main) until M4 unfreezes them. Capture-at-ship and end-of-cycle vault writes pause for all agents during the operator review.
- The live vault is untouched until the manifest is approved. The script is new; it has no callers, so there is no runtime change.

## Vault context consumed

- [[learning-atomic-migration-strategy]] -- live M1 + M3 apply land as one atomic step after approval, under the write freeze, never a half-migrated vault
- [[learning-git-merge-silently-drops-concurrent-large-edit-on-shared-markdown]] -- the freeze exists because concurrent note edits on main would be silently lost against the migration branch
- [[decision-vault-subagent-model-sonnet]] -- M2 distillation subagents pinned to sonnet
- [[learning-tests-must-not-mutate-shared-live-state]] -- tests and rehearsal run on tmp/scratch vaults only

## Applicable rules

- None matched (searched rules lane: vault, migration, git)
