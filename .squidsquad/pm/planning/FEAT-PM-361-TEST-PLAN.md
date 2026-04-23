# FEAT-PM-361 Test Plan -- Project-Adaptive Role Souls

## Test Cases

---

### Part A -- Setup-Time Seed

---

### TC-1: Wizard generates Project Adaptation per role from project intent

- **Precondition**: Fresh install. User has provided project intent (e.g., "Python FastAPI backend for enterprise SaaS"). Multiple roles selected (pm, dev, qa).
- **Steps**:
  1. Run the setup wizard through Steps 1-6.
  2. At Step 6b, wizard generates a `## Project Adaptation` section for each selected role.
  3. Review the generated sections in the Step 6 review screen.
- **Expected**:
  - Each role gets a distinct adaptation tailored to its function (PM gets planning lens, dev gets tech stack context, QA gets verification lens).
  - Adaptation text references the project intent terms (e.g., "FastAPI", "enterprise", "SaaS").
  - Each adaptation is under 40 lines.
- **Verification**:
  ```bash
  # Check each live SOUL.md has the section
  grep -l "## Project Adaptation" .squidsquad/*/SOUL.md
  # Check content is role-specific (not identical across roles)
  diff <(sed -n '/## Project Adaptation/,$ p' .squidsquad/pm/SOUL.md) \
       <(sed -n '/## Project Adaptation/,$ p' .squidsquad/skill/SOUL.md)
  # Verify line count per role
  sed -n '/## Project Adaptation/,$ p' .squidsquad/pm/SOUL.md | wc -l
  ```

### TC-2: Human reviews and edits each adaptation during setup

- **Precondition**: Wizard has generated adaptation sections for 3 roles. Review screen displayed.
- **Steps**:
  1. At the review screen, select [E]dit for one role's adaptation.
  2. Modify the adaptation text (e.g., change "enterprise SaaS" to "internal tooling").
  3. Confirm the edit.
  4. Accept all adaptations and proceed to scaffold.
- **Expected**:
  - The edited role's live SOUL.md contains the human's modified text, not the original generated text.
  - Other roles' adaptations remain as generated.
  - No error or overwrite on scaffold.
- **Verification**:
  ```bash
  grep "internal tooling" .squidsquad/pm/SOUL.md
  # Confirm other roles still have original text
  grep "enterprise" .squidsquad/skill/SOUL.md
  ```

### TC-3: Live SOUL.md gets adaptation section, source template untouched

- **Precondition**: Wizard has completed scaffold with adaptations.
- **Steps**:
  1. Check the live SOUL.md files under `.squidsquad/<role>/SOUL.md`.
  2. Check the reference templates under `references/roles/<role>/SOUL.md`.
- **Expected**:
  - Live SOUL.md files contain `## Project Adaptation` with generated content.
  - Reference templates contain only the `## Project Adaptation` placeholder (no generated content).
- **Verification**:
  ```bash
  # Live files have content after the header
  for role in pm skill qa; do
    lines=$(sed -n '/## Project Adaptation/,$ p' ".squidsquad/$role/SOUL.md" | wc -l)
    echo "$role live: $lines lines"
  done
  # Reference templates have only the placeholder
  for role in pm dev qa; do
    lines=$(sed -n '/## Project Adaptation/,$ p' "references/roles/$role/SOUL.md" | wc -l)
    echo "$role template: $lines lines (expect 1-3)"
  done
  ```

### TC-4: compose.py does not overwrite existing SOUL.md adaptations

- **Precondition**: Live SOUL.md files have `## Project Adaptation` sections with content. A template update is available.
- **Steps**:
  1. Modify a reference template (e.g., add a line to `references/roles/pm/SOUL.md` outside the adaptation section).
  2. Run `python references/scripts/compose.py deploy-all`.
  3. Check live SOUL.md files.
- **Expected**:
  - The `## Project Adaptation` section is preserved exactly as it was.
  - compose.py either skips SOUL.md entirely (current behavior) or merges while preserving the adaptation section.
