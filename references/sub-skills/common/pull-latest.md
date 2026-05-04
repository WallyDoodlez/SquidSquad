### Step 1 — Pull Latest

Print: `[🦑 HH:MM:SS] Pulling latest...`

```bash
python references/scripts/git_ops.py pull
```

The script handles stash/pop automatically if there are unstaged changes. If there is a merge conflict in a tracker file, resolve it by keeping both versions — append the conflicting section below the existing one. Never discard entries.
