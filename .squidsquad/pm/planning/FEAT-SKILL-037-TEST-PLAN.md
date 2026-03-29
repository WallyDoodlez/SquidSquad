# FEAT-SKILL-037 Test Plan — Status Bar Step Display + Rotating Hints

## Happy Path Tests

### T1: State file written at each Ralph Loop step
- **Preconditions**: Agent template in `references/agent-instructions.md` includes `current-state` write instructions. Agent role directory exists (e.g. `.squidsquad/skill/`).
- **Steps**:
  1. Read `references/agent-instructions.md` and locate each `[squid]` step marker in Template 1 (Dev) and Template 2 (PM/QA).
  2. Confirm that each step marker is followed by a line writing to `.squidsquad/[ROLE]/current-state`.
  3. Confirm the write uses the format `echo "$(date +%s)|<step_id>|<display_text>" > .squidsquad/[ROLE]/current-state`.
- **Expected**: Every `[squid]` step marker has a corresponding current-state write. Step IDs are unique per step. Display text includes an emoji and human-readable description.
- **Verify**: `grep -c 'current-state' references/agent-instructions.md` should match the number of step markers. Manually confirm format consistency.

### T2: Idle state written at cycle end
- **Preconditions**: Agent template includes cycle-end logic.
- **Steps**:
  1. Read `references/agent-instructions.md` and locate the cycle-end / "Done" step in each template.
  2. Confirm it writes `$(date +%s)|idle|` to `current-state`.
- **Expected**: At cycle end, the state file contains `idle` as the step_id and an empty display_text field.
- **Verify**: Search for `|idle|` in the template. Confirm it appears at the logical end of the loop.

### T3: Statusline reads current-state and displays step text
- **Preconditions**: `references/statusline.sh` contains line 2 logic. A sample `current-state` file exists with a recent timestamp and non-empty display text.
- **Steps**:
  1. Read `references/statusline.sh` and locate the section that reads `current-state`.
  2. Confirm it uses `IFS='|' read` or equivalent to parse timestamp, step_id, and display_text.
  3. Confirm that when display_text is non-empty, it is shown on line 2.
- **Expected**: Line 2 displays the display_text from `current-state` when an active step exists.
- **Verify**: Read `references/statusline.sh` and trace the logic from file read to output. Confirm the variable holding display_text is used in the line 2 printf/echo.

### T4: Rotating hints displayed when idle
- **Preconditions**: Hint pool file exists at `references/hints-pm.txt` (or `hints-dev.txt`). State file contains `idle` step_id or does not exist.
- **Steps**:
  1. Read `references/statusline.sh` and locate the hint selection logic.
  2. Confirm it reads the hint pool file from `.squidsquad/templates/hints-<role>.txt`.
  3. Confirm it uses a modulo calculation based on timestamp / 60 seconds to select a hint line.
  4. Confirm it outputs the selected hint on line 2.
- **Expected**: When no active step, line 2 shows a hint that rotates every 60 seconds.
- **Verify**: Read the awk/sed logic in `statusline.sh`. Confirm the modulo divisor is 60 (or `INTERVAL * 60`). Confirm the hint count is used as the modulo base.

### T5: Phase-aware hint sub-pool selection
- **Preconditions**: Hint pool file contains `@section` headers (e.g. `@qa`, `@planning`). State file contains a step_id that maps to a section.
- **Steps**:
  1. Read `references/statusline.sh` hint logic.
  2. Confirm it extracts the step_id from `current-state`.
  3. Confirm it matches step_id against `@section` headers in the hint pool.
  4. Confirm that matching yields only lines from that section; non-matching falls back to the general pool (lines before any `@` header).
- **Expected**: `step5` or `step6` selects hints from `@qa` section. `step2` selects from `@planning`. Unknown step_ids fall back to general pool.
- **Verify**: Read the awk pattern in `statusline.sh`. Check section-to-step mapping against the research doc's rules.

