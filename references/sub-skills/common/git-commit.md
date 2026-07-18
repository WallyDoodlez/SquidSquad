---
slot: instructions
ordinal: 10
---

### Step 5 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Branch-per-feature workflow is the only mode (#9478). Split commits into code (feature branch) and state (main):

1. **If working on a task** (status changed to `Pending Test` or still `In Progress`):
   - Commit code changes to the feature branch (use the branch name from task-begin output):
     ```bash
     python references/scripts/git_ops.py commit-code [ROLE] [BRANCH] "[brief description]"
     ```
   - Comment the branch name on the issue (first commit only):
     ```bash
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Working on branch [BRANCH]."
     ```

2. **Always** commit state changes (.squidsquad/) to main:
   ```bash
   python references/scripts/git_ops.py commit-state [ROLE] "[brief description of state changes]"
   ```

3. **When marking Pending Test**, create a PR from the feature branch.

   → run sub-skill: `pr-protocol` — canonical owner of PR creation. The locked rule (`git_ops.py pr-create`, not bare `gh pr create`), the structured-vs-simple body shapes, and the planning-review carve-out all live there. This step is the commit-flow handoff to PR creation.

   Read `PR Flow` from config:
   ```bash
   python references/scripts/config.py get pr-flow
   ```

   Pick the body shape per `pr-protocol`'s **Body shape** section (`PR Flow yes` → structured; `PR Flow no` → simple). Invoke `git_ops.py pr-create` with that body. For `PR Flow yes`, post a Code Review Summary as a PR comment after creation:

   ```bash
   gh pr comment [PR_NUMBER] --body "## Code Review Summary

   **What changed**: [brief description]
   **Why**: [rationale]
   **Key decisions**: [any notable choices]
   **Files touched**: [list of key files]"
   ```

   Record the PR URL in the tracker Discussion:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "PR opened: [URL]. Branch: [BRANCH]. Status → Pending Test."
   ```

4. **When PR Flow `yes`**: monitor PR comments each cycle for human feedback:
   ```bash
   gh pr view [PR_NUMBER] --json comments,reviews,isDraft
   ```
   - If human requested changes via review: **convert the PR to draft first** before making any code changes:
     ```bash
     gh pr ready --undo [PR_NUMBER]
     ```
     Then fix the issues and push to the branch.
   - If human posted new comments: read and address them (fix code, answer questions, reply on PR)
   - A PR must NEVER be in ready state while the agent is actively pushing commits to it.
   - After all fixes are pushed and the task moves to pending-test, `cycle_post.py` commits and creates the PR first, then the status transition triggers auto-conversion of the draft PR to ready.

5. **When PR Flow `yes`**: check own open PRs for merge conflicts and resolve via merge:
   ```bash
   gh pr list --search "squidsquad/" --state open --json number,headRefName,mergeable --limit 10
   ```
   For each PR with `mergeable` = `CONFLICTING` on a branch matching `squidsquad/*`:
   ```bash
   git fetch origin
   git checkout [BRANCH_NAME]
   git merge origin/[WORKING_BRANCH]
   ```
   - **Merge succeeds (no conflicts)**: push and log:
     ```bash
     git push origin [BRANCH_NAME]
     git checkout [WORKING_BRANCH]
     ```
     Log in iteration summary: `Merged [WORKING_BRANCH] into [BRANCH_NAME] — conflict resolved.`
   - **Merge has code conflicts**: abort and log (PM/verifier will handle):
     ```bash
     git merge --abort
     git checkout [WORKING_BRANCH]
     ```
     Log: `Merge of [WORKING_BRANCH] into [BRANCH_NAME] failed — manual conflict resolution needed.`
   - Only merge into branches for your own tasks — never touch other agents' PRs.
   - Skip this step when PR Flow is off or no open PRs exist.

### Test-file placement (#13551)

When a fix needs a regression test, **prefer a new dedicated file** — `tests/test_<issue-number>_<short-name>.py` — over appending a new test class to an existing shared file's tail (e.g. `test_git_ops.py`, `test_harness.py`). Two independent branches that each append a class after the same anchor point (commonly the last class in the file) cannot be auto-ordered by git: neither branch has seen the other's insertion, so the merge reports `mergeable=CONFLICTING/DIRTY` purely from insertion-position collision — not from any real code conflict. This has recurred across sibling branches worked in quick succession off the same file (e.g. the `git_ops.py` PR-lifecycle cluster). A dedicated per-issue file sidesteps the class of conflict entirely: two new files never collide at the git level. Only extend an existing shared test file (adding a class to it, not a new file) when the test is a direct, tightly-scoped addition to that file's own existing coverage of the same function — not merely "this fix happens to touch a function that file already tests."
