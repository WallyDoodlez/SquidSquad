# FEAT-PM-1228 Test Plan — PM Pipeline Sentinel

## Test Cases

### TC-1: Pipeline sentinel runs every cycle when QA is present
- **Precondition**: `.squidsquad/qa/` exists with a valid `current-state` file. QA agent is running. A task exists at `pending-ship` status with an open PR.
- **Steps**:
  1. Trigger a PM Ralph Loop cycle.
  2. Observe step output after the QA-skip message.
- **Expected**: PM prints the QA-skip message for Steps 3-6 (testing/verification), then proceeds to run the pipeline sentinel step. The sentinel prints its own step marker (e.g., `[🦑 HH:MM:SS] Running pipeline sentinel...`). The sentinel checks for stalled tickets, conflicting PRs, and unmerged pending-ship tasks.
- **Verification**:
  - `current-state` file shows a sentinel-related phase during that step.
  - Iteration log includes sentinel activity in the work summary.
  - The pending-ship task is detected and acted upon (nudge comment or conflict detection).

### TC-2: Pipeline sentinel is skipped during planning suppression
- **Precondition**: `working-state.md` contains `**Phase**: researching FEAT-PM-XXXX`. A task exists at `pending-ship` status.
- **Steps**:
  1. Trigger a PM Ralph Loop cycle.
  2. Observe the suppressed cycle output.
- **Expected**: Cycle prints `(suppressed — active planning phase)`. Only `git pull --rebase` and Agent Health Check (Step 7) run. The pipeline sentinel does NOT run. The pending-ship task is NOT processed.
- **Verification**:
  - Iteration log shows suppressed cycle.
  - No sentinel step marker in output.
  - No comments added to the pending-ship task's issue.

### TC-3: Sentinel detects stalled pending-ship tickets
- **Precondition**: A task at `pending-ship` status. The last Discussion comment setting that status has a timestamp older than the stale threshold (e.g., 60+ minutes ago). `Branch Workflow: yes`. Dev has not merged the PR.
- **Steps**:
  1. Trigger a PM Ralph Loop cycle.
  2. Sentinel runs and queries pending-ship tasks.
  3. Sentinel reads the timestamp from the Discussion comment that set pending-ship.
- **Expected**: Sentinel detects the task as stalled (time at pending-ship exceeds threshold). Sentinel adds a nudge comment on the issue: something like "Task has been at pending-ship for [N] minutes. Dev agent should merge the PR."
- **Verification**:
  ```bash
  gh issue view [NUMBER] --json comments --jq '.comments[-1].body'
  ```
  Last comment contains a stall/nudge message from PM.

### TC-4: Sentinel nudges dev when pending-ship PR not merged
- **Precondition**: A task at `pending-ship` with an open (unmerged) PR. Stale threshold exceeded. Dev agent is healthy (not stalled).
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel detects unmerged PR for the pending-ship task.
- **Expected**: Sentinel comments on the issue nudging dev to merge the PR. Sentinel does NOT merge the PR itself (PM monitors and nudges, does not merge per locked decisions).
- **Verification**:
  ```bash
  gh issue view [NUMBER] --json comments --jq '.comments[-1].body'
  ```
  Comment is a nudge, not a merge action. PR remains open:
  ```bash
  gh pr view [PR_NUMBER] --json state --jq '.state'
  ```
  State is still `OPEN`.

### TC-5: Sentinel does not nudge when pending-ship is fresh
- **Precondition**: A task at `pending-ship` with an open PR. The status was set less than the stale threshold ago (e.g., 10 minutes ago with a 60-minute threshold).
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel runs.
- **Expected**: Sentinel detects the pending-ship task but does NOT nudge because it is within the threshold. Silent pass for this task.
- **Verification**: No new nudge comments on the issue. Iteration log does not mention a stall for this task.