- **Verification**:
  ```bash
  # Before compose: capture adaptation content
  sed -n '/## Project Adaptation/,$ p' .squidsquad/pm/SOUL.md > /tmp/before-adapt.txt
  python references/scripts/compose.py deploy-all
  # After compose: compare
  diff /tmp/before-adapt.txt <(sed -n '/## Project Adaptation/,$ p' .squidsquad/pm/SOUL.md)
  # Expect no diff
  ```

---

### Part B -- Runtime Enrichment

---

### TC-5: PM applies 5-category checklist to a task that triggers an update

- **Precondition**: Project is running. PM has at least one role with an existing adaptation. A new task introduces a new tech stack element (e.g., first Redis usage).
- **Steps**:
  1. File a task that mentions Redis for the first time in the project.
  2. PM processes the task in its Ralph Loop.
  3. PM evaluates the task against the 5-category checklist.
- **Expected**:
  - PM detects "Tech stack evolution" signal (category 2).
  - PM appends an entry to `vault/areas/role-adaptations.md` with a timestamp, signal category, and the adaptation text.
  - PM re-renders the affected role's `## Project Adaptation` section in live SOUL.md.
  - PM commits the changes.
- **Verification**:
  ```bash
  grep -i "redis" .squidsquad/vault/areas/role-adaptations.md
  grep -i "redis" .squidsquad/skill/SOUL.md
  git log --oneline -1  # Expect "chore: soul adaptation -- ..."
  ```

### TC-6: Normal task does not trigger an update (signal-driven, not periodic)

- **Precondition**: Project has stable adaptations. A routine bug fix task is filed (no new deliverable type, tech stack, domain vocab, quality preference, or user persona).
- **Steps**:
  1. File a routine bug fix task.
  2. PM processes the task.
- **Expected**:
  - PM evaluates the 5 categories and finds no new signal.
  - No entry appended to `role-adaptations.md`.
  - No changes to any SOUL.md.
- **Verification**:
  ```bash
  # Capture mtime before
  stat .squidsquad/vault/areas/role-adaptations.md
  # After PM cycle, check mtime is unchanged
  stat .squidsquad/vault/areas/role-adaptations.md
  ```

### TC-7: Signal-driven frequency -- ~1 per 10-20 tasks

- **Precondition**: 20 tasks have been filed. Mix of routine and novel tasks.
- **Steps**:
  1. Review `role-adaptations.md` entry count after 20 tasks.
- **Expected**:
  - Entry count is in the range of 1-5 (not 20, not 0).
  - Entries correspond to genuinely novel signals, not routine work.
- **Verification**:
  ```bash
  grep -c "^##\|^###\|Signal:" .squidsquad/vault/areas/role-adaptations.md
  ```

### TC-8: Silent update with audit trail, mentioned in check-in

- **Precondition**: PM detects a new signal (e.g., first data pipeline task).
- **Steps**:
  1. PM processes the task, detects the signal, updates adaptations.
  2. Observe PM's check-in output for the cycle.
- **Expected**:
  - PM does NOT ask for human approval before writing.
  - PM mentions the update in its check-in: "Updated dev soul: this project now includes data pipeline work."
  - `role-adaptations.md` has the new entry with timestamp.
  - Git history shows the commit.
- **Verification**:
  ```bash
  # Check iteration log mentions the update
  grep -i "soul\|adaptation" .squidsquad/pm/iterations/iter-*.md | tail -5
  git log --oneline --all -- .squidsquad/vault/areas/role-adaptations.md | head -5
  ```

### TC-9: Contradiction flagged for human resolution

- **Precondition**: Existing adaptation says "this project has no frontend work." A new task adds a React component.
- **Steps**:
  1. File a task that involves React frontend work.
  2. PM processes the task and detects the contradiction with existing adaptation.
- **Expected**:
  - PM does NOT silently overwrite the existing adaptation.
  - PM flags the contradiction to the human (e.g., in check-in or Discussion comment).
  - PM waits for human resolution before updating the adaptation.
  - `role-adaptations.md` does NOT get an automatic supersession entry.
- **Verification**:
  ```bash
  # Check that PM flagged it (in issue comment or iteration log)
  grep -i "contradict" .squidsquad/pm/iterations/iter-*.md | tail -3
  # Check role-adaptations.md was NOT modified
  git diff .squidsquad/vault/areas/role-adaptations.md
  ```

