### Step 1b — Context Pressure Check

Print: `[🦑 HH:MM:SS] Checking context pressure...`

Check `context_window.used_percentage` from the status line JSON (available as the `$CONTEXT_USED` environment hint, or by reading the last status line output). Compare against the threshold:

```bash
python references/scripts/config.py get context-threshold
```

If context usage **exceeds the threshold**:
1. Compact your current working state into `.squidsquad/[ROLE]/working-state.md` (see Working State File below). This is a checkpoint — if the session crashes or is interrupted, the next session can resume from working state.
2. Commit and push all pending work.
3. Print: `[🦑 HH:MM:SS] Context pressure at [X]% — working state checkpointed. Continuing normally.`
4. **Continue the cycle normally.** Claude Code automatically compresses prior messages as context approaches limits, so the conversation can keep going indefinitely. Do NOT exit the conversation — exiting kills the cron loop and there is no auto-restart mechanism.

If context usage is below threshold, continue normally.
