### Self-Restart (Sentinel-Based)

At the end of each cycle (after Step Done), check whether a restart is needed. **Never restart mid-cycle** — complete the full Ralph Loop first.

**Restart triggers** (check in order):

1. **Context pressure**: If context usage exceeded the threshold during Step 1b this cycle, trigger a restart to get a fresh context window.
2. **Template change**: If `.squidsquad/[ROLE]/CLAUDE.md` mtime is newer than the session start time, trigger a restart to pick up updated instructions.

**Pre-restart checklist** (all steps required before writing the sentinel):

1. Save working state to `.squidsquad/[ROLE]/working-state.md`.
2. Commit and push all pending changes.
3. Write status bar: `restarting|Self-restart — [reason]`
4. Print: `[🦑 HH:MM:SS] Self-restart triggered: [reason]. State saved. Restarting...`

**Trigger the restart**:

Write the sentinel file with the reason:

```bash
echo "[reason]" > .squidsquad/[ROLE]/.restart
```

The boot script wrapper detects this sentinel, kills the current Claude process, deletes the sentinel, and starts a fresh session. The new session reads `working-state.md` on startup (Step 1c) and resumes where it left off.

**Safety rules**:

- Never write `.restart` mid-cycle — only after the cycle-complete marker.
- Never write `.restart` if working state has uncommitted changes — commit first.
- The sentinel is deleted by the boot script after restart — if it persists, the boot script did not detect it (check boot script version).
- Maximum 3 self-restarts per hour (tracked in `.squidsquad/[ROLE]/restart-log.txt`). If exceeded, skip the restart and print a warning. This prevents infinite restart loops.
