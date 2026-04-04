### Step 8 — Log Iteration (skip on quiet cycles)

If no QA issues were found, no bugs were verified, no features were shipped, no human input was processed, and no improvement scan was triggered this cycle, this is a **quiet cycle**. Produce no text output — skip silently to Step 10 (Done). The status bar shows the loop is still running.

Otherwise, print: `[🦑 HH:MM:SS] Logging iteration...`

Create `.squidsquad/pm/iterations/iter-N.md`:

```markdown
# PM/QA Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Human Check-in**: [summary of human input, or "no input"]
- **E2E Tests**: [passed/failed — N tests, X failures / skipped]
- **Bugs Filed**: [list IDs, or "none"]
- **Bugs Verified**: [list IDs, or "none"]
- **Features Shipped**: [list IDs, or "none"]
- **Agent Health**: [list each agent: healthy/stalled/unknown]
- **Notes**: [anything notable for the team]
```

After creating the log, clean up old iteration files: if more than 20 `iter-*.md` files exist in the iterations directory, delete the oldest ones. Git history preserves them if ever needed.
