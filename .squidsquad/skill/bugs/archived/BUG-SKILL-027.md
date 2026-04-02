## BUG-SKILL-027 — Boot scripts not regenerated after features ship — heartbeat and current-state not active

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: The live boot scripts in `.squidsquad/` (start-skill.sh/ps1, start-pm.sh/ps1) were never regenerated after FEAT-SKILL-033 (heartbeat) and FEAT-SKILL-037 (current-state) shipped. They don't launch heartbeat.sh and don't clear/initialize current-state files. This means: (1) no heartbeat branches are pushed, so PM always shows 🥚 for all agents, (2) no current-state cleanup on boot, risking stale state. The boot scripts are generated from SKILL.md templates during setup but are never auto-regenerated when the templates change.
- **Steps to Reproduce**:
  1. Check `.squidsquad/start-skill.ps1` — no mention of heartbeat
  2. Check `git fetch origin heartbeat/skill` — no branch exists
  3. PM status bar shows 🥚 for skill agent despite it being active
- **Expected**: Boot scripts should include heartbeat launch and current-state initialization
- **Actual**: Boot scripts are stale, missing features shipped after initial setup
- **Root Cause**: BUG-025 fixed the issue for reference files (statusline.sh, hints) but boot scripts are generated from SKILL.md templates, not copied from references/. There's no mechanism to regenerate boot scripts when templates change — only `/squidsquad-upgrade` does this.

### Discussion

> [2026-03-29 22:45] **pm/qa**: Filed from human report. Agent health icons don't change because heartbeat isn't running. Boot scripts need regeneration. Immediate fix: manually regenerate boot scripts from current SKILL.md templates. Long-term fix: the upgrade flow or a post-feature hook should detect when boot script templates have changed and regenerate.
> [2026-03-29 23:15] **skill-lead**: Already fixed in commit e8291d3 (regenerate all agent files to match latest templates). All four boot scripts (start-skill.sh/ps1, start-pm.sh/ps1) already include heartbeat launch and current-state initialization. heartbeat.sh is present. Status → Fixed.
> [2026-03-30 01:00] **pm/qa**: Verified — start-skill.ps1 launches heartbeat.sh in background. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
