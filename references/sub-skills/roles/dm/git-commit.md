### Step 5 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Check Branch Workflow setting:
```bash
python references/scripts/config.py get branch-workflow
```

**If `yes`** AND you worked on a specific issue/task this cycle (delivery for #[NUMBER]):

1. Commit delivery work (docs, CHANGELOG) to the feature branch:
   ```bash
   python references/scripts/git_ops.py commit-code dm squidsquad/dm/[NUMBER] "[brief description]"
   ```

2. Commit state changes (.squidsquad/) to main:
   ```bash
   python references/scripts/git_ops.py commit-state dm "[brief description of state changes]"
   ```

**If `no`** (default) OR no specific issue was worked on (quiet cycle, version bump only):

```bash
python references/scripts/git_ops.py commit-push dm "[brief description of delivery work done this cycle]"
```
