# Working State

- **Task**: none
- **Status**: none
- **Last Processed Event ID**: 744e7492

## Pending Human Input
- (none)

## Notes
- 🎉 Harness RESTARTED with both fixes in main. Auto-start clean. All 4 agents 'skip: alive' — recovered via existing PIDs.
- HTTP variance: 7/10 probes <1s, 3/10 timeout at 3s. Selector loop prevents the cascade failure; remaining variance is performance not correctness.
- Cadence can drop back to 30min on next cycle. Event wakes now work between cycles.
- Approved queue: #9415 (32-bit id collision), #9478 (branch_workflow=off removal), #9398/#9386/#9387 (deferred subprocess scenarios).
- DM approved: #3 awaiting human greenlight.
- PR #8812 still hanging.
- Watch for harness stability past 30 min (the prior wedge horizon). If it stays clean, this is the real fix.
