### Step 9 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Check Branch Workflow setting:
```bash
python references/scripts/config.py get branch-workflow
```

**If `yes`** AND you created planning artifacts for a specific issue/task (#[NUMBER]):

1. Commit planning artifacts to a feature branch:
   ```bash
   python references/scripts/git_ops.py commit-code pm squidsquad/pm/[NUMBER] "[brief description]"
   ```

2. Commit state changes (.squidsquad/ iteration logs, working state) to main:
   ```bash
   python references/scripts/git_ops.py commit-state pm "[brief summary]"
   ```

**If `no`** (default) OR only state/coordination work was done (check-in, health check, quiet cycle):

```bash
python references/scripts/git_ops.py commit-push pm "[brief summary — e2e results, bugs filed, features verified]"
```