### T6: Health icons moved to line 1
- **Preconditions**: `references/statusline.sh` previously showed health icons on line 2 for PM.
- **Steps**:
  1. Read `references/statusline.sh` and locate health icon rendering.
  2. Confirm health icons (squid/ghost/egg per agent) appear in line 1 output, right-aligned.
  3. Confirm line 2 no longer contains health icon variables.
- **Expected**: Line 1 shows role, health icons, context percentage, countdown. Line 2 is fully dedicated to step/hint text.
- **Verify**: Trace the line 1 and line 2 printf/echo statements. Confirm health icon variables are only referenced in line 1.

### T7: Hint pool files exist with correct format
- **Preconditions**: Feature implementation is complete.
- **Steps**:
  1. Read `references/hints-pm.txt`.
  2. Read `references/hints-dev.txt`.
  3. Confirm each file has: comment lines starting with `#`, general hints (before any `@` header), and at least one `@section` with contextual hints.
  4. Confirm no blank lines are treated as hints (parser skips them).
- **Expected**: PM file has general hints + `@qa`, `@planning`, `@health` sections. Dev file has general hints + `@bugs`, `@features`, `@testing` sections. Each section has 2-3 hints minimum.
- **Verify**: `grep -c '^@' references/hints-pm.txt` shows expected section count. `grep -v '^#' references/hints-pm.txt | grep -v '^@' | grep -v '^$' | wc -l` counts total hints.

### T8: Step text truncation at 60 characters
- **Preconditions**: `references/statusline.sh` includes truncation logic.
- **Steps**:
  1. Read `references/statusline.sh` and locate the display_text output section.
  2. Confirm there is a length check against 60 characters.
  3. Confirm that text exceeding 60 chars is cut and `...` is appended.
- **Expected**: Display text longer than 60 characters is truncated to 57 chars + "...".
- **Verify**: Search for `60` or truncation logic in `statusline.sh`. Confirm the cut + append pattern.

### T9: SKILL.md updated with new files
- **Preconditions**: Feature implementation is complete.
- **Steps**:
  1. Read `SKILL.md` and locate the structure diagram.
  2. Confirm `references/hints-pm.txt` and `references/hints-dev.txt` appear in the diagram.
  3. Confirm Step 4 (setup copy list) includes copying hint pool files to `.squidsquad/templates/`.
  4. Confirm the upgrade agent scope mentions hint pool files.
- **Expected**: All new files are documented. Setup and upgrade paths reference them.
- **Verify**: `grep 'hints-' SKILL.md` returns matches in structure diagram, setup steps, and upgrade scope.

### T10: Gitignore updated
- **Preconditions**: Feature implementation is complete.
- **Steps**:
  1. Read `.gitignore`.
  2. Confirm `.squidsquad/*/current-state` (or equivalent pattern) is listed.
- **Expected**: Current-state files are excluded from git tracking.
- **Verify**: `grep 'current-state' .gitignore` returns a match.

## Edge Case Tests

### T-E1: Missing current-state file (first boot / pre-upgrade)
- **Preconditions**: No `.squidsquad/<role>/current-state` file exists.
- **Steps**:
  1. Read `references/statusline.sh` and trace the logic when `current-state` does not exist.
  2. Confirm it uses `[ -f ... ]` or equivalent existence check.
  3. Confirm it falls through to hint display (or shows nothing if hints also missing).
- **Expected**: No error output. Line 2 shows a rotating hint or is blank. No bash errors or broken formatting.
- **Verify**: Confirm the file existence guard in `statusline.sh`. Check there are no unguarded `cat` or `read` calls on the state file.

### T-E2: Stale current-state file (agent crashed)
- **Preconditions**: `current-state` file exists with a timestamp older than 2x the loop interval (e.g. >10 minutes old).
- **Steps**:
  1. Read `references/statusline.sh` and locate the staleness detection logic.
  2. Confirm it compares the file's embedded timestamp against `$(date +%s)`.
  3. Confirm that if the difference exceeds the staleness threshold, the step display is suppressed and hints are shown instead.
