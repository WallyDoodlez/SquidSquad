# FEAT-SKILL-246 Test Plan — PR-Driven Workflow Mode

## Overview

Tests cover the full PR Flow lifecycle when enabled, backward compatibility when disabled, and all config-dependency enforcement. Tests assume Branch Workflow (#375) is already shipped and operational.

---

## Test Cases

### TC-1: PR body template — required sections present

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Dev agent has just marked an issue Pending Test.
- **Steps**: Inspect the PR created by the dev agent via `gh pr view [N] --json body`.
- **Expected**: PR body contains all of: `Closes #[NUMBER]`, a Summary section, an Acceptance Criteria section, a Changes section (files/what/why), and a QA Status checklist.
- **Verification**: `gh pr view [N] --json body | python -c "import sys,json; b=json.load(sys.stdin)['body']; assert 'Closes #' in b and '### Summary' in b and '### Acceptance Criteria' in b and '### QA Status' in b, 'Missing required section'"`

---

### TC-2: Dev creates PR with `gh pr create` and structured body, posts PR URL on issue

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Dev agent is on branch `squidsquad/skill/NNN` and is transitioning an issue to pending-test.
- **Steps**: Observe dev agent's output during the pending-test transition.
- **Expected**:
  - `gh pr create` is called with a structured body (not the old minimal template).
  - PR title format: `skill: #NNN -- [title]`
  - Dev agent comments the PR URL on the GitHub issue as a tracker comment.
- **Verification**: `gh issue view [N] --json comments` — most recent comment from `skill-lead` contains the PR URL. `gh pr view [N] --json title,body` — title and body match expected format.

---

### TC-3: `status:pending-review` label exists and is creatable

- **Precondition**: Fresh repo or repo where label does not yet exist.
- **Steps**: Run `gh label list | grep pending-review`.
- **Expected**: Label `status:pending-review` exists with a distinct color and description.
- **Verification**: `gh label list --json name,description,color | python -c "import sys,json; labels=json.load(sys.stdin); assert any(l['name']=='status:pending-review' for l in labels), 'Label missing'"`

---

### TC-4: QA transitions to `pending-review` (not `pending-ship`) when PR Flow enabled

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Issue is in `pending-test`, PR is open. QA has verified the branch — zero gaps.
- **Steps**: Execute QA verification cycle.
- **Expected**: Tracker transitions issue to `pending-review`, NOT `pending-ship`.
- **Verification**: `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:pending-review` and does NOT include `status:pending-ship`.

---

### TC-5: QA posts formal `gh pr review --approve` after passing verification

- **Precondition**: Branch Workflow: yes, PR Flow: yes. QA has verified — zero gaps.
- **Steps**: Observe QA agent output during verification completion.
- **Expected**: `gh pr review [PR_NUMBER] --approve --body "QA verified -- zero gaps."` is executed. A PR review appears on the GitHub PR from QA.
- **Verification**: `gh pr view [N] --json reviews | python -c "import sys,json; revs=json.load(sys.stdin)['reviews']; assert any(r['state']=='APPROVED' for r in revs), 'No QA approval found'"`

---

### TC-6: QA posts QA results as a comment on the PR (not only on the issue)

- **Precondition**: Branch Workflow: yes, PR Flow: yes. QA verification just completed (pass).
- **Steps**: Inspect PR comments via `gh pr view [N] --comments`.
- **Expected**: A comment from QA is present on the PR containing: Status (PASS/FAIL), reference to TEST-PLAN and QA-RESULTS files, test pass/fail count, findings summary.
- **Verification**: `gh pr view [N] --json comments` — at least one comment body contains "QA Results" and "Status".

---

### TC-7: QA posts `gh pr review --request-changes` on verification failure

- **Precondition**: Branch Workflow: yes, PR Flow: yes. QA verification fails — one or more gaps found.
- **Steps**: Execute QA verification on a branch known to have a failing acceptance criterion.
- **Expected**:
  - `gh pr review [PR_NUMBER] --request-changes --body "QA FAIL: [findings]"` is executed.
  - PR review state shows CHANGES_REQUESTED.
  - Tracker issue transitions back to `in-progress`.
- **Verification**: `gh pr view [N] --json reviews` — at least one review with `state == "CHANGES_REQUESTED"`. `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:in-progress`.

---

### TC-8: PM detects merged PR and transitions to `pending-ship`

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Issue is in `pending-review`. Human merges the PR on GitHub.
- **Steps**: Wait for or manually trigger a PM cycle. PM runs Step 6b.
- **Expected**:
  - PM detects the merged PR via `gh pr list ... --state all`.
  - Tracker issue transitions to `pending-ship`.
  - PM appends Discussion entry: "PR [URL] merged by human. Status → Pending Ship."
- **Verification**: `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:pending-ship`. `gh issue view [N] --json comments` — most recent comment from `pm-lead` references the merge.

---

### TC-9: PM detects PR closed without merge and transitions back to `in-progress`

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Issue is in `pending-review`. Human closes the PR without merging.
- **Steps**: Close the PR on GitHub without merging. Run a PM cycle.
- **Expected**: Tracker issue transitions to `in-progress`. PM appends Discussion entry noting the closed-without-merge event.
- **Verification**: `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:in-progress`.

---

### TC-10: PM relays new PR comments to tracker Discussion

- **Precondition**: Branch Workflow: yes, PR Flow: yes. PR is open. Human adds a comment on the PR.
- **Steps**: Post a comment on the PR via GitHub UI or `gh pr comment [N] --body "Looks good but please rename X to Y"`. Run a PM cycle.
- **Expected**: PM appends a Discussion entry on the issue summarizing the PR comment, attributed to the human author.
- **Verification**: `gh issue view [N] --json comments` — contains a comment from `pm-lead` with the PR comment body or summary.

---

### TC-11: PM detects "changes requested" review and transitions back to `in-progress`

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Issue is in `pending-review`. Human submits a "Request changes" review on the PR.
- **Steps**: Submit a request-changes review on the PR via GitHub UI or `gh pr review [N] --request-changes --body "Please fix X"`. Run a PM cycle.
- **Expected**:
  - PM detects the changes-requested review.
  - Tracker issue transitions to `in-progress`.
  - PM appends Discussion entry with the requested changes noted.
- **Verification**: `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:in-progress`. Discussion entry references the review feedback.

---

### TC-12: PM logs human approval review (informational, no status change)

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Issue is in `pending-review`. Human submits an "Approve" review on the PR but has NOT yet merged.
- **Steps**: Submit an approval review on the PR (no merge). Run a PM cycle.
- **Expected**:
  - PM logs a Discussion entry: "PR [URL] approved by [human]. Awaiting merge."
  - Tracker issue remains at `pending-review` — no status change.
- **Verification**: `python references/scripts/tracker.py get-labels [NUMBER]` still includes `status:pending-review`. `gh issue view [N] --json comments` — comment from `pm-lead` references the approval.

---

### TC-13: Code review summary posted as PR comment when PR is created

- **Precondition**: Branch Workflow: yes, PR Flow: yes. Dev agent has just created the PR.
- **Steps**: Inspect PR comments via `gh pr view [N] --comments` shortly after PR creation.
- **Expected**: A structured code review summary comment is present, authored by dev, containing: what changed, why, key decisions, files touched.
- **Verification**: `gh pr view [N] --json comments` — at least one comment with structured sections (Changes, Decisions, Files).

---

### TC-14: Dev agent monitors PR comments and reacts to requested changes

- **Precondition**: Branch Workflow: yes, PR Flow: yes. PR is open. Human posts a comment requesting a code change.
- **Steps**: Post a comment on the PR requesting a specific fix. Run a dev agent cycle.
- **Expected**:
  - Dev agent detects the new PR comment.
  - Dev agent implements the requested change (if within scope) or replies with a clarifying question.
  - Dev agent pushes updated commits to the same branch (PR auto-updates).
- **Verification**: `git log --oneline squidsquad/skill/[N]` — new commit present. Or `gh pr view [N] --json comments` — dev response comment present.

---

### TC-15: Dev agent monitors PR comments and answers questions

- **Precondition**: Branch Workflow: yes, PR Flow: yes. PR is open. Human posts a question as a PR comment.
- **Steps**: Post a question comment on the PR (e.g., "Why did you choose X over Y?"). Run a dev agent cycle.
- **Expected**: Dev agent replies to the PR comment with an answer.
- **Verification**: `gh pr view [N] --json comments` — dev comment present after the question, with a substantive reply.

---

### TC-16: Opt-in mandatory human approval config toggle — enabled

- **Precondition**: `config.md` has `Mandatory Human Approval: yes`. A task is in planning phase.
- **Steps**: Run PM task intake Phase 3 (planning gate).
- **Expected**: PM skips the planning approval gate (does not ask for human approval at the Planned → Approved transition). Task is held at `pending-review` until the human merges the PR.
- **Verification**: Task status does not transition to `approved` via the planning gate. PR merge is required for delivery to proceed.

---

### TC-17: Opt-in mandatory human approval config toggle — disabled (default)

- **Precondition**: `config.md` has `Mandatory Human Approval: no` (or key absent). A task is in planning phase.
- **Steps**: Run PM task intake Phase 3.
- **Expected**: Normal planning approval gate applies. Human can approve at the Planned → Approved transition as before.
- **Verification**: PM presents the approval gate prompt. Task transitions to `approved` when human says "go".

---

### TC-18: PR Flow: no — backward compatibility, no behavior change

- **Precondition**: `config.md` has `PR Flow: no`. Branch Workflow: yes.
- **Steps**: Complete a full feature cycle (dev → pending-test → QA verify → pending-ship).
- **Expected**:
  - QA does NOT call `gh pr review`.
  - QA transitions directly to `pending-ship` (not `pending-review`).
  - PM Step 6b does NOT run (no PR monitoring).
  - No `status:pending-review` label appears on any issue.
  - Delivery proceeds as before.
- **Verification**: `python references/scripts/tracker.py get-labels [NUMBER]` never contains `status:pending-review`. No `gh pr review` calls appear in agent output.

---

### TC-19: PR Flow: yes requires Branch Workflow: yes — dependency enforced

- **Precondition**: `config.md` has `PR Flow: yes` and `Branch Workflow: no`.
- **Steps**: Run `python references/scripts/config.py get pr-flow`.
- **Expected**: Config enforcement logs a warning (or the calling agent logs a warning) that PR Flow is disabled because Branch Workflow is not enabled. PR Flow behavior is treated as `no`.
- **Verification**: Agent output contains warning referencing Branch Workflow dependency. No `gh pr review` or `pending-review` transitions occur.

---

### TC-20: `Closes #N` in PR body — issue auto-closes on merge

- **Precondition**: Branch Workflow: yes, PR Flow: yes. PR body includes `Closes #[NUMBER]`.
- **Steps**: Human merges the PR on GitHub.
- **Expected**: GitHub auto-closes the issue (sets state to "closed"). PM's next cycle detects the merge, sets `status:pending-ship`, and proceeds with delivery regardless of the auto-close state.
- **Verification**: `gh issue view [N] --json state` — `state: "CLOSED"`. `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:pending-ship` (set by PM, independent of auto-close).

---

### TC-21: Tracker transition authorization — only QA can transition `pending-test` → `pending-review`

- **Precondition**: PR Flow: yes. Issue is in `pending-test`.
- **Steps**: Attempt to run `python references/scripts/tracker.py transition [N] pending-test pending-review --role skill-lead`.
- **Expected**: Transition rejected — skill agent is not authorized for this transition.
- **Verification**: Exit code non-zero. Error message references unauthorized role.

---

### TC-22: Tracker transition authorization — PM can transition `pending-review` → `in-progress`

- **Precondition**: PR Flow: yes. Issue is in `pending-review` (human requested changes on PR).
- **Steps**: PM attempts `python references/scripts/tracker.py transition [N] pending-review in-progress --role pm-lead`.
- **Expected**: Transition succeeds.
- **Verification**: Exit code 0. `python references/scripts/tracker.py get-labels [NUMBER]` includes `status:in-progress`.

---

### TC-23: Tracker transition authorization — only PM can transition `pending-review` → `pending-ship`

- **Precondition**: PR Flow: yes. Issue is in `pending-review`.
- **Steps**: Attempt `python references/scripts/tracker.py transition [N] pending-review pending-ship --role qa-lead`.
- **Expected**: Transition rejected — `pending-review → pending-ship` is PM-only (triggered by PM on merge detection).
- **Verification**: Exit code non-zero. Error references unauthorized role.

---

### TC-24: Full end-to-end happy path with PR Flow enabled

- **Precondition**: Branch Workflow: yes, PR Flow: yes. A task is in `approved` status.
- **Steps**:
  1. Dev picks up task → `in-progress`
  2. Dev implements on branch, commits, creates PR, comments URL on issue → `pending-test`
  3. QA checks out branch, verifies — zero gaps
  4. QA posts results on PR, calls `gh pr review --approve`, transitions to `pending-review`
  5. Human reviews PR, approves, merges
  6. PM cycle detects merge, transitions to `pending-ship`
  7. PM/DM delivers → `shipped`
- **Expected**: Each step completes without manual intervention. All status transitions follow the authorized path. PR body, QA comment, and code review summary are all present on the PR.
- **Verification**: `gh issue view [N] --json labels,state,comments` — labels show `status:shipped`, state is closed. PR is merged. Comments show QA results and review summary.

---

### TC-25: Bug goes through PR Flow (same as tasks)

- **Precondition**: PR Flow: yes. A bug is in `approved` status.
- **Steps**: Complete the same flow as TC-24 but starting from a `type:issue` rather than `type:task`.
- **Expected**: Bug follows the identical PR flow (no special bypass). `pending-review` status applies to bugs as well.
- **Verification**: Same as TC-24. Bug issue transitions include `pending-review`.

---

## Smoke Tests

- [ ] `python references/scripts/config.py get pr-flow` returns `yes` or `no` without error
- [ ] `gh label list | grep pending-review` returns the label (after setup/upgrade)
- [ ] `python references/scripts/tracker.py transition [N] pending-test pending-review --role qa-lead` succeeds when PR Flow is enabled
- [ ] Dev agent PR body contains `Closes #[NUMBER]` in the correct GitHub syntax
- [ ] PM Step 6b runs when PR Flow is yes and is skipped when PR Flow is no (check agent log output)
- [ ] QA step outputs `gh pr review --approve` call when PR Flow is yes
- [ ] QA step does NOT output `gh pr review` when PR Flow is no

---

## Regression Risks

- **Direct-merge path broken**: When PR Flow is no, QA must still transition to `pending-ship` (not `pending-review`). Any change to the QA verification step must preserve this path.
- **PM Step 6b collision**: PM Step 6b already monitors PRs. Enhancements must not duplicate existing comment-relay logic or create double Discussion entries.
- **Tracker transition table**: Adding `pending-review` to the status graph must not break existing legal transitions for `pending-test → pending-ship` (used when PR Flow is no).
- **`Closes #N` race condition**: GitHub auto-close fires before PM detects the merge. PM must handle issues that are already in "closed" GitHub state but still have `status:pending-review` label — transition to `pending-ship` must still succeed.
- **QA comments on PR vs issue**: When PR Flow is enabled, QA comments on both the PR and the issue. Verify no duplicate Discussion entries appear on the issue from this dual-write.
- **Config dependency check**: If `Branch Workflow` is toggled off after `PR Flow` was enabled, the enforcement check must fire on the next agent cycle — not silently ignore the broken config state.
