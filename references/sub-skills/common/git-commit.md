### Step 5 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Check PR Flow setting:
```bash
python references/scripts/config.py get pr-flow
```

**If `yes`** and this cycle completed a feature or bug fix (status changed to `Pending Test`):

1. Create a branch and commit:
   ```bash
   python references/scripts/git_ops.py branch-create squidsquad/[type]-[ROLE]-[NNN]
   python references/scripts/git_ops.py commit-push [ROLE] "[brief description]"
   ```
2. Open a PR:
   ```bash
   python references/scripts/git_ops.py pr-create "[ROLE]: [FEAT/BUG-ID] — [title]" "## [FEAT/BUG-ID]\n\n[acceptance criteria]\n\nStatus: Pending Test"
   ```
3. Record the PR URL in the tracker Discussion:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "PR opened: [URL]. Status → Pending Test."
   ```
4. Switch back to main:
   ```bash
   python references/scripts/git_ops.py branch-switch main
   ```

**If `no`** (default) or this cycle only updated tracker files (no feature/bug completion):

```bash
python references/scripts/git_ops.py commit-push [ROLE] "[brief description of work done this cycle]"
```
