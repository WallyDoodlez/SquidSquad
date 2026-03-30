# FEAT-SKILL-044 Test Plan — Granular Status Phases

## Test Cases

### TC-1: PM agent writes `researching` phase with item name
- **Precondition**: PM agent is running Phase 1 (Research) for a feature (e.g. FEAT-SKILL-035)
- **Steps**: Trigger Feature Intake Phase 1. Observe the `echo` command that writes to `.squidsquad/pm/current-state`.
- **Expected**: File contains `researching|Researching FEAT-SKILL-035...` (or similar wording with the item ID included)
- **Verification**: `cat .squidsquad/pm/current-state` shows `researching|...FEAT-SKILL-035...`

### TC-2: PM agent writes `discussing` phase with item name
- **Precondition**: PM agent is running Phase 2 (Discussion) for a feature
- **Steps**: Trigger Feature Intake Phase 2. Observe the current-state write.
- **Expected**: File contains `discussing|Discussion for FEAT-SKILL-XXX...` with the actual feature ID
- **Verification**: `cat .squidsquad/pm/current-state` shows `discussing|...FEAT-...`

### TC-3: PM agent writes `test-planning` phase with item name
- **Precondition**: PM agent is running Phase 3 (Planning/Test Plan) for a feature
- **Steps**: Trigger Feature Intake Phase 3. Observe the current-state write.
- **Expected**: File contains `test-planning|Test plan for FEAT-SKILL-XXX...` with the actual feature ID
- **Verification**: `cat .squidsquad/pm/current-state` shows `test-planning|...FEAT-...`

### TC-4: PM `verifying` phase includes item name
- **Precondition**: PM agent is in Step 5 (Verify Fixed Bugs) with BUG-SKILL-029 marked Fixed
- **Steps**: PM runs verification cycle. Observe current-state write during per-item verification.
- **Expected**: File contains `verifying|Verifying BUG-SKILL-029...` (per-item, not batch summary)
- **Verification**: `cat .squidsquad/pm/current-state` includes the specific bug ID

### TC-5: PM `planning` phase includes item name for non-intake planning
- **Precondition**: PM agent is doing general planning work on a feature (e.g. writing feature entry)
- **Steps**: Observe current-state write during Step 6 or general planning.
- **Expected**: File contains `planning|FEAT-SKILL-XXX intake...` or similar with item ID
- **Verification**: `cat .squidsquad/pm/current-state` includes the feature ID

### TC-6: Dev agent `implementing` phase includes item name
- **Precondition**: Dev agent picks up FEAT-SKILL-037 in Step 3
- **Steps**: Dev agent begins implementation. Observe current-state write.
- **Expected**: File contains `implementing|🔨 FEAT-SKILL-037...`
- **Verification**: `cat .squidsquad/skill/current-state` shows the feature ID

### TC-7: Dev agent `triaging` phase includes item name
- **Precondition**: Dev agent is in Step 2, triaging BUG-SKILL-029
- **Steps**: Dev agent begins bug triage. Observe current-state write.
- **Expected**: File contains `triaging|Fixing BUG-SKILL-029...` or similar with the bug ID
- **Verification**: `cat .squidsquad/skill/current-state` shows the bug ID

### TC-8: Per-item status updates during batch verification
- **Precondition**: PM has 3 bugs in Fixed status (BUG-SKILL-028, BUG-SKILL-029, BUG-SKILL-030)
- **Steps**: PM runs Step 5. Observe current-state writes across the batch.
- **Expected**: current-state is updated per-bug, not once for the batch. Each write includes the specific bug ID being verified at that moment.
- **Verification**: Monitor `.squidsquad/pm/current-state` during the loop; it should cycle through each bug ID sequentially

### TC-9: Long item name truncation (edge case)
- **Precondition**: A feature has a very long title, e.g. `FEAT-SKILL-099 — Extremely long feature title that exceeds sixty characters by a significant margin`
- **Steps**: Agent writes current-state for this feature during implementation.
- **Expected**: Description is truncated to <=60 characters. Truncation uses `...` suffix. The item ID (FEAT-SKILL-099) is preserved even after truncation.
- **Verification**: `cat .squidsquad/[role]/current-state` — description length <=60 chars; item ID is present