### TC-10: Human edits role-adaptations.md directly for rollback

- **Precondition**: PM has written 3 adaptation entries. One is incorrect.
- **Steps**:
  1. Human edits `vault/areas/role-adaptations.md` and marks the bad entry with `Status: reverted`.
  2. Human commits the edit.
  3. PM runs its next cycle.
- **Expected**:
  - PM detects the file has been modified (mtime changed).
  - PM re-renders the affected role's `## Project Adaptation` section excluding the reverted entry.
  - Live SOUL.md no longer contains the reverted content.
  - PM commits the re-rendered SOUL.md.
- **Verification**:
  ```bash
  grep "Status: reverted" .squidsquad/vault/areas/role-adaptations.md
  # Confirm the reverted content is gone from live SOUL.md
  grep "bad-inference-keyword" .squidsquad/skill/SOUL.md  # Expect no match
  git log --oneline -1  # Expect re-render commit
  ```

### TC-11: PM re-renders SOUL.md immediately after writing adaptations

- **Precondition**: PM detects a signal and appends to `role-adaptations.md`.
- **Steps**:
  1. PM writes the adaptation entry.
  2. Check timing of SOUL.md update relative to `role-adaptations.md` write.
- **Expected**:
  - Both files are updated in the same cycle, same commit.
  - There is no "lazy re-render" or deferred update.
- **Verification**:
  ```bash
  # Both files should appear in the same commit
  git log --oneline -1 --name-only -- .squidsquad/vault/areas/role-adaptations.md .squidsquad/*/SOUL.md
  ```

### TC-12: Atomic single commit for multi-role updates

- **Precondition**: A task introduces a new deliverable type (e.g., data pipeline) that affects dev, QA, and DM roles.
- **Steps**:
  1. PM detects the signal and determines it affects 3 roles.
  2. PM drafts adaptation entries for each role.
  3. PM writes all entries and re-renders all SOUL.md files.
- **Expected**:
  - All entries in `role-adaptations.md` share a common `Signal:` reference.
  - All affected SOUL.md files are updated.
  - Everything lands in a single commit.
- **Verification**:
  ```bash
  # Single commit with all changes
  git log --oneline -1
  git show --stat HEAD | grep -c "SOUL.md\|role-adaptations.md"
  # Expect 4 files: role-adaptations.md + 3 SOUL.md files
  ```

### TC-13: 40-line soft cap with consolidation

- **Precondition**: A role's `## Project Adaptation` section has grown to 42 lines (over the 40-line cap).
- **Steps**:
  1. PM writes an adaptation that pushes the section past 40 lines.
  2. PM detects the cap has been exceeded.
  3. PM triggers consolidation.
- **Expected**:
  - PM re-reads all non-reverted entries for the role from `role-adaptations.md`.
  - PM generates a consolidated summary (15-25 lines).
  - The `## Project Adaptation` section is replaced with the consolidated version.
  - Pre-consolidation entries in `role-adaptations.md` are marked `Status: consolidated`.
  - No information is lost -- key insights are preserved in the consolidated version.
- **Verification**:
  ```bash
  # Section is now under 40 lines
  sed -n '/## Project Adaptation/,$ p' .squidsquad/skill/SOUL.md | wc -l
  # Consolidated entries are marked
  grep -c "Status: consolidated" .squidsquad/vault/areas/role-adaptations.md
  ```

---

### Edge Cases

---

### TC-14: Empty project intent -- user skips intent during setup

- **Precondition**: Fresh install. User provides no project intent (skips or leaves blank).
- **Steps**:
  1. Run wizard with empty/blank project intent.
  2. Complete setup.
- **Expected**:
  - `## Project Adaptation` section in live SOUL.md contains a note: "No project intent provided -- PM will populate this as the project develops."
  - `config.md` has `Project Intent Description` field but it is empty.
  - PM's runtime enrichment works normally -- adaptations accumulate from task signals.
- **Verification**:
  ```bash
  grep "No project intent provided" .squidsquad/pm/SOUL.md
  grep "Project Intent Description" .squidsquad/config.md
  ```