- **Expected**: A stale state file is treated as "no active step". Line 2 falls through to hints.
- **Verify**: Search for staleness/threshold logic in `statusline.sh`. Confirm the comparison uses the timestamp field (field 1) from the pipe-delimited format.

### T-E3: Empty current-state file
- **Preconditions**: `current-state` file exists but is 0 bytes.
- **Steps**:
  1. Read `references/statusline.sh` and check for a `[ -s ... ]` (non-empty) guard.
  2. Confirm that an empty file triggers the same fallback as a missing file.
- **Expected**: Empty file = no active step. Falls through to hints.
- **Verify**: Confirm `[ -s ... ]` or equivalent non-empty check is present alongside `[ -f ... ]`.

### T-E4: Missing hint pool file
- **Preconditions**: No `hints-<role>.txt` exists in `.squidsquad/templates/` (e.g. partial upgrade or deleted by user).
- **Steps**:
  1. Read `references/statusline.sh` and trace the hint loading logic when the file does not exist.
  2. Confirm it guards with `[ -f "$HINT_FILE" ]`.
  3. Confirm that a missing hint file results in line 2 being blank or showing a hardcoded fallback hint.
- **Expected**: No bash errors. Line 2 is blank or shows a single fallback message. No broken formatting.
- **Verify**: Confirm file existence check before hint file read. Check if a fallback hint string is defined.

### T-E5: Hint pool file with only comments and blank lines
- **Preconditions**: Hint pool file exists but contains only `#` comment lines and blank lines (no actual hints).
- **Steps**:
  1. Read the awk/parsing logic in `statusline.sh`.
  2. Confirm that after filtering comments and blanks, a zero-hint result is handled.
  3. Confirm no division-by-zero in the modulo calculation when hint count is 0.
- **Expected**: Zero hints = line 2 is blank. No arithmetic errors.
- **Verify**: Check for `HINT_COUNT -gt 0` guard before the modulo line in `statusline.sh`.

### T-E6: Very long step description exceeding 60 chars
- **Preconditions**: Agent writes a step like `Implementing FEAT-SKILL-033 — Heartbeat system with background orphan branch pushes` (82 chars).
- **Steps**:
  1. Read truncation logic in `statusline.sh`.
  2. Confirm the output is cut to 60 characters total (57 visible + "...").
- **Expected**: Output: `Implementing FEAT-SKILL-033 — Heartbeat system with back...` (60 chars).
- **Verify**: Count characters in the truncation logic. Confirm the `...` suffix is appended correctly.

### T-E7: Pipe character in display text (format corruption)
- **Preconditions**: A step description inadvertently contains a `|` character.
- **Steps**:
  1. Read the `IFS='|' read` parsing in `statusline.sh`.
  2. Confirm what happens if the display_text field contains a pipe — does it split into extra fields?
- **Expected**: The research doc states pipes should not appear in step descriptions. The agent templates should not produce them. If one does appear, only the text before the pipe is shown (graceful degradation, not a crash).
- **Verify**: Review all step description strings in `references/agent-instructions.md` to confirm none contain `|`.

### T-E8: Exiting state display
- **Preconditions**: Agent writes `$(date +%s)|exiting|Context pressure — restarting...` to `current-state`.
- **Steps**:
  1. Confirm `statusline.sh` does not treat `exiting` as a special case that suppresses display.
  2. Confirm the display text "Context pressure — restarting..." appears on line 2.
- **Expected**: The exiting message is displayed like any other step until the timestamp goes stale.
- **Verify**: Read `statusline.sh` and confirm `exiting` step_id is not filtered out. Confirm staleness detection will eventually clear it after the agent stops.

## Regression Tests

### T-R1: PM line 1 content unchanged (except health icon addition)
- **Preconditions**: Current `references/statusline.sh` produces line 1 with role, context percentage, and countdown.
- **Steps**:
  1. Read `references/statusline.sh` line 1 output.
  2. Confirm role emoji/name, context percentage, and countdown timer are still present.
  3. Confirm health icons are now also on line 1 (new addition per D1).
  4. Confirm no existing line 1 content was removed.
