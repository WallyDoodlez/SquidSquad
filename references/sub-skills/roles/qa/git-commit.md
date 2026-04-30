### Step 8 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Check Branch Workflow setting:
```bash
python references/scripts/config.py get branch-workflow
```

**If `yes`** AND you verified a specific issue/task this cycle (#[NUMBER]):

QA verification results go on the issue's existing feature branch (if it exists). State changes go on main.

1. If a feature branch exists for the verified item:
   ```bash
   python references/scripts/git_ops.py commit-code qa squidsquad/skill/[NUMBER] "[brief QA results]"
   ```

2. Commit state changes (.squidsquad/) to main:
   ```bash
   python references/scripts/git_ops.py commit-state qa "[brief summary — verified #NUMBER]"
   ```

**If `no`** (default) OR no specific issue was verified:

```bash
python references/scripts/git_ops.py commit-push qa "[brief summary — e2e results, bugs filed, features verified]"
```