### TC-10: Phase without specific item (edge case)
- **Precondition**: Agent is in `pulling` phase (git pull) or `health` phase (agent health check) — no specific item
- **Steps**: Agent writes current-state during Step 1 (Pull) or Step 7 (Health).
- **Expected**: These phases remain as-is (e.g. `pulling|Syncing with remote...`, `health|Checking agent health...`). No item ID is required since these are not item-specific operations.
- **Verification**: `cat .squidsquad/[role]/current-state` shows generic description without a forced item ID

### TC-11: Unknown phase fallthrough in statusline.sh (edge case)
- **Precondition**: statusline.sh is running; `current-state` contains a new phase value like `researching`
- **Steps**: Write `echo "researching|Researching FEAT-SKILL-044..." > .squidsquad/pm/current-state` and run statusline.sh
- **Expected**: statusline.sh does not crash or produce an error. The description text ("Researching FEAT-SKILL-044...") is displayed with the `🚧` prefix on line 2. The phase value itself is only used for hint rotation fallback, and unknown phases gracefully fall through to idle hints.
- **Verification**: `echo '{}' | bash references/statusline.sh` — output includes line 2 with `🚧 Researching FEAT-SKILL-044...`

### TC-12: statusline.sh hint fallback for new phases with empty description
- **Precondition**: `current-state` contains `researching|` (new phase, empty description)
- **Steps**: Run statusline.sh
- **Expected**: Since description is empty, statusline attempts to find hints for `researching` phase. No matching hints exist in hints-pm.txt. Falls through to idle hints. No crash.
- **Verification**: `echo "researching|" > .squidsquad/pm/current-state && echo '{}' | bash references/statusline.sh` — shows idle hint or empty line 2, no errors

### TC-13: `idle|` phase still works after changes (regression)
- **Precondition**: Agent writes `idle|` at cycle end (existing behavior)
- **Steps**: Write `echo "idle|" > .squidsquad/skill/current-state` and run statusline.sh
- **Expected**: Rotating idle hints display correctly on line 2
- **Verification**: `echo '{}' | bash references/statusline.sh` — shows a `💡` hint line

### TC-14: Existing `pulling` phase still works (regression)
- **Precondition**: Agent writes `pulling|Syncing with remote...` (existing behavior)
- **Steps**: Write the value and run statusline.sh
- **Expected**: Line 2 shows `🚧 Syncing with remote...`
- **Verification**: Output includes the description with `🚧` prefix

### TC-15: Existing `planning` phase still works (regression)
- **Precondition**: PM agent writes `planning|FEAT-SKILL-037 intake...` (existing behavior, now with item name)
- **Steps**: Write the value and run statusline.sh
- **Expected**: Line 2 shows `🚧 FEAT-SKILL-037 intake...`
- **Verification**: Output includes the description

### TC-16: Dev template CLAUDE.md lists new phase vocabulary (if applicable)
- **Precondition**: Dev agent template in `references/agent-instructions.md` (Template 1)
- **Steps**: Read the template's "Status bar state" section.
- **Expected**: Phase list includes any new dev-specific phases (if added), or existing phases remain if only PM gets new values. All examples include item IDs in descriptions.
- **Verification**: `grep "Phase is one of" references/agent-instructions.md` — check both dev and PM sections

### TC-17: PM template CLAUDE.md lists new phase vocabulary
- **Precondition**: PM agent template in `references/agent-instructions.md` (Template 2)
- **Steps**: Read the PM template's "Status bar state" section.
- **Expected**: Phase list includes `researching`, `discussing`, `test-planning` as valid phases. Examples show item IDs in descriptions.
- **Verification**: `grep -A5 "Phase is one of" references/agent-instructions.md` — PM section includes new phases

