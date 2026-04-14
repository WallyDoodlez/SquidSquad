# QA Results: Issue #918 -- Agents Cannot Self-Restart

**Date**: 2026-04-13
**Verified by**: QA (manual review)
**Status**: PARTIAL PASS -- 1 finding

---

## Acceptance Criteria Verification

### AC1: Agent can trigger a restart by writing a .restart sentinel file
**Result**: PASS

The sub-skill at `references/sub-skills/common/self-restart.md` defines the sentinel mechanism clearly. The agent writes:
```bash
echo "[reason]" > .squidsquad/[ROLE]/.restart
```
The sub-skill specifies two restart triggers (context pressure, template change), a pre-restart checklist (save state, commit, update status bar, print message), and safety rules (cycle-end only, no uncommitted changes, max 3/hour rate limit).

### AC2: Shell script detects the sentinel and kills/restarts Claude
**Result**: PASS

Both boot script templates (`references/templates/start-role.sh` and `references/templates/start-role.ps1`) contain sentinel detection logic. After each Claude session exits, the script checks for `$RESTART_SENTINEL` / `$RestartSentinel`. If found, it reads the reason, deletes the sentinel, logs the restart to `restart-log.txt`, resets the restart counter, and immediately continues the loop (restarting Claude).

### AC3: Sentinel is deleted after restart (no infinite restart loop)
**Result**: PASS

Both scripts delete the sentinel immediately after detecting it:
- `.sh`: `rm -f "$RESTART_SENTINEL"` (line 126)
- `.ps1`: `Remove-Item $RestartSentinel -ErrorAction SilentlyContinue` (line 112)

Additionally, the sub-skill enforces a max 3 self-restarts per hour rate limit (tracked in `restart-log.txt`) to prevent infinite restart loops.

### AC4: working-state.md is saved before restart (context preserved)
**Result**: PASS

The pre-restart checklist in `self-restart.md` requires (step 1): "Save working state to `.squidsquad/[ROLE]/working-state.md`." Step 2 requires committing and pushing all pending changes. Step 1c of the Ralph Loop (Resume From Working State) reads this file on startup.

### AC5: Works on both Windows (.ps1) and Unix (.sh) boot scripts
**Result**: PASS

Both template files contain identical sentinel detection logic. Verified in:
- `references/templates/start-role.ps1` (lines 55, 108-119)
- `references/templates/start-role.sh` (lines 48, 124-134)

Deployed instances also verified:
- `.squidsquad/start-qa.ps1` (lines 55, 108-119)
- `.squidsquad/start-qa.sh` (lines 48, 124-134)

### AC6: Context pressure step uses the new mechanism instead of "exit"
**Result**: PARTIAL PASS -- finding below

The **common** `context-pressure.md` sub-skill (used by dev/skill roles via `includes.yml`) was correctly updated. It now says: "Continue the cycle normally. Set a flag so the Self-Restart step (at cycle end) triggers a fresh session after the cycle completes." This replaces the old "exit the conversation" behavior.

**Finding**: The PM, QA, DM, and Designer role templates have **inline** context-pressure sections (not using the common sub-skill) that still say "Exit the conversation." These were NOT updated:
- `references/roles/pm/CLAUDE.md` line 89
- `references/roles/qa/CLAUDE.md` line 91
- `references/roles/dm/CLAUDE.md` line 90
- `references/roles/designer/CLAUDE.md` line 90

The deployed `.squidsquad/qa/CLAUDE.md` (line 297) also still says "Exit the conversation." This means QA, PM, DM, and Designer agents will still try to "exit" rather than using the sentinel-based self-restart for context pressure. The self-restart sub-skill IS included in these roles (verified below), but the context-pressure trigger path still points to the old "exit" behavior rather than setting a flag for self-restart.

**Severity**: Medium. The self-restart sub-skill is present and works for the template-change trigger, but the most common trigger (context pressure) is broken for 4 of 5 roles.

### AC7: Template change detection triggers reboot (optional per issue)
**Result**: PASS

The self-restart sub-skill lists as trigger #2: "Template change: If `.squidsquad/[ROLE]/CLAUDE.md` mtime is newer than the session start time, trigger a restart to pick up updated instructions."

---

## Additional Checks

### All 5 role templates include self-restart
**Result**: PASS

All 5 `includes.yml` files contain `common/self-restart`:
- `references/roles/dev/includes.yml` -- line 23
- `references/roles/pm/includes.yml` -- line 26
- `references/roles/qa/includes.yml` -- line 17
- `references/roles/dm/includes.yml` -- line 19
- `references/roles/designer/includes.yml` -- line 19

### Deployed templates include self-restart content
**Result**: PASS

Verified in deployed CLAUDE.md files:
- `.squidsquad/qa/CLAUDE.md` -- lines 592-625 contain the full self-restart sub-skill
- `.squidsquad/skill/CLAUDE.md` -- lines 776-809 contain the full self-restart sub-skill

### Cycle-end-only enforcement
**Result**: PASS

The sub-skill explicitly states: "Never restart mid-cycle -- complete the full Ralph Loop first" and "Never write `.restart` mid-cycle -- only after the cycle-complete marker." In the role templates, the self-restart step appears immediately before the "Step N -- Done" step, ensuring it runs at cycle end.

### Boot scripts in this clone have restart detection
**Result**: PASS

Both `.squidsquad/start-qa.ps1` and `.squidsquad/start-qa.sh` contain the full sentinel detection loop, matching the reference templates.

---

## Summary

| Criteria | Status |
|----------|--------|
| AC1: Sentinel file mechanism | PASS |
| AC2: Boot script detection | PASS |
| AC3: Sentinel cleanup / loop prevention | PASS |
| AC4: Working state saved before restart | PASS |
| AC5: Windows + Unix support | PASS |
| AC6: Context pressure uses new mechanism | PARTIAL -- 4 roles still say "exit" |
| AC7: Template change trigger | PASS |

**Overall**: 6/7 PASS, 1 PARTIAL.

**Open finding**: The inline context-pressure sections in PM, QA, DM, and Designer role templates need to be updated to match the common sub-skill behavior (checkpoint + continue + flag for self-restart at cycle end) instead of "Exit the conversation."