- **Expected**: Line 1 retains all previous content plus gains health icons. No information loss.
- **Verify**: Compare line 1 printf/echo against the pre-feature version (check git diff of `references/statusline.sh`).

### T-R2: Rest nudge still appears
- **Preconditions**: PM line 2 previously showed a rest nudge right-aligned.
- **Steps**:
  1. Read `references/statusline.sh` and search for rest nudge logic.
  2. Confirm rest nudge is still rendered — either on line 1 (moved with health icons) or line 2 (alongside step/hint text).
- **Expected**: Rest nudge behavior is preserved. It may have moved position but is not removed.
- **Verify**: `grep -i 'rest' references/statusline.sh` returns matches. Trace the output to confirm it reaches the displayed line.

### T-R3: Statusline still works without .squidsquad/config.md
- **Preconditions**: `statusline.sh` has always guarded against missing config.
- **Steps**:
  1. Read `statusline.sh` and confirm the new current-state and hint-reading code does not introduce unguarded dependencies on `config.md`.
- **Expected**: If `config.md` is missing, statusline degrades gracefully (as before). New code paths do not add new hard dependencies.
- **Verify**: Trace all file reads in `statusline.sh` and confirm each has existence guards.

### T-R4: Dev agent single-line statusline not broken
- **Preconditions**: Dev agents previously had single-line status bars.
- **Steps**:
  1. Read `references/statusline.sh` and check dev-agent branch.
  2. Confirm line 1 for dev agents still works as before.
  3. Confirm line 2 is a new addition (step/hint), not a replacement of line 1 content.
- **Expected**: Dev agent line 1 is unchanged. Line 2 is purely additive.
- **Verify**: Read the role-conditional logic in `statusline.sh`. Confirm dev-agent line 1 output matches pre-feature behavior.

### T-R5: Heartbeat system unaffected
- **Preconditions**: FEAT-SKILL-033 heartbeat pushes to orphan branches and `statusline.sh` reads them for health icons.
- **Steps**:
  1. Read `references/statusline.sh` heartbeat reading logic.
  2. Confirm it is unchanged or only moved (from line 2 to line 1 per D1).
  3. Confirm no new code interferes with heartbeat branch reads.
- **Expected**: Heartbeat system continues to function. Health icons still reflect agent liveness.
- **Verify**: `grep -i 'heartbeat\|health' references/statusline.sh` returns expected matches. Logic is intact.

### T-R6: Quiet cycle behavior preserved
- **Preconditions**: PM Ralph Loop skips logging and committing on quiet cycles.
- **Steps**:
  1. Read `references/agent-instructions.md` PM template.
  2. Confirm quiet cycle detection is unchanged.
  3. Confirm that `current-state` writes still happen during quiet cycles (steps run, they just find nothing to do — per research doc).
- **Expected**: Quiet cycles still skip iteration logging and commits. State file writes occur normally during the scan steps.
- **Verify**: Read the quiet cycle logic in the template. Confirm it gates on QA issues/bugs/features/input, not on state file writes.

### T-R7: Working-state.md format unchanged
- **Preconditions**: `working-state.md` is a separate persistent file for context pressure exits.
- **Steps**:
  1. Confirm `current-state` and `working-state.md` are clearly separate files with different purposes.
  2. Confirm no code confuses or merges them.
- **Expected**: `working-state.md` format and usage is unchanged. `current-state` is a new, separate ephemeral file.
- **Verify**: `grep 'working-state' references/agent-instructions.md` returns the same references as before. No new conflation with `current-state`.

## Upgrade Tests

### T-U1: Upgrade copies hint pool files to templates directory
- **Preconditions**: Existing install with `.squidsquad/templates/` directory but no `hints-*.txt` files. Upgrade runs via `/squidsquad-upgrade`.
- **Steps**:
  1. Read `SKILL.md` upgrade agent scope or `references/agent-instructions.md` upgrade section.
  2. Confirm the settings upgrade agent copies `references/hints-pm.txt` and `references/hints-dev.txt` to `.squidsquad/templates/`.