### TC-18: agent-instructions.md examples updated
- **Precondition**: `references/agent-instructions.md` exists
- **Steps**: Search for status write examples in Feature Intake phases.
- **Expected**: Phase 1 uses `researching|...`, Phase 2 uses `discussing|...`, Phase 3 uses `test-planning|...` (not all `planning|...`)
- **Verification**: `grep "current-state" references/agent-instructions.md` — distinct phase values per intake phase

### TC-19: Live PM CLAUDE.md updated to match template
- **Precondition**: `.squidsquad/pm/CLAUDE.md` is the live PM instructions
- **Steps**: Compare phase vocabulary in live file vs template.
- **Expected**: Live file includes `researching`, `discussing`, `test-planning` in its phase list and examples
- **Verification**: `grep "Phase is one of" .squidsquad/pm/CLAUDE.md` — includes new phases

### TC-20: Live dev CLAUDE.md updated to match template
- **Precondition**: `.squidsquad/skill/CLAUDE.md` is the live dev instructions
- **Steps**: Compare phase vocabulary and examples in live file vs template.
- **Expected**: Examples include item IDs in descriptions (e.g. `triaging|Fixing BUG-SKILL-029...`)
- **Verification**: `grep "echo.*current-state" .squidsquad/skill/CLAUDE.md` — examples include item names

## Smoke Tests
- [ ] Write `researching|Researching FEAT-SKILL-044...` to pm/current-state, run statusline.sh — no crash, line 2 shows description
- [ ] Write `discussing|Discussion for FEAT-SKILL-044...` to pm/current-state, run statusline.sh — no crash, line 2 shows description
- [ ] Write `test-planning|Test plan for FEAT-SKILL-044...` to pm/current-state, run statusline.sh — no crash, line 2 shows description
- [ ] Write `idle|` to pm/current-state, run statusline.sh — rotating hints still work
- [ ] Write `implementing|🔨 FEAT-SKILL-037...` to skill/current-state, run statusline.sh — no crash
- [ ] `grep "researching" references/agent-instructions.md` returns matches in PM template
- [ ] `grep "discussing" references/agent-instructions.md` returns matches in PM template
- [ ] `grep "test-planning" references/agent-instructions.md` returns matches in PM template
- [ ] Phase list in PM template includes all 10 phases: `pulling`, `checkin`, `testing`, `verifying`, `planning`, `health`, `idle`, `researching`, `discussing`, `test-planning`

## Regression Risks
- **statusline.sh hint file mismatch**: If `hints-pm.txt` or `hints-dev.txt` does not have entries for new phases, the hint fallback to idle kicks in. This is safe but means new phases never get custom hints. Not a breakage, but a polish gap.
- **Pipe delimiter in item names**: If a feature title somehow contains `|`, the `cut -d'|'` parsing in statusline.sh will split incorrectly. Mitigation: item IDs (FEAT-SKILL-XXX) never contain pipes, so the ID will always be in field 2. Risk is low but worth noting.
- **Existing agents on old templates**: Agents running with cached old CLAUDE.md will keep writing old phase values (`planning` instead of `researching`). This is safe because statusline.sh treats all non-empty descriptions the same way (shows them with `🚧`). The upgrade path is restart-based, which is documented in CONTEXT.md.
- **Description length overflow**: If dev writes a description longer than 60 chars, statusline.sh truncates at 58. If the item ID is at the end of the string, truncation could cut it off. Mitigation: put item ID at the start of descriptions (e.g. `FEAT-SKILL-044 doing stuff...` not `doing stuff for FEAT-SKILL-044`).
- **Empty description + unknown phase**: A write like `researching|` (empty description) for a phase with no hints falls through to idle hints. This is correct behavior but could confuse if someone expects phase-specific hints for `researching`. Not a bug — just a gap until hints are added.
- **PM CLAUDE.md size growth**: Adding 3 new phases to the phase list and updating examples increases template size slightly. No functional risk but worth noting for context window pressure.
