### Step 7 — Log Iteration (skip on quiet cycles)

If no QA issues were found, no issues were verified, no tasks were tested, and no improvement scan was triggered, this is a **quiet cycle**. Produce no text output — skip silently to Step 9 (Done). The status bar shows the loop is still running.

Otherwise, print: `[🦑 HH:MM:SS] Logging iteration...`

Create `.squidsquad/qa/iterations/iter-N.md`:

```markdown
# QA Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **E2E Tests**: [passed/failed — N tests, X failures / skipped]
- **Issues Filed**: [list IDs, or "none"]
- **Issues Verified**: [list IDs, or "none"]
- **Tasks Verified**: [list IDs, or "none"]
- **Agent Health**: [list each agent: healthy/stalled/unknown]
- **Notes**: [anything notable]
```

After creating the log, clean up old iteration files: if more than 20 `iter-*.md` files exist in the iterations directory, delete the oldest ones. Git history preserves them if ever needed.
