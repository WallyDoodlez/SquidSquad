# FEAT-SKILL-246 Research -- PR-Driven Workflow Mode

## Summary

With #375 (branch-per-feature) shipped, dev agents already work on branches (`squidsquad/<role>/<number>`), commit code to branches and state to main, and create PRs when marking Pending Test. The current flow: after QA verifies on the branch, QA/PM transitions directly to Pending Ship and the code gets merged automatically (PM Step 6e detects merged branches). #246 changes the end of this pipeline: instead of auto-merging, the PR becomes the human review gate. The human reviews, approves, and merges on GitHub. PM detects the merge event and proceeds with delivery.

**Key insight**: Most of the infrastructure already exists. The dev agent already creates PRs (Step 5 item 3 in `common/git-commit.md`). PM already monitors PRs (Step 6b in `pm-specific/pr-flow.md`). QA already monitors PRs (Step 5b in `qa-specific/verification.md`). The `PR Flow` config toggle exists in `config.md` (currently `no`). What is missing is the *behavioral wiring* -- when PR Flow is enabled, the status flow changes and agents must stop auto-merging.

**Recommendation**: Feasible with moderate effort. The main changes are behavioral (template instructions), not infrastructure (scripts). Estimated 4-6 files changed, no new Python scripts needed.

---

## 1. Current PR Flow Infrastructure

### 1.1 Config toggle

`config.md` has:
```markdown
## PR Flow

- **Enabled**: no
```

`config.py` maps `pr-flow` to `("PR Flow", "Enabled")`, so agents read it via:
```bash
python references/scripts/config.py get pr-flow
```

### 1.2 git_ops.py -- pr_create already exists

`git_ops.py` line 182-193 has a working `pr_create(title, body)` function that calls `gh pr create`. It is already wired into the CLI as `pr-create <title> <body>`.

### 1.3 Dev agent already creates PRs

In `common/git-commit.md` (deployed to `.squidsquad/dev/CLAUDE.md` line 708-714), when Branch Workflow is `yes` and the dev marks Pending Test:
```bash
python references/scripts/git_ops.py pr-create "dev: #[NUMBER] -- [title]" "## #[NUMBER]\n\n[acceptance criteria]\n\nStatus: Pending Test"
```
The dev also comments the PR URL on the issue.

### 1.4 PM Step 6b -- PR monitoring exists

`pm-specific/pr-flow.md` defines Step 6b which:
- Lists open SquidSquad PRs via `gh pr list`
- Detects merged PRs -> transitions to Pending Ship
- Detects closed-without-merge -> transitions back to In Progress
- Relays new PR comments to tracker Discussion
- Detects "changes requested" reviews -> transitions back to In Progress

### 1.5 QA Step 5b -- PR monitoring exists

`qa-specific/verification.md` has an identical Step 5b with the same PR monitoring logic, using `qa` role instead of `pm`.

### 1.6 PM Step 6e -- Post-Merge Recompose exists

Detects recently merged `squidsquad/` branches and runs `compose.py deploy-all` if `references/` was modified.

### 1.7 What is NOT wired

- The `PR Flow` toggle is `no` -- all PR monitoring steps are skipped.
- When PR Flow is `no`, the status flow is: Pending Test -> QA verifies -> Pending Ship -> DM/PM ships (auto-merge implicit).
- There is no explicit "merge the branch" step anywhere -- #375 relies on the PR existing but merging happens outside the current automated flow (or the human merges manually on GitHub).
- The dev agent creates PRs unconditionally when Branch Workflow is `yes`, regardless of PR Flow setting. This is actually correct -- the PR exists even without PR Flow enabled; PR Flow just controls whether agents *monitor* PRs for human review signals.

---

## 2. Dev Agent Changes

### 2.1 Current behavior (Branch Workflow: yes, PR Flow: no)

