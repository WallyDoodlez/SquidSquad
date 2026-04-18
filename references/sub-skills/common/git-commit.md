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
   python references/scripts/git_ops.py pr-create "[ROLE]: #[NUMBER] — [title]" "## #[NUMBER]\n\n[acceptance criteria]\n\nStatus: Pending Test"
   ```

   Record the PR URL in the tracker Discussion:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "PR opened: [URL]. Branch: squidsquad/[ROLE]/[NUMBER]. Status → Pending Test."
   ```

4. **When PR Flow `yes`**: monitor PR comments each cycle for human feedback:
   ```bash
   gh pr view [PR_NUMBER] --json comments,reviews
   ```
   - If human posted new comments: read and address them (fix code, answer questions, reply on PR)
   - If human requested changes via review: fix the issues and push to the branch
   - After pushing fixes, re-request review if appropriate

5. **Merge your PR when task reaches pending-ship**: Each cycle, check for your tasks at `pending-ship` with open PRs:
   ```bash
   python references/scripts/tracker.py list-tasks [ROLE] --status pending-ship
   ```
   For each pending-ship task with an open PR (and `Auto Merge: yes` in config, `type:task` not `type:issue`, no `merge:manual` label):
   ```bash
   gh pr list --search "squidsquad/[ROLE]/[NUMBER]" --state open --json number,headRefName,mergeable --limit 1
   python references/scripts/git_ops.py pr-merge [PR_NUMBER]
   ```
   On merge conflict: rebase onto main and retry. On success: comment on the issue.

**If `no`** (default — direct-to-main workflow):

```bash
python references/scripts/git_ops.py commit-push [ROLE] "[brief description of work done this cycle]"
```
