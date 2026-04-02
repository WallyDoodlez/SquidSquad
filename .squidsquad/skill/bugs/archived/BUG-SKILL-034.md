## BUG-SKILL-034 — Statusline shows DM health icon even when DM is not present

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: After FEAT-SKILL-035, DM is treated as always present — statusline shows 3 health icons, config has `DM: always present`, and `dm/` directory is created unconditionally. But DM is optional (BUG-033). The `.squidsquad/dm/` directory is the sole presence indicator — no config flag needed. Fix requires multiple changes:
  1. `statusline.sh`: check `dm/` directory exists before showing DM health icon
  2. FEAT-035 setup/upgrade flow in `SKILL.md`: only create `dm/` directory when user opts in (not hardcoded/unconditional)
  3. Config template: only add `DM` line to agents section when `dm/` is created during setup
  4. `references/agent-instructions.md` PM template: health check Step 7 should only check DM heartbeat if `dm/` exists
- **Steps to Reproduce**:
  1. Run PM agent without opting into DM during setup
  2. Observe status bar — shows 3 icons instead of 2
- **Expected**: Only PM and dev agent icons shown when `dm/` directory doesn't exist
- **Actual**: DM icon shown regardless of DM presence

### Discussion

> [2026-03-30 13:15] **pm/qa**: Filed from human report. Human sees 3 health icons but doesn't have DM enabled. statusline.sh needs to check DM presence before rendering its icon — same dm/ directory check as the PM Delivery Fallback.
> [2026-03-30 13:30] **pm/qa**: Human clarified: dm/ directory IS the presence indicator. No config flag needed. If dm/ exists, DM is enabled. If not, DM doesn't exist. Setup creates dm/ when user opts in. Removed dm/ directory and config entry since human hasn't opted in. statusline.sh and all DM-aware code should use dm/ directory check. Config `DM: always present` line should only be added by setup when dm/ is created.
> [2026-03-31 00:10] **skill-lead**: Fixed all 4 items: (1) statusline.sh already conditionally checks dm/ dir — confirmed correct. (2) SKILL.md upgrade flow now conditional — only creates/updates DM artifacts if dm/ already exists, no unconditional creation. (3) Config — PM already removed DM entry. (4) PM Step 7 and agent-instructions.md Template 3 description updated from "hardcoded, always present" to "optional, present when dm/ exists". Status → Fixed.
> [2026-03-31 00:30] **pm/qa**: Verified — statusline checks `[ -d "$SQDIR/dm" ]` before including DM. Setup/upgrade conditional. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
