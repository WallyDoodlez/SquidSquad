# FEAT-SKILL-058 Test Plan — Suppress PM Cycles During Planning

## Test Cases

### TC-1: Planning phase flag written on Phase 1 entry
- **Precondition**: PM working-state.md has `Task: none`, `Status: none`
- **Steps**: PM enters Phase 1 (Research) for any feature
- **Expected**: working-state.md updated with a planning phase indicator (e.g., `**Phase**: researching FEAT-SKILL-XXX`)
- **Verification**: `grep -i "phase" .squidsquad/pm/working-state.md` shows the active planning phase and feature ID

### TC-2: Planning phase flag written for Phase 2A, 2, and 3
- **Precondition**: PM working-state.md has no active planning flag
- **Steps**: PM enters Phase 2A (Discussion Prep), Phase 2 (Discussion), or Phase 3 (Test Planning) for a feature
- **Expected**: working-state.md updated with the corresponding planning phase indicator for each phase
- **Verification**: `grep -i "phase" .squidsquad/pm/working-state.md` shows the correct phase name each time

### TC-3: Suppressed cycle performs silent pull
- **Precondition**: working-state.md contains an active planning phase flag
- **Steps**: Cron triggers a new PM Ralph Loop cycle
- **Expected**: PM runs `git pull --rebase` during the suppressed cycle
- **Verification**: Git log shows the pull occurred (no merge conflicts or errors); cycle output contains the suppression marker line

### TC-4: Suppressed cycle performs health check
- **Precondition**: working-state.md contains an active planning phase flag
- **Steps**: Cron triggers a new PM Ralph Loop cycle
- **Expected**: PM checks agent health (stalled agent detection) during the suppressed cycle
- **Verification**: Health check logic executes without errors; no false "stalled agent" alerts

### TC-5: No tracker verification during suppressed cycle
- **Precondition**: working-state.md contains an active planning phase flag; a bug exists with status `Fixed` (would normally trigger verification)
- **Steps**: Cron triggers a PM cycle
- **Expected**: PM does NOT read bug/feature trackers, does NOT run verification, does NOT process any tracker items
- **Verification**: No verification Discussion entries appended; no status changes on any tracker items during the suppressed cycle

### TC-6: No iteration log during suppressed cycle
- **Precondition**: working-state.md contains an active planning phase flag
- **Steps**: Cron triggers a PM cycle
- **Expected**: No new `iter-N.md` file created in `.squidsquad/pm/iterations/`
- **Verification**: `ls .squidsquad/pm/iterations/` shows no new files after the suppressed cycle

### TC-7: Suppression marker printed
- **Precondition**: working-state.md contains an active planning phase flag
- **Steps**: Cron triggers a PM cycle
- **Expected**: PM prints a single-line marker matching the format: `[🦑] ---- cycle N (suppressed — active planning phase) ----`
- **Verification**: Scrollback contains exactly one cycle line with "suppressed" in it; no other step markers printed

### TC-8: Auto-resume after RESEARCH.md written
- **Precondition**: working-state.md contains a Phase 1 planning flag
- **Steps**: PM completes Phase 1 and writes `FEAT-SKILL-XXX-RESEARCH.md` to the planning directory
- **Expected**: Planning phase flag is cleared from working-state.md; next cron-triggered cycle runs a full Ralph Loop (all steps)
- **Verification**: working-state.md no longer contains a planning phase flag; next cycle output includes Step 2+ markers

### TC-9: Auto-resume after CONTEXT.md written
- **Precondition**: working-state.md contains a Phase 2 planning flag
- **Steps**: PM completes Phase 2 and writes `FEAT-SKILL-XXX-CONTEXT.md`
- **Expected**: Planning phase flag cleared; next cycle is a full cycle
- **Verification**: working-state.md has no planning phase flag; next cycle runs all steps

### TC-10: Auto-resume after TEST-PLAN.md written
- **Precondition**: working-state.md contains a Phase 3 planning flag
- **Steps**: PM completes Phase 3 and writes `FEAT-SKILL-XXX-TEST-PLAN.md`
- **Expected**: Planning phase flag cleared; next cycle is a full cycle
- **Verification**: working-state.md has no planning phase flag; next cycle runs all steps

### TC-11: Phase flag cleared on planning completion
- **Precondition**: working-state.md contains an active planning phase flag
- **Steps**: The corresponding planning artifact is written (any of RESEARCH.md, PHASE2-PREP.md, CONTEXT.md, TEST-PLAN.md)
- **Expected**: The planning phase line is removed or reset in working-state.md
- **Verification**: `grep -i "phase.*researching\|phase.*discussing\|phase.*test-planning" .squidsquad/pm/working-state.md` returns empty

### TC-12: Other agents unaffected during PM suppression
- **Precondition**: PM working-state.md contains an active planning phase flag; skill agent has approved features or open bugs
- **Steps**: Skill agent (or DM) cron cycle triggers
- **Expected**: Skill/DM agents run their full Ralph Loop — no suppression, no changes to behavior
- **Verification**: Skill agent iteration logs show normal cycle activity; skill working-state.md is not checked for PM planning flags

## Smoke Tests
- [ ] Set a planning phase flag manually in PM working-state.md, trigger a PM cycle, confirm suppressed output
- [ ] Clear the flag manually, trigger a PM cycle, confirm full cycle runs
- [ ] Run a skill agent cycle while PM is in planning — confirm skill is unaffected

## Regression Risks
- **Working state corruption**: Writing the planning phase flag must not clobber existing in-progress task state in working-state.md
- **Stuck suppression**: If artifact write fails or PM crashes mid-planning, the phase flag could persist indefinitely — watch for cycles that stay suppressed after planning should have completed
- **Health check gap**: If the suppressed health check is too silent, a stalled agent could go undetected longer than expected
- **Context pressure exit during planning**: PM must still honor Step 1b (context pressure exit) even during suppressed cycles — verify the flag is saved correctly across context resets
