---
type: archive
tags: [shipped, briefing-graduate, historical]
created: 2026-05-25
updated: 2026-05-25
status: archived
confidence: high
source: observation
owner: pm
---

# Shipped items graduated from BRIEFING.md (pre 2026-05-19)

Graduated from `BRIEFING.md` Recently Shipped during the 2026-05-25 trim-or-graduate pass. The BRIEFING list had grown to 33 entries (well over the ~50-line BRIEFING target) — most entries below this line are individual bug fixes / test additions / dead-code removals that don't need ongoing visibility in the active context summary.

The strategic / structural ships stay in BRIEFING.md Recently Shipped; everything else lives here for audit.

## Graduated entries (chronological, oldest at bottom)

- #8916 L2 dev: mandate reading CONTEXT.md / TEST-PLAN.md (shipped)
- #8081 triage.py: datetime-parsed timestamp comparison replacing fragile string compare (shipped)
- #8082 scan_index.py: record_decision inserts file_coverage row on missing (shipped)
- #7794 PM prohibitions.md: replaced stale 'tracker files' references in PM, DM, installer (shipped)
- #7947 wizard.py: validate_interval — 20 parametrized tests added (shipped)
- #7948 wizard.py: Code Review Model default test coverage added (shipped)
- #7955 cycle_post.py: added 13 tests for _do_tracker_comments and _do_working_state_update (shipped)
- #7793 PM/QA ship counter double-counting — QA now owns counter authoritatively (shipped)
- #7879 squidsquad-upgrade.md: removed .claude/ from upgrade commit staging (shipped)
- #7890 config.md missing Code Review Model field — model_router code-review fix (shipped)
- #7491 compose/sync config.md contamination fix (shipped) — root cause of 10+ QA rejections
- #7285 config.py sync_agents() NameError fix (shipped)
- #7441 harness.py save_state race condition fix (shipped)
- #7440 cycle_post.py dead no-op str.replace (shipped)
- #7191 dev-instructions.md unscoped copy references (shipped)
- #7286 boot_remote.py AppleScript quoting fix (shipped)
- #7589 state_bus.py silent git commit failure (shipped)
- #7590 manifest.py redundant yaml import (shipped)
- #7618 vault_optimize.py lock TOCTOU (shipped)
- #7619 squidsquad_cli.py URLError swallowed (shipped)
- #7622 tc_coverage.py OSError handling (shipped)
- #7624 vault_remember.py decay_scan error handling (shipped)
- #7625 forgejo_setup.py dead code (shipped)
- #6597 deploy-all clone isolation fix (shipped)
- #5423 harness.py INTENT_STOPPED constant

## Why graduated (not deleted)

- Per VAULT-ARCH §5 BRIEFING trim-or-graduate rule: trimmed content moves to a vault note, never deleted.
- Git history of `.squidsquad/vault/BRIEFING.md` is also a valid audit trail for these entries.
- This file exists so a future cycle's `grep -r "<issue-number>" .squidsquad/vault/` finds the historical context without having to walk git log.

## Changelog

- 2026-05-25 — Created by pm-lead. Graduated 25 entries from BRIEFING.md Recently Shipped.