### TC-6: PR conflict detection gated on Branch Workflow (not PR Flow)
- **Precondition**: `config.md` has `Branch Workflow: yes` and `PR Flow: no`. A task has an open PR with `mergeable: CONFLICTING`.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel runs and lists PRs.
- **Expected**: Sentinel detects the conflicting PR despite `PR Flow: no`. Sentinel transitions the task back to `In Progress` and comments on the issue about the merge conflict, routing back to dev for rebase.
- **Verification**:
  ```bash
  python references/scripts/tracker.py get-labels [NUMBER]
  ```
  Status label is `status:in-progress`.
  ```bash
  gh issue view [NUMBER] --json comments --jq '.comments[-1].body'
  ```
  Comment mentions merge conflicts and routing back to dev.

### TC-7: PR conflict detection skipped when Branch Workflow is off
- **Precondition**: `config.md` has `Branch Workflow: no`. Tasks exist with various statuses.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel runs.
- **Expected**: Sentinel skips PR conflict detection entirely (no PRs exist when Branch Workflow is off). No `gh pr list` calls related to conflict detection.
- **Verification**: No PR-related step markers or comments in the iteration log.

### TC-8: Sentinel detects CONFLICTING PR and comments on issue
- **Precondition**: `Branch Workflow: yes`. Two tasks with open PRs. One PR has `mergeable: MERGEABLE`, the other has `mergeable: CONFLICTING`.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel checks all open PRs.
- **Expected**: The CONFLICTING PR's task is transitioned back to `In Progress` with a Discussion comment about the conflict. The MERGEABLE PR's task is NOT affected.
- **Verification**:
  - Conflicting task: `status:in-progress` label, conflict comment present.
  - Clean task: status unchanged, no new comments from sentinel about conflicts.

### TC-9: Dev agent merges own PR at pending-ship
- **Precondition**: Dev agent template includes instruction to "merge your PR when task hits pending-ship." A task owned by the dev agent is at `pending-ship` status. An open PR exists for that task. `Auto Merge: yes`, `Branch Workflow: yes`.
- **Steps**:
  1. Dev agent runs its cycle.
  2. Dev detects its own task at `pending-ship`.
  3. Dev merges the PR.
- **Expected**: Dev successfully merges the PR via `git_ops.py pr-merge`. Dev adds a Discussion comment about the merge. PR state becomes `MERGED`.
- **Verification**:
  ```bash
  gh pr view [PR_NUMBER] --json state --jq '.state'
  ```
  Returns `MERGED`.
  ```bash
  gh issue view [NUMBER] --json comments --jq '.comments[-1].body'
  ```
  Comment from dev about PR merge.

### TC-10: Dev handles rebase when merge conflicts exist
- **Precondition**: Dev task at `pending-ship`. Open PR with merge conflicts. Dev attempts to merge.
- **Steps**:
  1. Dev agent detects pending-ship on own task.
  2. Dev attempts `git_ops.py pr-merge`.
  3. Merge fails due to conflicts.
- **Expected**: Dev detects the conflict, rebases the branch, force-pushes, and re-attempts merge. If rebase succeeds, PR is merged. If rebase fails, dev comments on the issue and routes back to `in-progress`.
- **Verification**: PR is either merged (if rebase succeeded) or task is back at `in-progress` with a conflict comment.

### TC-11: QA-present gate only skips testing/verification (Steps 3-6)
- **Precondition**: `.squidsquad/qa/` exists with valid `current-state`. Tasks exist at `pending-ship`. `Branch Workflow: yes`. DM is absent (`.squidsquad/dm/` does not exist).
- **Steps**:
  1. Trigger PM cycle.
  2. Observe which steps run and which are skipped.
- **Expected**: Steps 3-6 (E2E tests, investigate failures, verify issues, verify tasks) are skipped with the QA-present message. Pipeline sentinel step runs. Delivery fallback (PM-as-DM) runs. Post-merge recompose runs.
- **Verification**:
  - Output includes `QA agent present — skipping verification`.
  - Output includes pipeline sentinel step marker.
  - If pending-ship tasks exist and DM absent, delivery fallback runs.
  - Post-merge recompose runs (or silently skips if no merged branches).

