# FEAT-PM-329 Test Plan — Consistent Per-Cycle Reporting

## Test Cases

### TC-1: Active cycle log via cycle.py for Skill role (happy path)
- **Precondition**: `cycle.py log-iteration` updated with unified format. Skill role iterations directory exists.
- **Steps**:
  1. Run `python references/scripts/cycle.py log-iteration skill 1 --issues "#10, #12" --tasks "#15" --notes "Fixed auth bug"`
  2. Read the created `iter-1.md` file.
- **Expected**: File contains unified format with Date, Cycle Number (1), Type (active), Work Summary bullets listing issues and tasks, and Notes. No role-specific fields (no "Issues Fixed" / "Tasks Progressed" / "Tests" old fields).
- **Verification**: `cat .squidsquad/skill/iterations/iter-1.md` — confirm fields match: Date (YYYY-MM-DD HH:MM), Type: active, Work Summary with bullet content, Notes.

### TC-2: Active cycle log via cycle.py for PM role
- **Precondition**: PM iterations directory exists.
- **Steps**:
  1. Run `python references/scripts/cycle.py log-iteration pm 5 --issues "#20" --tasks "none" --notes "Verified 3 items"`
  2. Read `iter-5.md`.
- **Expected**: Same unified format as TC-1. No PM-specific fields (no "Human Check-in", "Agent Health", "E2E Tests").
- **Verification**: `cat .squidsquad/pm/iterations/iter-5.md` — confirm unified format, Type: active.

### TC-3: Active cycle log via cycle.py for QA role
- **Precondition**: QA iterations directory exists.
- **Steps**:
  1. Run `python references/scripts/cycle.py log-iteration qa 3 --issues "#8" --tasks "#9" --notes "Filed 2 bugs"`
  2. Read `iter-3.md`.
- **Expected**: Unified format. No QA-specific fields (no "Tasks Verified", no old QA structure).
- **Verification**: `cat .squidsquad/qa/iterations/iter-3.md` — confirm unified format.

### TC-4: Active cycle log via cycle.py for DM role
- **Precondition**: DM iterations directory exists.
- **Steps**:
  1. Run `python references/scripts/cycle.py log-iteration dm 2 --issues "none" --tasks "#30" --notes "Delivered v0.8.0"`
  2. Read `iter-2.md`.
- **Expected**: Unified format. No DM-specific fields (no "Features Delivered", "Version Bumped").
- **Verification**: `cat .squidsquad/dm/iterations/iter-2.md` — confirm unified format.

### TC-5: Active cycle log via cycle.py for Designer role
- **Precondition**: Designer iterations directory exists.
- **Steps**:
  1. Run `python references/scripts/cycle.py log-iteration designer 4 --issues "none" --tasks "#22, #25" --notes "Completed mockups"`
  2. Read `iter-4.md`.
- **Expected**: Unified format. No Designer-specific fields (no "Designs Progressed", "Designs Completed", "Quiet Cycles" counter).
- **Verification**: `cat .squidsquad/designer/iterations/iter-4.md` — confirm unified format.

