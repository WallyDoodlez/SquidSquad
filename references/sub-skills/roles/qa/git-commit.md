### Step 8 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Branch-per-feature workflow is the only mode (#9478). If you verified a specific issue/task this cycle (#[NUMBER]):

QA verification results go on the issue's existing feature branch (if it exists). State changes go on main.

1. If a feature branch exists for the verified item:
   ```bash
   python references/scripts/git_ops.py commit-code qa squidsquad/skill/[NUMBER] "[brief QA results]"
   ```

2. Commit state changes (.squidsquad/) to main:
   ```bash
   python references/scripts/git_ops.py commit-state qa "[brief summary — verified #NUMBER]"
   ```

If no specific issue was verified this cycle (smoke pass only, no per-issue work), commit directly to the working branch:

```bash
python references/scripts/git_ops.py commit-push qa "[brief summary — e2e results, bugs filed, features verified]"
```