### TC-12: PM fallback (no QA) runs full Steps 3-6
- **Precondition**: `.squidsquad/qa/` does NOT exist. E2E test command is configured. Tasks at `pending-test` exist.
- **Steps**:
  1. Trigger PM cycle.
  2. Observe step output.
- **Expected**: PM runs Steps 3-6 in full: E2E tests, investigate failures, verify issues, verify tasks. Pipeline sentinel also runs after Steps 3-6. No QA-skip message printed.
- **Verification**:
  - Output includes `Running E2E tests...`, `Verifying fixed issues...`, `Verifying pending test tasks...`.
  - Output also includes pipeline sentinel step marker.
  - Both testing/verification AND pipeline management execute in the same cycle.

### TC-13: Delivery fallback works when DM absent and QA present
- **Precondition**: `.squidsquad/qa/` exists. `.squidsquad/dm/` does NOT exist. A task at `pending-ship` exists with `delivery: skip` in its Discussion.
- **Steps**:
  1. Trigger PM cycle.
  2. Steps 3-6 skipped (QA present).
  3. Pipeline sentinel runs.
  4. Delivery fallback runs.
- **Expected**: PM detects no DM. PM performs delivery fallback for the pending-ship task. Since `delivery: skip` is set, PM marks it `Shipped` immediately and increments the ship counter.
- **Verification**:
  ```bash
  python references/scripts/tracker.py get-labels [NUMBER]
  ```
  Status is `status:shipped` (issue auto-closed).
  ```bash
  gh issue view [NUMBER] --json comments --jq '.comments[-1].body'
  ```
  Comment mentions PM delivery, delivery:skip, status shipped.

### TC-14: Post-merge recompose runs when QA is present
- **Precondition**: `.squidsquad/qa/` exists. `Branch Workflow: yes`. A recent merge commit touched `references/` files.
- **Steps**:
  1. Trigger PM cycle.
  2. Steps 3-6 skipped (QA present).
  3. Pipeline sentinel runs.
  4. Post-merge recompose step runs.
- **Expected**: Post-merge recompose detects the merged branch that touched `references/`. Runs `compose.py deploy-all`. Comments on the associated issue.
- **Verification**:
  ```bash
  git log --oneline -1
  ```
  Shows a compose-related commit if templates changed.
  Issue comment mentions recomposition.

### TC-15: Post-merge recompose silently skips when no references/ changes
- **Precondition**: `Branch Workflow: yes`. No recent merges touched `references/`.
- **Steps**:
  1. Trigger PM cycle.
  2. Post-merge recompose step runs.
- **Expected**: Step runs but exits silently. No `compose.py deploy-all` invoked. No issue comments.
- **Verification**: No compose-related output in step markers. No new issue comments.

### TC-16: No duplicate merges (dev merges, PM does not also try)
- **Precondition**: Dev agent has already merged a PR for a pending-ship task. PR state is `MERGED`. PM cycle runs after dev's merge.
- **Steps**:
  1. Dev merges PR for task #X.
  2. PM cycle runs, sentinel checks pending-ship tasks.
- **Expected**: PM sentinel sees no open PR for the task (already merged). PM does NOT attempt a merge. If DM is absent, delivery fallback proceeds directly to delivery packaging (no PR found = silent proceed). No duplicate merge attempts or errors.
- **Verification**:
  - No merge-related comments from PM on the issue.
  - No errors in PM iteration log about merge attempts.
  - Delivery fallback (if applicable) proceeds without the auto-merge sub-step.

### TC-17: Existing auto-merge config respected
- **Precondition**: `Auto Merge: no` in config.md. A task at `pending-ship` with an open PR. DM absent.
- **Steps**:
  1. Trigger PM cycle.
  2. Delivery fallback runs for the pending-ship task.
