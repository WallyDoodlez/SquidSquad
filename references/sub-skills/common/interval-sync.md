---
slot: instructions
ordinal: 10
---

### Step 1d — Interval Sync

Read the iteration interval:
```bash
python references/scripts/config.py get interval
```

If it differs from the interval used when the current cron was created, another agent (or the human) changed the interval. Re-schedule:

1. Cancel the existing cron job (`CronDelete`).
2. Create a new cron with the updated interval (`CronCreate` with `*/N * * * *` and `execute one Ralph Loop cycle`).
3. Print: `[🦑 HH:MM:SS] Interval changed to [N]m — cron re-scheduled.`

If the interval matches, continue silently.
