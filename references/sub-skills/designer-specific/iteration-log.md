### Step 3 — Log Iteration (skip on quiet cycles)

If no design work was done and no improvement scan was triggered this cycle, this is a **quiet cycle**. Produce no text output — skip silently to Step 5 (Done). The status bar shows the loop is still running.

Otherwise, print: `[🦑 HH:MM:SS] Logging iteration...`

Create `.squidsquad/designer/iterations/iter-N.md` (increment N from last log):

```markdown
# Designer Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Designs Progressed**: [list issue #numbers, or "none"]
- **Designs Completed**: [list issue #numbers, or "none"]
- **Quiet Cycles**: [consecutive count, or "0"]
- **Notes**: [anything notable]
```

After creating the log, clean up old iteration files: if more than 20 `iter-*.md` files exist in the iterations directory, delete the oldest ones.
