### Step 5 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Check Branch Workflow setting:
```bash
python references/scripts/config.py get branch-workflow
```

**If `yes`** (branch-per-feature workflow):

Split commits into code (feature branch) and state (main):

1. **If working on a task** (status changed to `Pending Test` or still `In Progress`):
   - Commit code changes to the feature branch:
     ```bash
     python references/scripts/git_ops.py commit-code [ROLE] squidsquad/[ROLE]/[NUMBER] "[brief description]"
     ```
   - Comment the branch name on the issue (first commit only):
     ```bash
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Working on branch squidsquad/[ROLE]/[NUMBER]."
     ```

2. **Always** commit state changes (.squidsquad/) to main:
   ```bash
   python references/scripts/git_ops.py commit-state [ROLE] "[brief description of state changes]"
   ```

3. **When marking Pending Test**, create a PR from the feature branch:

   Check PR Flow setting:
   ```bash
   python references/scripts/config.py get pr-flow
   ```

   **If PR Flow `yes`** — structured PR with review sections:
   ```bash
   python references/scripts/git_ops.py pr-create "[ROLE]: #[NUMBER] — [title]" "$(cat <<'PRBODY'
   Closes #[NUMBER]

   ### Summary
   [Brief description of what was implemented and why]

   ### Acceptance Criteria
   - [ ] [criterion 1]
   - [ ] [criterion 2]

   ### Changes
   - **Files**: [key files changed]
   - **What**: [what changed]
   - **Why**: [rationale and key decisions]

   ### QA Status
   - [ ] Unit tests passing
   - [ ] Smoke tests passing
   - [ ] Acceptance criteria met
   PRBODY
   )"
   ```

   After PR creation, post a code review summary as a PR comment:
   ```bash
   gh pr comment [PR_NUMBER] --body "## Code Review Summary

   **What changed**: [brief description]
   **Why**: [rationale]
   **Key decisions**: [any notable choices]
   **Files touched**: [list of key files]"
   ```

   **If PR Flow `no`** — simple PR (no review sections):
   ```bash
   python references/scripts/git_ops.py pr-create "[ROLE]: #[NUMBER] — [title]" "Closes #[NUMBER]\n\n## #[NUMBER]\n\n[acceptance criteria]\n\nStatus: Pending Test"
   ```

   Record the PR URL in the tracker Discussion:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "PR opened: [URL]. Branch: squidsquad/[ROLE]/[NUMBER]. Status → Pending Test."
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
   - After all fixes are pushed and the task moves to pending-test, the tracker auto-converts the PR back to ready.

5. **When PR Flow `yes`**: check own open PRs for merge conflicts and rebase:
   ```bash
   gh pr list --search "squidsquad/[ROLE]/" --state open --json number,headRefName,mergeable --limit 10
   ```
   For each PR with `mergeable` = `CONFLICTING` on a branch matching `squidsquad/[ROLE]/*`:
   ```bash
   git fetch origin
   git checkout [BRANCH_NAME]
   git rebase origin/[WORKING_BRANCH]
   ```
   - **Rebase succeeds**: force-push and log:
     ```bash
     git push --force-with-lease origin [BRANCH_NAME]
     git checkout [WORKING_BRANCH]
     ```
     Log in iteration summary: `Rebased [BRANCH_NAME] — conflict resolved.`
   - **Rebase has code conflicts**: abort and log (PM/QA will handle):
     ```bash
     git rebase --abort
     git checkout [WORKING_BRANCH]
     ```
     Log: `Rebase of [BRANCH_NAME] failed — manual conflict resolution needed.`
   - Only rebase own branches (`squidsquad/[ROLE]/*`) — never touch other agents' PRs.
   - Skip this step when PR Flow is off or no open PRs exist.

**If `no`** (default — direct-to-main workflow):

```bash
python references/scripts/git_ops.py commit-push [ROLE] "[brief description of work done this cycle]"
```
