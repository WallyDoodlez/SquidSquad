### Step 1b — Context Pressure Check

Print: `[🦑] Checking context pressure...`

Check `context_window.used_percentage` from the status line JSON (available as the `$CONTEXT_USED` environment hint, or by reading the last status line output). Compare against the threshold in `config.md` (default 80%).

If context usage **exceeds the threshold**:
1. Compact your current working state into `.squidsquad/[ROLE]/working-state.md` (see Working State File below).
2. Commit and push all pending work.
3. Print: `[🦑] Context pressure at [X]% — exiting for fresh context. State saved to working-state.md.`
4. Exit the conversation. The boot script will restart you with a fresh context window.

If context usage is below threshold, continue normally.