- **Expected**: After upgrade, `.squidsquad/templates/hints-pm.txt` and `.squidsquad/templates/hints-dev.txt` exist.
- **Verify**: Check the upgrade agent instructions for hint file copy commands. Confirm both files are listed.

### T-U2: Upgrade regenerates statusline.sh
- **Preconditions**: Existing install with old `statusline.sh` (no current-state reading or hint logic).
- **Steps**:
  1. Confirm the settings upgrade agent already copies `references/statusline.sh` to `.squidsquad/statusline.sh`.
  2. Confirm this existing behavior is sufficient — no additional upgrade step needed for statusline.
- **Expected**: The upgraded `statusline.sh` includes all new logic (state file reading, hint pool, line 2 display, truncation, staleness detection).
- **Verify**: Read upgrade agent instructions. Confirm `statusline.sh` copy is in scope.

### T-U3: Upgrade regenerates agent instruction templates
- **Preconditions**: Existing install with old agent templates (no `current-state` write instructions).
- **Steps**:
  1. Confirm the dev-role and PM/QA upgrade agents regenerate templates from `references/agent-instructions.md`.
  2. Confirm this existing behavior picks up the new `current-state` write lines.
- **Expected**: After upgrade, agent CLAUDE.md files include current-state writes at each step marker.
- **Verify**: Read upgrade agent instructions. Confirm template regeneration is in scope for all roles.

### T-U4: Upgrade adds current-state to .gitignore
- **Preconditions**: Existing `.gitignore` does not contain `current-state` pattern.
- **Steps**:
  1. Read upgrade instructions or SKILL.md setup steps.
  2. Confirm the upgrade appends `.squidsquad/*/current-state` to `.gitignore` if not already present.
- **Expected**: After upgrade, `current-state` files are gitignored.
- **Verify**: Check upgrade agent instructions for `.gitignore` update logic. Confirm idempotent append (does not duplicate if already present).

### T-U5: Graceful behavior during partial upgrade (old agent, new statusline)
- **Preconditions**: `statusline.sh` is upgraded (reads `current-state`) but agent templates are not yet regenerated (no `current-state` writes).
- **Steps**:
  1. Read `references/statusline.sh` and confirm it handles missing `current-state` file gracefully (T-E1).
  2. Confirm that in this state, line 2 shows rotating hints (since no state file is written).
- **Expected**: No errors. Hints display immediately. Step display activates once agents are restarted with new templates.
- **Verify**: This is covered by T-E1. Confirm the same guards apply.

### T-U6: Graceful behavior during partial upgrade (new agent, old statusline)
- **Preconditions**: Agent templates are upgraded (write `current-state`) but `statusline.sh` is not yet upgraded (does not read it).
- **Steps**:
  1. Confirm that writing `current-state` files has no side effects if nothing reads them.
  2. Confirm old `statusline.sh` does not error on the presence of new files it does not know about.
- **Expected**: `current-state` files are written but ignored. Old statusline displays as before. No errors.
- **Verify**: The `echo ... > file` write is fire-and-forget. Old `statusline.sh` never references these files, so no conflict.

### T-U7: Boot script clears stale current-state on restart
- **Preconditions**: A `current-state` file exists from a previous crashed session.
- **Steps**:
  1. Read the boot/start scripts (e.g. `start-skill.sh`, `start-pm.sh` or equivalent referenced in SKILL.md).
  2. Confirm `rm -f .squidsquad/$ROLE/current-state` is present early in the boot sequence.
  3. Confirm the agent then writes `Initializing...` as its first state (per D5).
- **Expected**: Stale state is cleared before agent launches. First visible state is "Initializing...".
- **Verify**: `grep 'current-state' references/start-*.sh` or equivalent boot script. Confirm `rm -f` and initial write are present.