### TC-15: Single-role install -- only PM installed

- **Precondition**: Install with only PM role (no dev, QA, DM, designer).
- **Steps**:
  1. Complete wizard with only PM.
  2. PM runs its cycle and detects a signal.
- **Expected**:
  - PM generates adaptation only for its own SOUL.md.
  - No errors about missing role directories.
  - `role-adaptations.md` contains only PM entries.
- **Verification**:
  ```bash
  ls .squidsquad/*/SOUL.md  # Only pm/SOUL.md should exist
  grep "Role:" .squidsquad/vault/areas/role-adaptations.md  # Only pm entries
  ```

### TC-16: Pre-existing customized SOUL.md -- hand edits preserved

- **Precondition**: Existing install where user has hand-edited SOUL.md (e.g., added custom content under `### Quality Bar`).
- **Steps**:
  1. Run upgrade that adds `## Project Adaptation` section.
  2. PM later writes an adaptation entry.
- **Expected**:
  - Hand edits in other sections (Professional Identity, Quality Bar, etc.) are untouched.
  - `## Project Adaptation` is appended at the end, clearly demarcated.
  - PM only modifies content within the `## Project Adaptation` section.
- **Verification**:
  ```bash
  # Check custom content still exists
  grep "my custom quality bar text" .squidsquad/pm/SOUL.md
  # Check adaptation section exists at end
  tail -20 .squidsquad/pm/SOUL.md | grep "## Project Adaptation"
  ```

### TC-17: Contradictory signals across time

- **Precondition**: Task #50 adaptation says "we never do frontend work." Task #75 adds a React component.
- **Steps**:
  1. PM processes task #75 and detects the contradiction.
- **Expected**:
  - PM does not silently overwrite.
  - PM notes the contradiction and flags it for human resolution.
  - Previous adaptation remains active until human resolves.
- **Verification**:
  ```bash
  # Both entries exist in role-adaptations.md
  grep -c "frontend" .squidsquad/vault/areas/role-adaptations.md  # Expect 2+ hits
  # PM flagged the contradiction
  grep -i "contradict" .squidsquad/pm/iterations/iter-*.md | tail -3
  ```

### TC-18: Missing role-adaptations.md -- graceful creation

- **Precondition**: Existing install. `vault/areas/role-adaptations.md` does not exist (never created or accidentally deleted).
- **Steps**:
  1. PM detects a signal that would trigger an adaptation update.
- **Expected**:
  - PM creates `vault/areas/role-adaptations.md` on first signal detection.
  - No error or crash.
  - The entry is written normally.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/areas/role-adaptations.md && echo "created" || echo "missing"
  ```

### TC-19: Consolidation preserves key insights

- **Precondition**: Role has 45 lines of adaptation across 8 entries covering tech stack, domain vocab, and quality preferences.
- **Steps**:
  1. PM triggers consolidation.
  2. Compare consolidated version against original entries.
- **Expected**:
  - All 5 categories that had entries are represented in the consolidated version.
  - No category is dropped entirely.
  - Consolidated version is 15-25 lines.
- **Verification**:
  ```bash
  # Check all key terms survived consolidation
  for term in "FastAPI" "tenant" "100% test coverage"; do
    grep -q "$term" .squidsquad/skill/SOUL.md && echo "$term: present" || echo "$term: MISSING"
  done
  ```

---

### Side Effect Regression Tests

---

### TC-20: compose.py deploy does not clobber SOUL.md

- **Precondition**: Live SOUL.md has `## Project Adaptation` with 20 lines of content.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy pm`.
- **Expected**: `## Project Adaptation` section is preserved exactly.
- **Verification**:
  ```bash
  md5sum .squidsquad/pm/SOUL.md  # Compare before and after
  ```

### TC-21: Vault-remember does not conflict with soul shepherd writes

- **Precondition**: PM runs a cycle where both vault-remember and soul shepherd trigger.
- **Steps**:
  1. PM's cycle has a task that triggers a soul adaptation AND a vault reflection.
  2. Both steps execute in the same cycle.
- **Expected**:
  - Both writes succeed.
  - No file locking conflict.
  - `role-adaptations.md` has the adaptation entry.
  - Vault galaxy/ has the reflection note.
  - Commit includes all changes.
