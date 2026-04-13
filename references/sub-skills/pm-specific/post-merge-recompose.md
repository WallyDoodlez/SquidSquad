### Step 6e — Post-Merge Recompose (Branch Workflow)

Check Branch Workflow setting:
```bash
python references/scripts/config.py get branch-workflow
```

If `no`, skip this step.

Print: `[🦑 HH:MM:SS] Checking for merged branches...`

Detect recently merged `squidsquad/` branches:
```bash
git log --merges --oneline --since="2 hours ago" -- | grep -i "squidsquad/"
```

For each merged branch that touched files under `references/`:

1. Check if the merge modified templates or sub-skills:
   ```bash
   git diff HEAD~1 --name-only -- references/
   ```
2. If `references/` was modified, recompose all affected roles:
   ```bash
   python references/scripts/compose.py deploy-all
   ```
3. Comment on the associated issue:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role pm --message "Branch merged. Recomposed agent templates from updated references/."
   ```

If no merged branches touched `references/`, skip silently.