- **Expected**: Delivery fallback checks auto-merge eligibility. `Auto Merge: no` means auto-merge is not eligible. Fallback skips the merge sub-step silently and proceeds to delivery packaging. PR remains open.
- **Verification**:
  ```bash
  gh pr view [PR_NUMBER] --json state --jq '.state'
  ```
  Returns `OPEN`.
  No merge-related comments on the issue.

### TC-18: Bug fixes (type:issue) are not auto-merged
- **Precondition**: `Auto Merge: yes`, `Branch Workflow: yes`. An issue (type:issue, not type:task) at `pending-ship` with an open PR. DM absent.
- **Steps**:
  1. Trigger PM cycle.
  2. Delivery fallback runs.
- **Expected**: Auto-merge eligibility check rejects the item because it is `type:issue`, not `type:task`. PR remains open. Delivery proceeds without merge.
- **Verification**: PR state is `OPEN`. No merge comment from PM.

### TC-19: merge:manual label prevents auto-merge
- **Precondition**: `Auto Merge: yes`, `Branch Workflow: yes`. A task at `pending-ship` with `merge:manual` label and an open PR.
- **Steps**:
  1. Trigger PM cycle.
  2. Delivery fallback runs.
- **Expected**: Auto-merge eligibility check rejects the item because of `merge:manual` label. PR remains open.
- **Verification**: PR state is `OPEN`. No merge comment from PM.

### TC-20: Multiple pending-ship tasks with conflicting PRs
- **Precondition**: Two tasks at `pending-ship`, each with an open PR. The PRs conflict with each other (touching the same files). Dev merges task A's PR first.
- **Steps**:
  1. Dev merges PR for task A.
  2. Dev attempts to merge PR for task B.
  3. Merge fails due to conflicts with the now-merged task A changes.
- **Expected**: Task A's PR merges successfully. Task B's PR reports merge conflict. Dev (or sentinel) transitions task B back to `in-progress` with a conflict comment. Dev rebases task B's branch and resubmits.
- **Verification**:
  - Task A: PR merged, status progresses normally.
  - Task B: status is `in-progress`, conflict comment present, PR still open.

### TC-21: Tasks without PRs (Branch Workflow off)
- **Precondition**: `Branch Workflow: no`. A task at `pending-ship`. DM absent.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel and delivery fallback run.
- **Expected**: Sentinel skips PR conflict detection (no Branch Workflow). Delivery fallback skips auto-merge silently (no PR exists). Delivery proceeds directly to packaging. No errors about missing PRs.
- **Verification**: No PR-related step markers. Delivery completes normally. Task ships.

### TC-22: PR Flow off but Branch Workflow on (current project config)
- **Precondition**: `PR Flow: no`, `Branch Workflow: yes` (matches current config). QA present. A task at `pending-ship` with an open PR that has `mergeable: CONFLICTING`.
- **Steps**:
  1. Trigger PM cycle.
  2. Steps 3-6 skipped (QA present).
  3. Pipeline sentinel runs.
- **Expected**: Sentinel detects the conflicting PR because conflict detection is gated on Branch Workflow, not PR Flow. Task is routed back to `in-progress` with a conflict comment. This is the primary failure case this task fixes.
- **Verification**:
  ```bash
  python references/scripts/tracker.py get-labels [NUMBER]
  ```
  Status is `status:in-progress`.
  Conflict comment present on the issue.

