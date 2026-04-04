### Step 4 — Log Iteration (skip on quiet cycles)

If no human input was processed, no features were filed or progressed, and no improvement scan was triggered this cycle, this is a **quiet cycle**. Produce no text output — skip silently to Step 6 (Done). The status bar shows the loop is still running.

Otherwise, print: `[🦑 HH:MM:SS] Logging iteration...`

Create `.squidsquad/pm/iterations/iter-N.md`:

```markdown
# PM Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Human Check-in**: [summary of human input, or "no input"]
- **Features Filed**: [list IDs, or "none"]
- **Features Progressed**: [list IDs with status changes, or "none"]
- **Notes**: [anything notable for the team]
```

After creating the log, clean up old iteration files: if more than 20 `iter-*.md` files exist in the iterations directory, delete the oldest ones. Git history preserves them if ever needed.
