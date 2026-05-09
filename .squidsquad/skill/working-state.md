# Working State

- **Task**: #6261
- **Status**: in-progress
- **Started**: 2026-05-09 02:33
- **Last Processed Event ID**: 1af4cc69

## Completed Steps
- AC-1: COMPLETE — tracker-protocol inlined into L1, source deleted, includes/manifest/installer cleaned
- AC-2: MOSTLY COMPLETE — fallback logic stripped from PM/QA instructions, cycle_pre, cycle_post, boot_remote, add_role, status-line, L4 project files, delivery-fallback renamed to delivery

## Remaining Steps
- AC-3: tracker.py LEGAL_TRANSITIONS + ROLE_AUTHORITY for DM skip-QA (in-progress → pending-ship for dm-lead, pending-ship → in-progress for dm)
- AC-4: DM delivery-packaging.md merge-fail handler
- AC-5: Config.py — remove legacy PM/QA combined string parsing
- AC-6: Test updates (test_compose tracker-protocol fixtures, test_tracker_authority, test_installer_wiring)
- AC-7: compose.py deploy-all validation, run full tests, self-review, atomic commit, PR

## Key Decisions
- Tracker-protocol content inlined into L1 with AC-3 state machine edges pre-applied
- delivery-fallback.md → delivery.md (same content, no fallback name)
- Entire PM CHANGELOG fallback branch removed from cycle_post.py
- boot_remote.py: unconditional roles.update({"pm", "qa", "dm"}) replaces conditional regex
- add_role.py: mandatory roles loop replaces DM dir check
