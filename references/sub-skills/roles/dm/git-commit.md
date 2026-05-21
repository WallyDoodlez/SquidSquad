### Step 5 — Commit and Push (skip on quiet cycles)

Print: `[🦑 HH:MM:SS] Committing and pushing...`

Branch-per-feature workflow is the only mode (#9478). If you worked on a specific issue/task this cycle (delivery for #[NUMBER]):

1. Commit delivery work (docs, CHANGELOG) to the feature branch:
   ```bash
   python references/scripts/git_ops.py commit-code dm squidsquad/dm/[NUMBER] "[brief description]"
   ```

2. Commit state changes (.squidsquad/) to main:
   ```bash
   python references/scripts/git_ops.py commit-state dm "[brief description of state changes]"
   ```

If no specific issue was worked on this cycle (quiet cycle, version bump only), commit directly to the working branch:

```bash
python references/scripts/git_ops.py commit-push dm "[brief description of delivery work done this cycle]"
```
