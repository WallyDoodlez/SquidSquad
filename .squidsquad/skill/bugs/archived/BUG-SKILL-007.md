## BUG-SKILL-007 — Boot script templates lack while-loop for multi-cycle execution

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Neither the SKILL.md boot script templates nor the generated boot scripts have a `while true` loop. The CHANGELOG for v0.5.1 claims "Boot scripts now own the loop via `while true` in the shell", but this was never actually implemented. Both `.sh` and `.ps1` templates run `claude -p` once and then exit. Since `claude -p` handles one Ralph Loop cycle and exits, the agent runs one cycle and dies. The boot scripts need a `while true` loop that restarts `claude -p` after each cycle, with a sleep interval between cycles.
- **Steps to Reproduce**:
  1. Read SKILL.md boot script templates (lines 365-410)
  2. Note there is no loop — just a single `claude` invocation
  3. Start a skill lead — it runs once and exits
- **Expected**: Boot scripts wrap `claude -p` in a `while true` / `while ($true)` loop with a sleep between iterations
- **Actual**: Single `claude -p` call, script exits after one cycle

### Discussion

> [2026-03-28 01:40] **pm/qa**: Found while investigating skill lead inactivity. CHANGELOG says the loop exists but templates don't have it. This affects all agents — both dev and PM boot scripts.
> [2026-03-28 01:45] **pm/qa**: Invalid — dev agents are interactive (`--continue`), so Claude handles the Ralph Loop internally. No external while loop needed. The CHANGELOG entry about `while true` is misleading but the current design (single interactive session) is correct. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
