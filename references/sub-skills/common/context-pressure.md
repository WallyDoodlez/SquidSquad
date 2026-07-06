---
slot: instructions
ordinal: 10
---

### Step 1b — Context Pressure Check

Print: `[🦑 HH:MM:SS] Checking context pressure...`

Read the real context pressure from disk. The statusline hook writes the actual `used_percentage` to `.squidsquad/[ROLE]/context-pressure` after every assistant message — agents should **read** this file, not fabricate values.

```bash
CTX_PCT=$(cat .squidsquad/[ROLE]/context-pressure 2>/dev/null || echo "0")
python references/scripts/config.py get context-threshold
```

Compare `CTX_PCT` against the threshold. If the file doesn't exist yet (first cycle, statusline not running), default to `0` and continue normally.

If context usage **exceeds the threshold**:
1. Compact your current working state into `.squidsquad/[ROLE]/working-state.md` (see Working State File below). This is a checkpoint — if the session crashes or is interrupted, the next session can resume from working state.
2. Commit and push all pending work.
3. Print: `[🦑 HH:MM:SS] Context pressure at [X]% — working state checkpointed. Continuing normally.`
4. **Continue the cycle normally.** Claude Code automatically compresses prior messages as context approaches limits, so the conversation can keep going indefinitely. At cycle end, `cycle_post.py` detects the exceeded threshold from `cycle-input.json` and exits with code 42, triggering a harness respawn.

If context usage is below threshold, continue normally.

> **Loop mode vs event mode (#13335).** The check above is the **loop-mode** path: it runs as Step 1b of each cycle and the actor that respawns you is `cycle_post.py` exit-42 at cycle end. In **event mode** there is no per-event `cycle_post.py`, so this step does not run — instead the **harness health poller** enforces the same `context-threshold` for you: roughly every 5 seconds it reads your `.squidsquad/[ROLE]/context-pressure` and, at/over threshold, flips your `intent` to `restarting` so you checkpoint at a task boundary and respawn with a fresh context window (see [[event-mode-contract]]). Keep `working-state.md` fresh at every task boundary either way — that checkpoint is what survives the respawn.
