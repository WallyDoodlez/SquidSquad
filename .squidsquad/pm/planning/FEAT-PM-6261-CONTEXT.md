# FEAT-PM-6261 Context — Fixed Team Architecture

## Scope

Codify the fixed team (PM+QA+DM+workers) into the architecture. Merge tracker-protocol into L1. Strip all role-absence fallback logic. DM skips QA and routes merge conflicts back to dev.

## Locked Decisions (human decided)

- **Fixed team**: PM + QA + DM + technical workers. Always present. No optional roles, no fallback logic.
- **Tracker-protocol into L1**: Inline directly into `references/roles/instructions.md`. No separate file, no include directive. ~140 lines added to base.
- **DM skips QA entirely**: DM goes in-progress → pending-ship directly. DM never needs QA verification.
- **DM merge conflict → route back to dev**: On PR merge failure, DM transitions item back to in-progress and comments. Dev agent resolves the conflict.
- **delivery-fallback.md deleted entirely**: No stubs, no redirects. Clean deletion.
- **tracker-protocol.md deleted after merge**: Content moves to L1, old file removed in same commit.
- **Tracker-protocol sub-skill is universal and stable**: It should never change — that's why it belongs in L1, not as a swappable sub-skill.

## Dev Discretion (dev agent can choose)

- How to structure the tracker-protocol content within L1 (section ordering, markdown headers)
- Whether to keep PM's pending-test authority or remove it (research recommends keeping as coordination backstop)
- How config.py handles legacy PM/QA combined identity migration
- Whether to add a migration step to wizard.py or rely on compose.py's mandatory-role check

## Side Effect Mitigations (required)

- Run `compose.py deploy-all` after all template changes — mandatory-role check enforces fixed team at composition time
- Update config.py to stop synthesizing QA from PM/QA legacy string
- Verify event contracts still derive correctly after tracker-protocol moves from L2 include to L1 inline
- All changes in one atomic commit to avoid mixed-state agents (per learning-atomic-migration-strategy)
- tracker.py: add in-progress → pending-ship to BOTH `LEGAL_TRANSITIONS` AND `ROLE_AUTHORITY` for dm-lead
- tracker.py: add dm to `ROLE_AUTHORITY` for pending-ship → in-progress (DM merge conflict rollback)
- installer-files.txt: remove deleted files (tracker-protocol.md, delivery-fallback.md) — `test_installer_wiring.py` will fail otherwise
- test_compose.py: update 6 locations that reference tracker-protocol fixtures/markers
- test_tracker_authority.py: update "combined PM/QA identity" comment
- manifest.md: remove 5 stale tracker-protocol references (composition order tables + file inventory)
- dm/issue-triage.md: DM bug fixes must route to pending-ship, not pending-test
- common/task-pickup.md: create DM-specific override (`roles/dm/task-pickup.md`) that transitions to pending-ship
- L4 project files: clean `.squidsquad/project/pm-instructions.md` (lines 19, 29) and `.squidsquad/project/dm-instructions.md` (line 34) of fallback language
- PM SOUL.md line 147: remove "If DM absent: PM is fallback reboot authority"
- boot_remote.py:128: update QA/DM detection to handle new config.md format
- add_role.py:63: remove DM directory existence check
- cycle_post.py:440: remove live `if not dm_dir.exists()` conditional in `_do_version_bump()`
- delivery-packaging.md: add explicit merge-fail handler (comment on issue + transition to in-progress)

## Upgrade Path (required)

- Stop all agents → git pull → compose.py deploy-all → start via harness
- Old config.md with "PM/QA" format: compose.py or config.py migration rewrites to separate entries
- Old composed CLAUDE.md with tracker-protocol include: compose.py will ERROR on deploy-all (old file deleted), forcing upgrade. Acceptable hard break.

## Out of Scope

- Changing tracker-protocol content itself (it's a move, not a rewrite)
- Removing PM's pending-test authority from tracker.py (kept as coordination backstop)
- Adding new roles or changing the worker role system