### TC-23: DM present - sentinel does not attempt shipping
- **Precondition**: `.squidsquad/dm/` exists. A task at `pending-ship`. Stale threshold not exceeded.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel runs.
- **Expected**: Sentinel monitors the task but does NOT attempt shipping (that is DM's transition). Sentinel only handles conflict detection and stall nudging. Delivery fallback is skipped because DM is present.
- **Verification**: No `pending-ship -> shipped` transition by PM. No delivery-related comments from PM. DM remains responsible for shipping.

### TC-24: Sentinel step position in Ralph Loop
- **Precondition**: Recomposed PM `CLAUDE.md` with the new pipeline-sentinel sub-skill.
- **Steps**:
  1. Read the composed PM template.
  2. Identify the position of the pipeline sentinel step.
- **Expected**: Pipeline sentinel appears AFTER the QA-skippable Steps 3-6 block and BEFORE Step 7 (Health Check). It is included via `{{include: pm-specific/pipeline-sentinel}}` in the template. It is NOT nested inside the QA-skip gate.
- **Verification**:
  ```bash
  grep -n "pipeline-sentinel\|QA presence check\|Step 7" .squidsquad/pm/CLAUDE.md
  ```
  Pipeline sentinel line number is between the QA-skip block end and Step 7.

## Edge Case Tests

### TC-25: QA rejects task after dev already merged PR
- **Precondition**: Dev merged a PR for task #X. QA later re-tests and finds an issue (hypothetical re-test scenario). PR is already merged.
- **Steps**:
  1. QA transitions task back to `in-progress`.
  2. Dev picks up the task again.
- **Expected**: Dev creates a new branch for the fix (the old PR is already merged). This is correct behavior -- the merge was valid at the time of approval. No rollback of the merge. Dev submits a new PR for the fix.
- **Verification**: A new branch/PR is created for the fix. Original PR remains merged. Task is at `in-progress`.

### TC-26: Stalled pending-ship with no open PR (already merged, no delivery)
- **Precondition**: Task at `pending-ship`. PR was already merged by dev. DM is absent. Stale threshold exceeded. Delivery fallback has not yet run for this task.
- **Steps**:
  1. Sentinel detects stalled pending-ship task.
  2. Sentinel checks for open PR -- none found (already merged).
- **Expected**: Sentinel nudges about the stall. Delivery fallback picks up the task and proceeds directly to delivery (no auto-merge needed since PR is already merged).
- **Verification**: Nudge comment on issue. Delivery fallback runs and ships the task.

### TC-27: Sentinel runs with zero pending-ship tasks
- **Precondition**: No tasks at `pending-ship` status. All tasks are either `in-progress`, `pending-test`, or `shipped`.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel runs.
- **Expected**: Sentinel queries for pending-ship tasks, finds none. Silent pass. No errors, no comments, no nudges.
- **Verification**: No sentinel-related comments on any issues. Iteration log shows sentinel ran but found nothing actionable.

### TC-28: Sentinel with GitHub temporarily unreachable
- **Precondition**: GitHub API is temporarily down or network blip occurs during sentinel's PR check.
- **Steps**:
  1. Trigger PM cycle.
  2. Sentinel attempts to query PRs or issues.
  3. `gh` commands fail with network error.
- **Expected**: Sentinel follows the existing protocol: "GitHub unreachable -- skipping tracker operations. Will retry next cycle." No status transitions attempted. No crashes. Cycle continues to remaining steps.
- **Verification**: Output includes the unreachable warning. No partial transitions. Next cycle retries successfully.

## Side Effect Regression Tests

### TC-29: QA-absent PM still runs full verification
- **Precondition**: `.squidsquad/qa/` does NOT exist. E2E tests configured. Issues at `pending-test`.
- **Steps**:
  1. Trigger PM cycle.
- **Expected**: PM runs Steps 3-6 in full (E2E tests, investigate, verify issues, verify tasks). Behavior is identical to pre-#1228. The new pipeline sentinel step runs AFTER Steps 3-6, adding monitoring without removing verification.
- **Verification**: Compare step marker output to a pre-#1228 cycle. All verification steps present. Pipeline sentinel is additive.

### TC-30: Existing auto-merge in delivery-fallback unchanged
- **Precondition**: `Auto Merge: yes`, `Branch Workflow: yes`. QA absent. DM absent. Task at `pending-test`.
- **Steps**:
  1. PM verifies the task (Step 6), transitions to `pending-ship`.
  2. Delivery fallback (Step 6d) runs for the task.
  3. Auto-merge sub-step triggers.
- **Expected**: Delivery fallback auto-merge behavior is identical to pre-#1228. The auto-merge eligibility check, PR discovery, merge execution, and error handling all work the same way. No changes to delivery-fallback logic.
- **Verification**: Discussion comments match the existing format. Merge behavior matches documented behavior in delivery-fallback.md.

### TC-31: Step 6b PR monitoring unchanged when PR Flow is on
- **Precondition**: `PR Flow: yes`. QA absent. Open PRs exist.
- **Steps**:
  1. Trigger PM cycle.
  2. Step 6b runs (PR Flow is on).
- **Expected**: Step 6b behavior is identical to pre-#1228: merged PR detection, closed PR detection, conflict detection, comment sync, changes-requested handling. The new pipeline sentinel does NOT duplicate Step 6b's work when PR Flow is on.
- **Verification**: Compare output and Discussion comments to pre-#1228 behavior. No duplicate conflict comments. No duplicate status transitions.

### TC-32: Ship counter increments correctly
- **Precondition**: `Shipped Since Last Bump: 3`. DM absent. A task ships via PM delivery fallback.
- **Steps**:
  1. Task transitions to `Shipped`.
  2. Counter increments.
- **Expected**: `Shipped Since Last Bump` becomes `4`. Counter logic unchanged by #1228.
- **Verification**:
  ```bash
  python references/scripts/config.py get shipped-since-last-bump
  ```
  Returns `4`.

### TC-33: Planning suppression still works correctly
- **Precondition**: `working-state.md` has active planning phase. Pipeline sentinel is in the template.
- **Steps**:
  1. Trigger PM cycle.
- **Expected**: Suppression behavior unchanged: only pull + health check run. Pipeline sentinel is suppressed along with all other steps. No regression in suppression logic.
- **Verification**: Output shows `(suppressed — active planning phase)`. Only pull and health check markers present.

### TC-34: Health check (Step 7) runs independently of sentinel
- **Precondition**: Normal PM cycle. Agents are running.
- **Steps**:
  1. Trigger PM cycle.
  2. Both sentinel and health check run.
- **Expected**: Health check runs at its existing position (Step 7), unaffected by the new sentinel step. No interaction between sentinel's stall detection and health check's stall detection (they serve different purposes: sentinel checks task staleness, health check checks agent process staleness).
- **Verification**: Both step markers appear. Health check output is identical to pre-#1228.

## Upgrade Verification Tests

### TC-35: compose.py deploy-all regenerates PM CLAUDE.md with sentinel
- **Precondition**: New `pipeline-sentinel.md` exists in `references/sub-skills/pm-specific/`. `includes.yml` updated with the new sub-skill entry.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy pm`.
  2. Read the generated `.squidsquad/pm/CLAUDE.md`.
- **Expected**: The composed CLAUDE.md includes the pipeline sentinel section. The sentinel appears after the QA-skippable block and before Step 7. The QA-skip gate text says "Skip Steps 3-6 (testing and verification only)" or equivalent narrowed language. Pipeline steps (sentinel, delivery fallback, post-merge recompose) are outside the skip gate.
- **Verification**:
  ```bash
  grep -c "pipeline.sentinel\|Pipeline Sentinel" .squidsquad/pm/CLAUDE.md
  ```
  Returns >= 1.
  ```bash
  grep "Skip Steps 3" .squidsquad/pm/CLAUDE.md
  ```
  Text no longer says "Skip Steps 3-6 entirely" without qualification.

### TC-36: Dev template updated with merge instruction
- **Precondition**: Dev-specific sub-skill (e.g., `implement-tasks.md`) updated with "merge your PR when task hits pending-ship" instruction.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy skill`.
  2. Read the generated `.squidsquad/skill/CLAUDE.md`.
- **Expected**: Dev template includes instruction for the dev agent to detect pending-ship status on its own tasks and merge the PR.
- **Verification**:
  ```bash
  grep -i "pending-ship.*merge\|merge.*pending-ship" .squidsquad/skill/CLAUDE.md
  ```
  Returns at least one match.

### TC-37: includes.yml has pipeline-sentinel entry
- **Precondition**: `references/roles/pm/includes.yml` has been updated.
- **Steps**:
  1. Read `includes.yml`.
- **Expected**: `pm-specific/pipeline-sentinel` appears as an include entry, positioned after `pm-specific/testing-and-verification`.
- **Verification**:
  ```bash
  grep "pipeline-sentinel" references/roles/pm/includes.yml
  ```
  Returns a match.

### TC-38: Graceful degradation for non-upgraded installs
- **Precondition**: An existing install that has NOT run `compose.py deploy` after the template changes. Old CLAUDE.md is in use.
- **Steps**:
  1. PM runs a cycle with the old template.
- **Expected**: PM behaves exactly as before #1228 -- pipeline steps are skipped when QA is present. No errors, no crashes, no missing sub-skill references. The gap continues but nothing breaks.
- **Verification**: PM cycle completes without errors. The old QA-skip behavior is preserved.

### TC-39: No new config values required
- **Precondition**: Existing `config.md` with current fields.
- **Steps**:
  1. Run `compose.py deploy pm` with the new template.
  2. PM runs a cycle.
- **Expected**: No errors about missing config values. The sentinel uses existing `Branch Workflow`, `Auto Merge`, and `Iteration Interval` settings. Stale threshold is derived (2x Iteration Interval) without a new config field.
- **Verification**: PM cycle completes without config-related errors. No prompts to add new config fields.

## Smoke Tests

- [ ] `pipeline-sentinel.md` exists at `references/sub-skills/pm-specific/pipeline-sentinel.md`
- [ ] `includes.yml` references `pm-specific/pipeline-sentinel`
- [ ] `compose.py deploy pm` completes without errors
- [ ] Composed PM CLAUDE.md contains pipeline sentinel section
- [ ] Composed PM CLAUDE.md QA-skip gate does NOT cover pipeline steps
- [ ] Dev template mentions merging PRs at pending-ship
- [ ] `python references/scripts/config.py get branch-workflow` returns a value (sentinel dependency)
- [ ] `python references/scripts/config.py get auto-merge` returns a value (sentinel dependency)
- [ ] PM cycle with QA present prints sentinel step marker after QA-skip message
- [ ] PM cycle with QA absent runs both verification AND sentinel

## Regression Risks

- **QA-skip gate wording change breaks existing behavior**: If the gate text is changed too aggressively, PM might stop skipping verification steps when QA is present. Test TC-11 and TC-12 carefully.
- **Step numbering confusion**: If the sentinel is numbered ambiguously (e.g., "Step 6.5"), PM might misinterpret its position relative to the QA-skip gate. Verify TC-24.
- **Double PR conflict comments**: If both the sentinel and Step 6b (when PR Flow is on) detect the same conflict, two comments could be posted. Verify TC-31 for deduplication.
- **Delivery fallback regression**: Moving delivery-related logic around could break the PM-as-DM path. Verify TC-13 and TC-30 thoroughly.
- **Post-merge recompose running too often**: If the sentinel triggers recompose every cycle without the early exit check, it wastes cycles. Verify TC-15.
- **Dev merge + PM merge race**: If dev merges and PM simultaneously tries to merge (before seeing the merged state), one will fail. Verify TC-16 for graceful handling.
- **Planning suppression must suppress sentinel**: If the sentinel is not properly excluded during planning suppression, it could run during planning and cause side effects. Verify TC-2 and TC-33.
