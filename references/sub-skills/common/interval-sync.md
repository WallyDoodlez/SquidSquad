### Step 1d — Interval Sync

Read `Iteration Interval > Minutes` from `.squidsquad/config.md`. If it differs from the interval used when the current cron was created, another agent (or the human) changed the interval. Re-schedule:

1. Cancel the existing cron job (`CronDelete`).
2. Create a new cron with the updated interval (`CronCreate` with `*/N * * * *` and `execute one Ralph Loop cycle`).
3. Print: `[🦑] Interval changed to [N]m — cron re-scheduled.`

If the interval matches, continue silently.