### TC-6: Quiet cycle log via cycle.py (condensed entry)
- **Precondition**: Skill role iterations directory exists.
- **Steps**:
  1. Run quiet-cycle variant of `log-iteration` (e.g., `python references/scripts/cycle.py log-iteration skill 7 --quiet` or equivalent based on dev's chosen CLI interface — may also detect from empty work summary).
  2. Read `iter-7.md`.
- **Expected**: Condensed 2-3 line entry containing Date, Type: quiet, and a one-line note (e.g., "No approved tasks available"). NOT a full format with all fields set to "none".
- **Verification**: `cat .squidsquad/skill/iterations/iter-7.md` — confirm file exists, is 2-3 lines of content, contains "Type: quiet" or equivalent marker.

### TC-7: Quiet cycle log for PM role
- **Precondition**: PM iterations directory exists.
- **Steps**:
  1. Run quiet-cycle variant: `python references/scripts/cycle.py log-iteration pm 10 --quiet` (or equivalent).
  2. Read `iter-10.md`.
- **Expected**: Condensed 2-3 line quiet entry with date and Type: quiet.
- **Verification**: `cat .squidsquad/pm/iterations/iter-10.md` — confirm condensed format.

---

## Edge Case Test Cases

### TC-8: vault_remember.py is_quiet() detects quiet cycle from file content
- **Precondition**: A quiet-cycle iter file exists (created within the iteration interval window) at `.squidsquad/skill/iterations/iter-7.md` with Type: quiet marker.
- **Steps**:
  1. Create a quiet iter file using cycle.py (as in TC-6) with mtime within the iteration interval.
  2. Run `python references/scripts/vault_remember.py is-quiet skill`.
- **Expected**: Exit code 0 (quiet). The function reads iter file content and finds Type: quiet, returning quiet despite a recent mtime.
- **Verification**: `python references/scripts/vault_remember.py is-quiet skill; echo $?` — must print "quiet" and exit 0.

### TC-9: vault_remember.py is_quiet() detects active cycle from file content
- **Precondition**: An active-cycle iter file exists (created within the iteration interval window) with Type: active marker.
- **Steps**:
  1. Create an active iter file using cycle.py (as in TC-1).
  2. Run `python references/scripts/vault_remember.py is-quiet skill`.
- **Expected**: Exit code 1 (non-quiet). The function reads iter file content and finds Type: active.
- **Verification**: `python references/scripts/vault_remember.py is-quiet skill; echo $?` — must print "non-quiet" and exit 1.

### TC-10: vault_remember.py is_quiet() with no iterations directory
- **Precondition**: No iterations directory for the role.
- **Steps**:
  1. Ensure `.squidsquad/testrole/iterations/` does not exist.
  2. Run `python references/scripts/vault_remember.py is-quiet testrole`.
- **Expected**: Exit code 0 (quiet) — no iter files means quiet.
- **Verification**: Exit code 0, prints "quiet".

### TC-11: vault_remember.py is_quiet() with only old iter files (beyond interval window)
- **Precondition**: Iter files exist but all have mtime older than the iteration interval.
- **Steps**:
  1. Create iter files and set their mtime to 2 hours ago.
  2. Run `python references/scripts/vault_remember.py is-quiet skill`.
- **Expected**: Exit code 0 (quiet) — no recent iter file, regardless of content.
- **Verification**: Exit code 0, prints "quiet".

### TC-12: Mixed old-format and new-format iter files in same directory
- **Precondition**: Directory contains old-format files (pre-change, with "Issues Fixed" fields) and new-format files (unified format with Type field).
- **Steps**:
  1. Manually place an old-format iter file (`iter-1.md` with PM-specific fields).
  2. Create a new-format iter file via cycle.py (`iter-2.md`).
  3. Run `python references/scripts/vault_remember.py is-quiet pm`.
- **Expected**: is_quiet() only checks the most recent file within the interval window. Old-format files without a Type field should be treated as active (non-quiet) since they were only written for active cycles in the old system.
- **Verification**: Verify is_quiet returns correct result based on the most recent file's content.

### TC-13: Iter file numbering — no gaps after quiet cycles
- **Precondition**: Empty iterations directory.
- **Steps**:
  1. Log active cycle: `cycle.py log-iteration skill 1 --issues "#5" --tasks "none"`
  2. Log quiet cycle: `cycle.py log-iteration skill 2 --quiet`
  3. Log active cycle: `cycle.py log-iteration skill 3 --issues "#6" --tasks "none"`
- **Expected**: Files exist: `iter-1.md`, `iter-2.md`, `iter-3.md`. No numbering gaps. Quiet cycles do not skip numbers.
- **Verification**: `ls .squidsquad/skill/iterations/` — all three files present with sequential numbering.

### TC-14: Iteration number as non-numeric input
- **Precondition**: cycle.py available.
- **Steps**:
  1. Run `python references/scripts/cycle.py log-iteration skill abc --issues "none" --tasks "none"`.
- **Expected**: Script prints error ("iteration number must be numeric") and exits with code 1. No file created.
- **Verification**: Check exit code is 1 and no `iter-abc.md` file exists.

### TC-15: Suppressed cycle does not write an iteration log
- **Precondition**: PM working-state.md contains `**Phase**: researching FEAT-PM-329`.
- **Steps**:
  1. Observe that the PM Ralph Loop Step 1c detects the planning phase flag.
  2. Check that the cycle skips Step 8 (Log Iteration) entirely.
- **Expected**: No new iter file created for suppressed cycles. Suppressed cycles are distinct from quiet cycles.
- **Verification**: Count files in iterations directory before and after suppressed cycle — count unchanged.

---

## Side Effect Regression Tests

### TC-16: Iter file cleanup still works with more files (>20)
- **Precondition**: Create 25 iter files (mix of active and quiet) in `.squidsquad/skill/iterations/`.
- **Steps**:
  1. Create iter-1.md through iter-25.md using cycle.py.
  2. Run `python references/scripts/cycle.py cleanup-iterations skill --keep 20`.
- **Expected**: 5 oldest files removed. 20 most recent files retained. Both active and quiet iter files are treated equally by cleanup (mtime-based sorting, not content-based).
- **Verification**: `ls .squidsquad/skill/iterations/ | wc -l` — should be 20. Verify the 5 oldest (by mtime) are gone.

### TC-17: Cleanup with --keep flag still respects custom values
- **Precondition**: 15 iter files exist.
- **Steps**:
  1. Run `python references/scripts/cycle.py cleanup-iterations skill --keep 10`.
- **Expected**: 5 oldest removed, 10 retained.
- **Verification**: File count is 10.

### TC-18: vault_remember.py write-budget unaffected by format change
- **Precondition**: vault_remember.py available, working-state.md exists.
- **Steps**:
  1. Run `python references/scripts/vault_remember.py reset-writes skill`.
  2. Run `python references/scripts/vault_remember.py write-budget skill`.
- **Expected**: Returns budget count (default 2). Format change in iter files does not affect write-budget logic.
- **Verification**: Exit code 0, prints remaining budget.

### TC-19: Existing cycle.py commands unaffected (timestamp, step-marker, inc-counter, reset-counter)
- **Precondition**: cycle.py available.
- **Steps**:
  1. Run `python references/scripts/cycle.py timestamp` — expect YYYY-MM-DD HH:MM format.
  2. Run `python references/scripts/cycle.py timestamp-short` — expect HH:MM:SS format.
  3. Run `python references/scripts/cycle.py step-marker "Test step"` — expect formatted marker.
  4. Run `python references/scripts/cycle.py inc-counter skill` — expect counter increment.
  5. Run `python references/scripts/cycle.py reset-counter skill` — expect counter reset to 0.
  6. Run `python references/scripts/cycle.py is-quiet skill` — expect quiet/non-quiet check.
- **Expected**: All commands produce correct output. No regressions from log-iteration format change.
- **Verification**: Run each command, check exit code 0 and expected output format.

### TC-20: Old-format iter files are not corrupted or modified
- **Precondition**: Place an old-format PM iter file (with "Human Check-in", "Agent Health" fields) in iterations directory.
- **Steps**:
  1. Create a new iter file using updated cycle.py.
  2. Read the old iter file.
- **Expected**: Old file content unchanged. New file uses unified format. Both coexist without issues.
- **Verification**: `cat` both files — old file has original content, new file has unified format.

---

## Upgrade Verification Tests

### TC-21: compose.py deploy-all regenerates all CLAUDE.md files
- **Precondition**: Sub-skill templates updated (all 5 role-specific iteration-log.md files + common/iteration-log.md). compose.py available.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Read each generated CLAUDE.md: `.squidsquad/pm/CLAUDE.md`, `.squidsquad/qa/CLAUDE.md`, `.squidsquad/skill/CLAUDE.md` (and dm, designer if configured).
- **Expected**: All generated CLAUDE.md files reference cycle.py log-iteration for iteration logging. No role still contains inline format instructions with role-specific fields. All roles reference the unified format.
- **Verification**: `grep -c "cycle.py log-iteration" .squidsquad/*/CLAUDE.md` — each file should have at least one reference. `grep -c "Human Check-in\|Features Delivered\|Designs Progressed\|Tasks Verified" .squidsquad/*/CLAUDE.md` — should return 0 for iteration log sections (old fields gone from the logging instructions).

### TC-22: Deployed templates instruct quiet-cycle logging
- **Precondition**: compose.py deploy-all completed successfully.
- **Steps**:
  1. Read each role's CLAUDE.md iteration logging section.
- **Expected**: All roles instruct writing a quiet-cycle entry (via cycle.py) instead of "skip silently to Step N (Done)". The old "Produce no text output — skip silently" instruction is replaced.
- **Verification**: `grep -c "skip silently" .squidsquad/*/CLAUDE.md` — should return 0 in iteration log sections. Quiet cycle instructions should reference cycle.py with quiet flag/mode.

### TC-23: Existing installs with old templates gracefully degrade
- **Precondition**: An agent running old CLAUDE.md template (pre-change) that skips quiet cycles.
- **Steps**:
  1. Do NOT run compose.py deploy-all. Leave old templates in place.
  2. Agent runs a quiet cycle.
- **Expected**: Old behavior — no iter file created for quiet cycle. No crash, no error. Just inconsistency with agents that have new templates.
- **Verification**: Observe agent produces no iter file on quiet cycle (old behavior). No errors in output.

### TC-24: Post-upgrade, agents pick up new templates on restart
- **Precondition**: compose.py deploy-all has regenerated CLAUDE.md files. Agent session is running with old template.
- **Steps**:
  1. Agent detects CLAUDE.md mtime change (self-restart trigger in Ralph Loop).
  2. Agent restarts and loads new CLAUDE.md.
  3. Agent runs a quiet cycle.
- **Expected**: After restart, agent uses new template. Quiet cycle produces a condensed iter file via cycle.py.
- **Verification**: Check iterations directory — new quiet-cycle iter file exists after restart.

### TC-25: Sub-skill template references are consistent
- **Precondition**: All 5 role-specific sub-skill files updated + common/iteration-log.md.
- **Steps**:
  1. Diff each sub-skill file against the expected unified template.
  2. Verify all reference `cycle.py log-iteration` with same argument structure.
- **Expected**: All sub-skill templates produce identical cycle.py invocations (only role name differs). No template still uses inline format or role-specific fields.
- **Verification**: Read each file in `references/sub-skills/*/iteration-log.md` and confirm they share the same cycle.py command pattern.

---

## Smoke Tests

- [ ] `python references/scripts/cycle.py log-iteration skill 1 --issues "none" --tasks "none"` creates a file and exits 0
- [ ] `python references/scripts/cycle.py log-iteration pm 1 --quiet` creates a condensed file and exits 0
- [ ] `python references/scripts/vault_remember.py is-quiet skill` exits 0 or 1 without error
- [ ] `python references/scripts/compose.py deploy-all` completes without error
- [ ] Quiet-cycle iter file is visibly shorter than active-cycle iter file (2-3 lines vs full format)
- [ ] `python references/scripts/cycle.py cleanup-iterations skill` runs without error on an empty directory
- [ ] Active iter file contains "Type: active" (or equivalent marker)
- [ ] Quiet iter file contains "Type: quiet" (or equivalent marker)

---

## Regression Risks

- **vault_remember.py false non-quiet**: If is_quiet() is not updated to check content (still uses mtime only), every quiet cycle with a new iter file will be detected as non-quiet, causing vault-remember to run every cycle unnecessarily. This is the highest-severity regression risk.
- **Old-format iter files without Type field**: is_quiet() must handle iter files that lack a Type marker (from before the change). These should be treated as active (non-quiet) since old quiet cycles never wrote files.
- **Faster iter file accumulation**: Quiet agents now generate ~48 files/day at 30-min intervals. The 20-file cleanup handles this, but git history grows faster. Monitor repo size if many agents run idle for extended periods.
- **Step number references in templates**: Old templates reference specific step numbers for "skip silently to Step N". If unified templates use generic phrasing ("skip to the Done step"), verify no hardcoded step numbers remain that could confuse agents.
- **cycle.py CLI backward compatibility**: If the CLI interface changes (new flags, removed old flags), agents with cached/old command invocations could break. The `--bugs`/`--features` aliases in the current code suggest backward compat is a concern — verify old aliases still work or are cleanly removed.
- **Designer Quiet Cycles counter dropped**: The Designer role currently tracks consecutive quiet cycles. If the unified format drops this counter, verify no Designer-specific logic depends on parsing it from iter files (research says nothing parses iter content except vault_remember.py, so risk is low).