- **Verification**:
  ```bash
  git show --stat HEAD  # Both role-adaptations.md and galaxy/ files present
  ```

### TC-22: Reference SOUL.md templates never modified by runtime enrichment

- **Precondition**: PM has been running for 10+ cycles with multiple adaptation updates.
- **Steps**:
  1. Check git log for any modifications to `references/roles/*/SOUL.md`.
- **Expected**: No commits modify reference templates. Only `.squidsquad/*/SOUL.md` is changed.
- **Verification**:
  ```bash
  git log --oneline -- references/roles/*/SOUL.md | head -5
  # Should show no commits from PM's soul shepherd step
  ```

### TC-23: Multi-clone agents pick up SOUL.md changes on next pull

- **Precondition**: PM updates skill's SOUL.md in PM's clone. Skill agent is running in a separate clone.
- **Steps**:
  1. PM commits and pushes the SOUL.md update.
  2. Skill agent runs its next cycle (Step 1: git pull --rebase).
- **Expected**:
  - Skill agent gets the updated SOUL.md.
  - Skill reads the updated SOUL.md on its next context reset/session start.
  - No merge conflict.
- **Verification**:
  ```bash
  # In skill's clone after pull
  grep "## Project Adaptation" .squidsquad/skill/SOUL.md
  ```

### TC-24: Existing tracker operations unaffected

- **Precondition**: PM is running with soul shepherd enabled. Normal issue/task lifecycle is in progress.
- **Steps**:
  1. File a task, transition through statuses, verify, ship.
- **Expected**: All tracker operations (create, transition, comment, close) work exactly as before. Soul shepherd step does not interfere.
- **Verification**:
  ```bash
  python references/scripts/tracker.py list-tasks skill --status shipped | head -5
  ```

---

### Upgrade Verification Tests

---

### TC-25: Existing install with customized SOUL.md -- upgrade path

- **Precondition**: Existing install. User has hand-edited `.squidsquad/pm/SOUL.md` with custom content. No `## Project Adaptation` section.
- **Steps**:
  1. Run `/squidsquad-upgrade`.
- **Expected**:
  - `## Project Adaptation` section appended at the end of SOUL.md.
  - All existing custom content preserved.
  - `Project Intent Description` added to config.md (empty default).
  - `vault/areas/role-adaptations.md` created (empty template).
- **Verification**:
  ```bash
  tail -5 .squidsquad/pm/SOUL.md | grep "## Project Adaptation"
  grep "Project Intent Description" .squidsquad/config.md
  test -f .squidsquad/vault/areas/role-adaptations.md && echo "exists"
  ```

### TC-26: Existing install with generic SOUL.md -- upgrade path

- **Precondition**: Existing install. SOUL.md is unmodified from template.
- **Steps**:
  1. Run `/squidsquad-upgrade`.
- **Expected**:
  - SOUL.md regenerated from template with `## Project Adaptation` placeholder.
  - If human provides project intent during upgrade, seed adaptation is generated.
  - If no intent provided, placeholder note added.
- **Verification**:
  ```bash
  grep "## Project Adaptation" .squidsquad/pm/SOUL.md
  ```

### TC-27: Fresh install -- full flow

- **Precondition**: No existing `.squidsquad/` directory.
- **Steps**:
  1. Run setup wizard with project intent provided.
  2. Complete all steps including adaptation review.
- **Expected**:
  - Live SOUL.md files have `## Project Adaptation` with generated content.
  - `config.md` has `Project Intent Description` populated.
  - `vault/areas/role-adaptations.md` exists (empty -- PM will populate at runtime).
  - BRIEFING.md includes project intent.
- **Verification**:
  ```bash
  grep "## Project Adaptation" .squidsquad/*/SOUL.md
  grep "Project Intent Description" .squidsquad/config.md
  test -f .squidsquad/vault/areas/role-adaptations.md && echo "exists"
  grep -i "intent\|purpose" .squidsquad/vault/BRIEFING.md
  ```

### TC-28: Missing role-adaptations.md -- graceful degradation on upgrade