1. Dev works on branch `squidsquad/skill/NNN`
2. Dev commits code to branch, state to main
3. Dev creates PR when marking Pending Test
4. QA verifies on branch (checks out branch, runs tests, switches back)
5. QA marks Pending Ship
6. PM detects Pending Ship -> DM/PM ships -> Shipped

The PR exists but is not the review gate. The merge happens implicitly (or doesn't -- the branch just sits there).

### 2.2 New behavior (Branch Workflow: yes, PR Flow: yes)

1. Dev works on branch `squidsquad/skill/NNN` -- **no change**
2. Dev commits code to branch, state to main -- **no change**
3. Dev creates PR when marking Pending Test -- **no change**
4. QA verifies on branch -- **no change**
5. QA marks **Pending Review** (new status) instead of Pending Ship -- **CHANGE**
6. Human reviews PR on GitHub -- approve, request changes, comment
7. Human merges PR when satisfied
8. PM/QA detects merge via Step 6b/5b -> transitions to Pending Ship -- **already exists**
9. DM/PM ships -> Shipped

### 2.3 PR template improvements

Current PR body is minimal:
```
## #[NUMBER]

[acceptance criteria]

Status: Pending Test
```

Recommended PR body for human review:
```markdown
## #[NUMBER] -- [title]

Closes #[NUMBER]

### Changes
[Brief description of what changed and why]

### Acceptance Criteria
[Copied from task]

### QA Status
- [ ] QA verification pending

### Test Results
- Unit tests: [pass/fail count]
- Smoke tests: [pass/fail or N/A]
```

The `Closes #[NUMBER]` line auto-closes the GitHub Issue when the PR is merged -- this is a GitHub native feature that aligns with the Shipped status transition.

### 2.4 Dev agent template changes needed

**File**: `references/sub-skills/common/git-commit.md`

The PR creation block (item 3 under Branch Workflow: yes) needs:
- Richer PR body template (see above)
- No behavioral change to when PRs are created -- this already happens at Pending Test

**No other dev changes needed.** The dev agent's job ends at creating the PR and marking Pending Test. Everything after that is QA/PM territory.

---

## 3. QA Interaction

### 3.1 Current QA flow

QA verifies on branch -> marks Pending Ship directly.

### 3.2 New QA flow when PR Flow enabled

QA verifies on branch -> instead of Pending Ship, QA:
1. Comments QA results on the **PR** (not just the issue) so the human reviewer sees them
2. Marks the tracker item as **Pending Review** (new intermediate status)
3. Adds a PR review via `gh pr review [N] --approve` (or `--request-changes` on failure)

This gives the human reviewer:
- QA results visible directly on the PR
- A green check from QA's approval review
- Clear signal that the code is QA-verified and ready for human review

### 3.3 QA commenting on PR vs issue

Both. QA should:
- Comment on the **issue** (tracker) for status transitions (existing behavior)
- Comment on the **PR** with QA results summary so the human sees it during review
- Use `gh pr review` for the formal approve/request-changes signal

### 3.4 QA template changes needed

**File**: `references/sub-skills/qa-specific/verification.md`

In Steps 4-5 (verify issues/tasks), when PR Flow is enabled:
- After verification passes: add `gh pr review [PR_NUMBER] --approve --body "QA verified -- zero gaps."` before transitioning
- After verification fails: add `gh pr review [PR_NUMBER] --request-changes --body "QA FAIL: [findings]"` and transition back to In Progress
- New status: transition to `pending-review` instead of `pending-ship`

**File**: `references/sub-skills/qa-specific/verification.md` Step 5b already handles PR monitoring -- no changes needed there.

---

## 4. PM Step 6b Changes

### 4.1 Current Step 6b behavior

Already handles:
- Merged PR -> Pending Ship
- Closed without merge -> In Progress
- New comments -> relay to tracker
- Changes requested -> In Progress

### 4.2 Changes needed

Minimal. Step 6b already does the right things. The only addition:

- **Detect approved reviews**: When a PR has an "approved" review from the human (not from QA), log it:
  ```
  > [YYYY-MM-DD HH:MM] **pm**: PR [URL] approved by [human]. Awaiting merge.
  ```
  This is informational -- no status change needed (it stays Pending Review until merge).

- **PR review detection command**:
  ```bash
  gh pr view [N] --json reviews --jq '.reviews[] | select(.state == "APPROVED") | .author.login'
  ```

### 4.3 PM Step 6b template changes needed

**File**: `references/sub-skills/pm-specific/pr-flow.md`

Add to the "For each PR" block:
- New bullet: **If open with approved review from human**: append Discussion entry noting approval, no status change.
- Existing "If merged" bullet: works as-is. Transitions to Pending Ship which triggers delivery.

---

## 5. PR Body Content

### 5.1 Recommended PR template

```markdown
## #[NUMBER] -- [title]

Closes #[NUMBER]

### Summary
[1-3 sentence description of what this change does and why]

### Acceptance Criteria
[Copied from task body -- checklist format]

### Files Changed
[Auto-generated by gh pr create, or manually listed]

### QA Status
- [ ] Awaiting QA verification

### Notes for Reviewer
[Any context the human needs: migration steps, config changes, known limitations]
```

### 5.2 QA updates the PR body

After QA verifies, QA adds a comment (not body edit) with results:
```markdown
## QA Results

- **Status**: PASS (zero gaps)
- **Test Plan**: FEAT-SKILL-NNN-TEST-PLAN.md
- **Results**: FEAT-SKILL-NNN-QA-RESULTS.md
- **Tests**: [N] passed, [N] failed
- **Findings**: None
```

### 5.3 Auto-linking

The `Closes #[NUMBER]` line in the PR body auto-closes the issue on merge. This is useful but needs coordination with the tracker status flow -- if the issue auto-closes, the tracker label should also transition. PM Step 6b already handles this: it detects merged PRs and transitions to Pending Ship.

**Caution**: GitHub auto-close sets the issue to "closed" state. The tracker uses labels for status (`status:pending-ship`, `status:shipped`). These are independent. PM Step 6b should:
1. Detect the merge
2. Set `status:pending-ship` label
3. Proceed with delivery

The auto-close is a bonus -- it ensures the issue is closed even if PM misses a cycle.

---

## 6. Human Review Flow

### 6.1 What the human sees

On GitHub:
1. A PR from branch `squidsquad/skill/NNN` to `main`
2. PR title: `skill: #NNN -- [title]`
3. PR body with acceptance criteria, summary, QA status
4. QA's review (approved or changes-requested)
5. QA's comment with detailed results
6. File diff showing all code changes
7. Commit history on the branch

### 6.2 Human actions

- **Approve**: Click "Approve" in GitHub review UI. This does not merge.
- **Request changes**: Click "Request changes" with feedback. PM/QA detect this and transition back to In Progress.
- **Comment**: Add inline or general comments. PM/QA relay these to tracker Discussion.
- **Merge**: Click "Merge pull request" (or squash-merge, rebase-merge). This triggers the merge event that PM detects.

### 6.3 Merge strategy recommendation

**Squash and merge** is recommended for SquidSquad PRs:
- Creates a single clean commit on main
- Preserves the branch history in the PR for reference
- The squash commit message should be `[role]: #[NUMBER] -- [title]`

This can be configured as the default merge strategy in GitHub repo settings.

### 6.4 What triggers after merge

1. PM Step 6b detects the merged PR
2. PM transitions tracker item to Pending Ship
3. PM Step 6d (delivery fallback, if no DM) or DM handles delivery
4. PM Step 6e runs `compose.py deploy-all` if `references/` was touched
5. PM Step 6e deletes the merged branch (cleanup)

---

## 7. Config Changes

### 7.1 Toggle PR Flow

Change in `config.md`:
```markdown
## PR Flow

- **Enabled**: yes
```

This activates:
- PM Step 6b (PR monitoring)
- QA Step 5b (PR monitoring)
- New QA behavior: PR review + Pending Review status

### 7.2 New status label needed

Add `status:pending-review` to the label taxonomy. This sits between `pending-test` and `pending-ship`:

```
approved -> in-progress -> pending-test -> pending-review -> pending-ship -> shipped
```

The `pending-review` status means:
- QA has verified the code (zero gaps)
- A PR exists and is open
- The human has not yet reviewed/merged

### 7.3 Tracker transition authorization

Update the transition authorization table:
- `pending-test` -> `pending-review` -- **QA** (new)
- `pending-review` -> `in-progress` -- **PM or QA** (if human requests changes)
- `pending-review` -> `pending-ship` -- **PM** (on merge detection)

### 7.4 Optional: merge strategy config

Could add to config.md:
```markdown
## PR Flow

- **Enabled**: yes
- **Merge Strategy**: squash
- **Auto-delete Branch**: yes
```

But this is likely over-engineering for v1. The human controls merge strategy on GitHub. Branch cleanup can be handled by PM Step 6e.

### 7.5 No other config changes needed

The `Branch Workflow: yes` config is already set and is a prerequisite for PR Flow. The `PR Flow` toggle is the only new config needed.

---

## 8. Integration with #375 (Branch Workflow)

### 8.1 Full end-to-end flow

```
1. PM creates task, runs intake (RESEARCH, CONTEXT, TEST-PLAN)
2. Human approves task -> status: Approved
3. Dev picks up task -> status: In Progress
4. Dev creates branch squidsquad/skill/NNN
5. Dev implements on branch, commits code to branch, state to main
6. Dev runs tests on branch
7. Dev marks Pending Test, creates PR, comments PR URL on issue
8. QA checks out branch, runs verification
9a. QA PASS: QA approves PR, marks Pending Review, comments results on PR
9b. QA FAIL: QA requests changes on PR, marks In Progress, comments findings
10. Human reviews PR on GitHub
10a. Human approves + merges -> PM detects merge -> Pending Ship
10b. Human requests changes -> PM/QA detect -> In Progress (back to step 5)
10c. Human comments -> PM/QA relay to tracker
11. PM/DM handles delivery -> Shipped
12. PM runs compose.py deploy-all if references/ was modified
13. Branch deleted (auto-delete on merge, or PM cleanup)
```

### 8.2 Branch Workflow is a prerequisite

PR Flow only makes sense when Branch Workflow is enabled. If Branch Workflow is `no`, there are no branches to create PRs from. The config should enforce this:
- If `PR Flow: yes` and `Branch Workflow: no`, log a warning and treat PR Flow as `no`.

### 8.3 What changes from #375

#375 established:
- `commit-code` and `commit-state` split in git_ops.py
- Branch naming: `squidsquad/<role>/<number>`
- QA branch checkout for verification
- Post-merge recompose (Step 6e)

#246 adds:
- PR as the human review gate (not just a record of the branch)
- New `pending-review` status between QA pass and merge
- QA comments on PRs (not just issues)
- QA uses `gh pr review` for formal review signals
- PM detects human review actions (approve, request changes, comments)
- Human merges (not agent)

---

## 9. Side Effects, Edge Cases, Upgrade Path

### 9.1 Side Effects

1. **Slower delivery velocity**: Every feature now requires human review before merge. This is intentional -- the whole point of #246 is human oversight. Impact depends on human responsiveness.
2. **PR accumulation**: If the human is slow to review, PRs pile up. Agents continue working on other tasks, but branches diverge from main over time.
3. **QA double-duty**: QA now interacts with both the issue tracker and the PR. More work per verification cycle, but the information is richer.
4. **GitHub notification volume**: Human gets PR notifications for every feature/bug. This is the desired signal.

### 9.2 Edge Cases

1. **Human merges without QA verification**: The PR exists before QA verifies (created at Pending Test). A human could merge it early. PM detects the merge and transitions to Pending Ship, skipping QA. Mitigation: branch protection rules requiring QA approval before merge.
2. **QA rejects after human approves**: Human approves the PR, then QA finds issues on the next cycle. QA should request changes on the PR (overriding the human approval) and transition back to In Progress. The human sees the QA feedback.
3. **Dev pushes more commits after PR creation**: Dev fixes QA feedback, pushes to the same branch. The PR automatically updates. QA re-verifies. No new PR needed.
4. **Merge conflicts**: The PR shows merge conflicts if main diverges. Human or dev resolves. If dev resolves, they rebase the branch and force-push (PR updates).
5. **PR for bugs vs features**: Both go through PRs when PR Flow is enabled. For trivial bugs, this may feel heavy. Could add a config option for "PR only for tasks, direct-merge for bugs" but this adds complexity. Recommend starting with PRs for everything.
6. **Auto-close vs label transition**: GitHub auto-close (from `Closes #N`) sets issue state to closed. Tracker label (`status:pending-ship`) is set by PM. These are independent but should align. If auto-close fires but PM hasn't run yet, the issue is closed but labels say `pending-review`. PM's next cycle catches up.

### 9.3 Upgrade Path

1. **Config change**: `PR Flow: Enabled: no` -> `yes` (human sets this)
2. **New label**: Create `status:pending-review` label on the repo
3. **Template updates**: Recompose all roles with updated sub-skills
4. **No script changes**: `git_ops.py` already has `pr-create`. No new Python code needed.
5. **Branch protection** (optional): Set up GitHub branch protection on `main` requiring PR review before merge. This enforces the PR flow at the Git level.
6. **Backward compatible**: Setting `PR Flow: no` restores the current behavior. No breakage.

### 9.4 Upgrade steps for squidsquad-upgrade

1. Add `status:pending-review` label: `gh label create "status:pending-review" --color "1d76db" --description "QA verified, awaiting human PR review"`
2. Update `config.md`: Set `PR Flow: Enabled: yes` (prompt user)
3. Update sub-skill source files (see Section 10)
4. Recompose: `python references/scripts/compose.py deploy-all`

---

## 10. Files to Change

### 10.1 Sub-skill source files

| File | Change | Scope |
|------|--------|-------|
| `references/sub-skills/common/git-commit.md` | Richer PR body template | Small |
| `references/sub-skills/qa-specific/verification.md` | Add `gh pr review`, comment on PR, use `pending-review` when PR Flow enabled | Medium |
| `references/sub-skills/pm-specific/pr-flow.md` | Add human-approved detection, minor wording | Small |
| `references/sub-skills/pm-specific/testing-and-verification.md` | Add `pending-review` transition when PR Flow enabled | Small |
| `references/sub-skills/common/tracker-protocol.md` | Add `status:pending-review` to label taxonomy and transition table | Small |

### 10.2 Config

| File | Change |
|------|--------|
| `.squidsquad/config.md` | Toggle `PR Flow: Enabled` from `no` to `yes` |

### 10.3 No script changes

`git_ops.py` and `config.py` already support all needed operations. No new Python code.

---

## 11. Open Questions

- **Q1**: Should `pending-review` be a new status, or should we reuse `pending-test` with a "PR open" signal? A new status is cleaner but adds to the label taxonomy. **Recommendation**: New status. The semantic difference is real -- QA has verified, human has not reviewed.

- **Q2**: Should QA use `gh pr review --approve` or just comment? Formal reviews integrate with GitHub's branch protection. **Recommendation**: Use formal reviews. This enables branch protection rules requiring QA approval.

- **Q3**: Should the `Closes #N` auto-close be used? It is convenient but creates a race with PM's label-based tracking. **Recommendation**: Use it. PM catches up within one cycle. The auto-close is a safety net.

- **Q4**: Should bugs also go through PR review, or only tasks? **Recommendation**: Start with everything through PRs. Add a bypass for trivial bugs later if the human finds it too heavy.

- **Q5**: Should branch protection rules be set up automatically during upgrade? **Recommendation**: No. Document it as a recommended step. Branch protection is a repo-level setting that the human should control.
