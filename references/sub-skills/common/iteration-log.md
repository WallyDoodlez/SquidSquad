### Step 4 — Log Iteration (skip on quiet cycles)

If no bugs were fixed and no features were progressed this cycle (and no improvement scan was triggered), this is a **quiet cycle**. Produce no text output — skip silently to Step 6 (Done). The status bar shows the loop is still running.

Otherwise, print: `[🦑 HH:MM:SS] Logging iteration...`

Create `.squidsquad/[ROLE]/iterations/iter-N.md` (increment N from last log):

```markdown
# [ROLE_UPPER] Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Bugs Fixed**: [list issue #numbers, or "none"]
- **Features Progressed**: [list issue #numbers, or "none"]
- **Tests**: [passed/failed — brief note]
- **Notes**: [anything notable]
```

After creating the log, clean up old iteration files: if more than 20 `iter-*.md` files exist in the iterations directory, delete the oldest ones. Git history preserves them if ever needed.