- **Precondition**: Upgraded install where `vault/areas/role-adaptations.md` was not created (e.g., partial upgrade).
- **Steps**:
  1. PM starts its cycle. Checks for `role-adaptations.md`.
- **Expected**:
  - PM creates it on first signal detection.
  - No error or crash if the file is missing at boot.
  - PM still runs all other steps normally.
- **Verification**:
  ```bash
  # Delete the file, run PM cycle
  rm -f .squidsquad/vault/areas/role-adaptations.md
  # After PM cycle with a signal
  test -f .squidsquad/vault/areas/role-adaptations.md && echo "recreated"
  ```

### TC-29: Non-upgraded install -- graceful degradation

- **Precondition**: Install that has NOT been upgraded. No `## Project Adaptation` section in SOUL.md. No `role-adaptations.md`.
- **Steps**:
  1. PM runs its normal cycle.
- **Expected**:
  - PM skips the soul shepherd step entirely.
  - No errors, no crashes.
  - All other PM functionality works normally.
- **Verification**:
  ```bash
  # Verify no adaptation section
  grep "## Project Adaptation" .squidsquad/pm/SOUL.md  # Expect no match
  # Verify PM cycle completes normally
  grep "cycle.*complete" .squidsquad/pm/iterations/iter-*.md | tail -1
  ```

---

### Storage Verification

---

### TC-30: config.md Project Intent Description field

- **Precondition**: Setup or upgrade completed.
- **Steps**:
  1. Read `config.md`.
- **Expected**: Contains `Project Intent Description` field (may be empty or populated).
- **Verification**:
  ```bash
  grep "Project Intent Description" .squidsquad/config.md
  ```

### TC-31: vault/BRIEFING.md includes intent

- **Precondition**: Setup completed with project intent.
- **Steps**:
  1. Read BRIEFING.md.
- **Expected**: Project intent is referenced in the briefing, giving agents project context at session start.
- **Verification**:
  ```bash
  grep -i "intent\|purpose\|project.*description" .squidsquad/vault/BRIEFING.md
  ```

### TC-32: role-adaptations.md is append-only

- **Precondition**: PM has written 5 entries over multiple cycles.
- **Steps**:
  1. Review git history for `role-adaptations.md`.
- **Expected**:
  - Every commit only adds lines. No lines are deleted by PM.
  - Status changes (consolidated, reverted) are marked inline, not removed.
- **Verification**:
  ```bash
  # Check that no commit removes lines (only adds)
  git log --oneline -- .squidsquad/vault/areas/role-adaptations.md | while read hash msg; do
    deletions=$(git show --stat "$hash" -- .squidsquad/vault/areas/role-adaptations.md | grep -o '[0-9]* deletion' | head -1)
    [ -n "$deletions" ] && echo "WARNING: $hash has $deletions"
  done
  ```

---

## Smoke Tests

- [ ] `grep "## Project Adaptation" .squidsquad/*/SOUL.md` -- all installed roles have the section
- [ ] `test -f .squidsquad/vault/areas/role-adaptations.md` -- adaptation changelog exists
- [ ] `grep "Project Intent Description" .squidsquad/config.md` -- config field present
- [ ] `grep "## Project Adaptation" references/roles/*/SOUL.md` -- templates have placeholder only (no generated content)
- [ ] PM cycle completes without errors when soul shepherd step runs
- [ ] `python references/scripts/compose.py deploy-all` preserves adaptation sections
- [ ] PM mentions adaptation updates in its check-in output

---

## Regression Risks

- **compose.py SOUL.md handling**: Any change to how compose.py handles SOUL.md could clobber adaptations. Watch for changes to `deploy_role` function.
- **Vault write budget exhaustion**: Soul shepherd writes to `role-adaptations.md` -- ensure this does not count against the vault-remember write budget (they are separate sub-steps).
- **Git merge conflicts in role-adaptations.md**: If PM and a human edit the file simultaneously, merge conflicts could occur. Append-only format mitigates this but does not eliminate it.
- **Context window bloat**: If consolidation logic has a bug and does not trigger, SOUL.md could grow unbounded, consuming agent context tokens.
- **Wizard regression**: Changes to the wizard flow (Step 6b) could break existing setup steps. Ensure Steps 1-6 and 7+ still work.
- **Multi-clone timing**: If PM pushes a SOUL.md update while another agent is mid-cycle, the agent won't see it until next cycle. This is expected but could cause confusion if the update is urgent.

