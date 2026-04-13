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
   ```bash
   python references/scripts/git_ops.py pr-create "[ROLE]: #[NUMBER] — [title]" "## #[NUMBER]\n\n[acceptance criteria]\n\nStatus: Pending Test"
   ```
   Record the PR URL in the tracker Discussion:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "PR opened: [URL]. Branch: squidsquad/[ROLE]/[NUMBER]. Status → Pending Test."
   ```

**If `no`** (default — direct-to-main workflow):

```bash
python references/scripts/git_ops.py commit-push [ROLE] "[brief description of work done this cycle]"
```
