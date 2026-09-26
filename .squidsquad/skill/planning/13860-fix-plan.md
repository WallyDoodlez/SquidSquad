# Fix plan -- #13860

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

Task, not a bug: PRD-VAULT-V2 P4 (S4.1-S4.5). The vault had an engine (P2/P3)
but no consumption contract. Agents grepped the vault, left no receipts, and
nothing enforced consultation or dedup at write time.

## Intended direction

The deterministic parts are scripts in `vault_consume.py`: the lineage file,
search, cite, the receipt gate, dedup via the 7.2 merge-target test, and
intake injection. Sub-skills call those scripts instead of carrying prose
procedures. There is a dedicated `rule` type lane. The git_ops guards exempt
only this issue's lineage file and additive capture-at-ship notes.

## Impact

All four roles' instructions change: implement-tasks, triage-issues, PM
task-intake, verifier verification, and vault-protocol/remember/optimize/
synthesis. Agents pick these up on reboot or recompose. Existing installs
keep their own `vault-schema.json`, because the wizard seeds it only when
absent, so they do not get the `rule` type or `dedupThreshold`. Without them
`dedup_threshold` falls back to 0.5 and the rules lane is empty. Adding them
to an existing install needs a migration entry, which is the DM release lane.

## Vault context consumed

- [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] -- the composed CLAUDE.md in this clone is built from unmerged branch source; restore it before task-end so it does not land on main early
- [[learning-git-merge-silently-drops-concurrent-large-edit-on-shared-markdown]] -- a clean merge can silently revert shared vault content; this is why capture notes are held to additive-only against the base tree
- [[decision-vault-remember-source-agnostic]] -- the capture-at-ship reflection stays source-agnostic (review findings count as signals)

## Applicable rules

- None matched (searched rules lane: vault, consumption, receipts, capture)