---

## Comprehension Test Specs (CQs)

These comprehension questions verify that a fresh agent reading the updated PM template understands the new soul shepherd behavior. Spawn a fresh agent, give it the updated PM CLAUDE.md, and ask these questions. The agent must answer correctly without external hints.

---

### CQ-1: PM understands the 5-category trigger checklist

**Question**: "You are the PM agent. A new task has been filed: 'Add caching to the /users endpoint using Redis.' What categories from the soul shepherd checklist does this task trigger, and what would you do?"

**Expected answer must include**:
- Identifies "Tech stack evolution" (Redis is new to the project) as a trigger
- May identify "Quality/process preference" if caching implies performance requirements
- States it would append an adaptation entry to `role-adaptations.md`
- States it would re-render affected role SOUL.md files
- States it would commit the changes

**Fail criteria**: Agent says it would update on every task, or cannot name the 5 categories, or says it needs human approval for this non-contradictory signal.

---

### CQ-2: PM knows to flag contradictions for human, not auto-resolve

**Question**: "An earlier adaptation entry says 'This project is backend-only with no frontend.' A new task asks you to build a React dashboard. What do you do?"

**Expected answer must include**:
- Recognizes the contradiction with the existing adaptation
- States it would flag the contradiction to the human
- States it would NOT silently overwrite or supersede the earlier entry
- States it would wait for human resolution before updating adaptations

**Fail criteria**: Agent says it would automatically supersede the old entry, or silently add the new signal, or update the adaptation without human input.

---

### CQ-3: PM knows to re-render SOUL.md immediately after writing adaptations

**Question**: "You just appended a new entry to role-adaptations.md for the dev role. What do you do next in this same cycle?"

**Expected answer must include**:
- States it re-renders the dev role's `## Project Adaptation` section in `.squidsquad/skill/SOUL.md` immediately
- States it does this in the same cycle (not deferred to next cycle)
- States it commits the changes (both role-adaptations.md and SOUL.md in the same commit)

**Fail criteria**: Agent says it waits until next cycle to re-render, or says it only updates role-adaptations.md and leaves SOUL.md for later.

---

### CQ-4: PM knows the 40-line consolidation cap

**Question**: "After writing an adaptation entry, the dev role's Project Adaptation section is now 43 lines. What do you do?"

**Expected answer must include**:
- Recognizes the 40-line soft cap has been exceeded
- States it triggers consolidation
- Describes re-reading all non-reverted entries from `role-adaptations.md` for this role
- States it generates a consolidated summary (target 15-25 lines)
- States it marks pre-consolidation entries as `Status: consolidated`
- States no information should be lost in consolidation

**Fail criteria**: Agent does not know about the 40-line cap, or says 30-line cap (research draft value, not the locked decision), or says it would just truncate/delete content.

---

### CQ-5: PM knows signal-driven frequency (not periodic)

**Question**: "Should you update role adaptations every cycle, every 5 tasks, or only when you detect a new signal? Explain."

**Expected answer must include**:
- States signal-driven, not periodic
- States it checks every task/bug against the 5-category checklist (lightweight evaluation)
- States it only writes when something new is learned
- Mentions expected frequency of ~1 per 10-20 tasks

**Fail criteria**: Agent says it updates on a fixed schedule, or says it updates every task, or does not mention the checklist.

---

### CQ-6: PM understands atomic multi-role updates

**Question**: "A task reveals that the project now serves enterprise customers. This affects PM (priority lens), dev (error handling), and QA (test focus). How do you handle this?"

**Expected answer must include**:
- States it drafts adaptation entries for all 3 affected roles
- States all entries go into `role-adaptations.md` with a shared `Signal:` reference
- States it re-renders all 3 roles' SOUL.md files
- States everything lands in a single atomic commit

**Fail criteria**: Agent says it would make 3 separate commits, or only updates one role at a time across multiple cycles.
