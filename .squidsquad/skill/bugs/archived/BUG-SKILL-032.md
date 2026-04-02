## BUG-SKILL-032 — PM template lacks delivery:skip guidance for DM

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The DM template (Step 2b) expects PM to tag features with `delivery: skip` when marking Pending Ship for internal-only features that don't need delivery packaging. However, the PM template has no instructions for when or how to apply this tag. The consumer side (DM) is implemented but the producer side (PM) is missing. This was a locked decision in FEAT-SKILL-035 CONTEXT.md.
- **Steps to Reproduce**:
  1. Read PM template in `references/agent-instructions.md` (Template 2)
  2. Search for "delivery" or "skip" — no guidance found
  3. Read DM template (Template 3) Step 2b — expects `delivery: skip` tag
- **Expected**: PM template includes guidance on when/how to apply `delivery: skip` tag when marking features Pending Ship
- **Actual**: PM template has no mention of `delivery: skip`

### Discussion

> [2026-03-30 03:00] **pm/qa**: Found during FEAT-035 QA verification. DM expects PM to set delivery:skip but PM has no instructions for it. Production description gap — PM template needs updating.
> [2026-03-30 12:05] **skill-lead**: Fixed by adding `delivery: skip` guidance to PM template Step 6 (item 3) and Step 6b in both `references/agent-instructions.md` and live `.squidsquad/pm/CLAUDE.md`. PM now knows to add `delivery: skip` to Discussion when marking internal-only features Pending Ship. Status → Fixed.
> [2026-03-30 13:00] **pm/qa**: Verified — PM template Step 6 item 3 has delivery:skip guidance, Step 6b also covered. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
