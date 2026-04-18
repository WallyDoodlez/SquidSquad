### Step 7 — Log Iteration

Print: `[🦑 HH:MM:SS] Logging iteration...`

**Every cycle writes a log entry** — active or quiet. Use the cycle script:

```bash
# Active cycle (work was done):
python references/scripts/cycle.py log-iteration qa [N] \
  --work "[comma-separated summary of work done]" \
  --notes "[anything notable]"

# Quiet cycle (no actionable work):
python references/scripts/cycle.py log-iteration qa [N] --quiet \
  --notes "[why quiet, e.g. 'No pending-test items']"

# Clean up old logs (keeps most recent 20)
python references/scripts/cycle.py cleanup-iterations qa
```

The script writes a unified format with Date, Type (active/quiet), Work Summary, and Notes. Quiet entries are condensed (2-3 lines).
