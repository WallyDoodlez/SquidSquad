## FEAT-SKILL-050 — Urgent cycle trigger: force any agent to start a cycle immediately

- **Priority**: High
- **Status**: On Hold
- **Requested By**: human
- **Description**: Allow any agent (or the human) to trigger an immediate cycle on another agent without waiting for the next scheduled interval. Use case: QA finds a broken implementation and needs the dev agent to fix it now, not in 30 minutes. Currently agents only work on their scheduled cron interval — there's no way to say "hey dev, start working now."
- **How It Could Work**:
  - Agent writes a trigger file (e.g. `.squidsquad/<target-role>/trigger`) with a reason
  - Target agent checks for trigger file at cycle start (Step 1) — if present, it was woken up early
  - The trigger mechanism needs to actually interrupt the cron wait — options:
    1. **File-based polling**: Target agent polls trigger file every N seconds between cycles (lightweight but adds a polling loop)
    2. **Cron manipulation**: Triggering agent creates a one-shot cron for the target (`CronCreate` with immediate fire) — but this only works in the same Claude session
    3. **Cross-clone file signal**: Since FEAT-047 adds `.local-config` with clone paths, the triggering agent could write a trigger file directly to the target's clone
  - Human can also trigger manually: "tell skill to start now" → PM writes trigger
- **Acceptance Criteria**:
  - [ ] Any agent can trigger an immediate cycle on any other agent
  - [ ] Human can trigger via conversation with PM ("tell dev to work on this now")
  - [ ] Target agent starts a new cycle within seconds, not waiting for next interval
  - [ ] Trigger includes a reason/context (what to prioritize)
  - [ ] Works across separate clones (leverages .local-config paths from FEAT-047)
  - [ ] No API calls needed (local file-based)
  - [ ] SKILL.md, agent-instructions.md updated

### Discussion

> [2026-03-31 02:10] **pm/qa**: Filed from human request. Human wants urgent work handled immediately, not waiting for the 30-minute cycle. Example: QA finds broken implementation → tell dev to fix now. Cross-clone trigger files via .local-config paths (FEAT-047 dependency). Status: Pending — awaiting human approval.
> [2026-03-31 04:30] **pm/qa**: Human approved. Status → Planning. Beginning intake process.
> [2026-03-31 05:30] **pm/qa**: Research complete. Discussion revealed the core problem requires agent concurrency/yielding (file locking, claim protocol, separate clones for parallel work) — significantly more complexity than the trigger signal itself. Human decided to put On Hold — manual triggering is sufficient for now. Status → On Hold.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
