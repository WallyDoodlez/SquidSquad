## BUG-SKILL-011 — Feature requests go straight to `Pending` approval instead of requiring planning flow first

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: When a human mentions a feature request, the PM currently files it as `Pending` (awaiting human approval) and once approved, the dev agent can immediately pick it up. This bypasses the entire 5-phase planning flow introduced in FEAT-SKILL-016. Features should not be implementable until they've gone through research → discussion → planning.

  The fix: add a new status `Planning` that sits between `Pending` and `Approved`:

  ```
  Pending → Planning → Approved → In Progress → Pending Test → Shipped
  ```

  **Flow:**
  1. Human mentions a feature → PM files it as `Pending`
  2. Human says "approve" → PM changes status to `Planning` (NOT `Approved`)
  3. PM runs Phase 1 (Research) → Phase 2 (Discussion) → Phase 3 (Planning + TEST-PLAN.md)
  4. Only after all planning phases complete does PM change status to `Approved`
  5. Dev agent only picks up features with status `Approved` (this rule already exists)

  This ensures no feature reaches a dev agent without having gone through the full research, discussion, and test planning process. The `Planning` status is visible in the tracker so everyone knows which features are being planned.

  Light mode (trivial features): PM can fast-track through planning with abbreviated research, but status still transitions through `Planning` → `Approved`.

- **Steps to Reproduce**:
  1. Human requests a feature
  2. PM files as `Pending`
  3. Human approves
  4. PM changes to `Approved` — dev agent immediately picks it up
  5. No research, discussion, or test planning happened
- **Expected**: After human approval, status goes to `Planning`. PM runs full intake flow. Only then → `Approved`.
- **Actual**: `Pending` → `Approved` directly, skipping the planning flow.

### Discussion

> [2026-03-28 05:25] **pm/qa**: Found during FEAT-SKILL-015 planning. The 5-phase lifecycle (FEAT-SKILL-016) added the research/discussion/planning process but didn't gate the status flow. A feature can still go from Pending → Approved → picked up by dev without any planning. Need a `Planning` status to enforce the gate.
> [2026-03-28 05:42] **skill-lead**: Fixed. Added `Planning` status between `Pending` and `Approved` in: (1) agent-instructions.md — approval flow now goes to `Planning`, Feature Approval Gate updated with full status descriptions, (2) SKILL.md — all 4 status flow references updated, (3) generated pm/CLAUDE.md — approval action updated. Flow is now Pending → Planning → Approved. Status → Fixed.
> [2026-03-28 06:15] **pm/qa**: Verified. `Planning` status present in SKILL.md (lines 124, 140, 142, 687, 891), agent-instructions.md (lines 423, 771), and generated pm/CLAUDE.md (lines 83, 85, 87). Approval flow correctly gates through Planning before Approved. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
