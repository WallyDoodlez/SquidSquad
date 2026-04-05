### Step 4 — Log Iteration (skip on quiet cycles)

If no bugs were fixed and no features were progressed this cycle (and no improvement scan was triggered), this is a **quiet cycle**. Produce no text output — skip silently to Step 6 (Done). The status bar shows the loop is still running.

Otherwise, print: `[🦑 HH:MM:SS] Logging iteration...`

Use the cycle script to create and clean up logs:

```bash
# Create iteration log
python references/scripts/cycle.py log-iteration [ROLE] [N] \
  --bugs "[list or none]" --features "[list or none]" \
  --tests "[passed/failed]" --notes "[anything notable]"

# Clean up old logs (keeps most recent 20)
python references/scripts/cycle.py cleanup-iterations [ROLE]
```
