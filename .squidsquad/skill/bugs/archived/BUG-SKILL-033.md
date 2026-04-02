## BUG-SKILL-033 — DM role is treated as required but should be optional with PM fallback

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: FEAT-SKILL-035 designed the DM role as "hardcoded, always present." However, the DM role should be optional. When no DM agent is present (no `dm/` directory, no DM in config, or DM not running), PM must automatically activate DM functionality and perform all delivery work itself — CHANGELOG entries, version bumps, git tags, releases, user-facing docs. This is not just "treat Pending Ship as Shipped" (skip delivery) — PM must actually DO the delivery work when DM is absent. The PM template needs a DM-presence check that enables/disables its delivery capabilities.
- **Steps to Reproduce**:
  1. Install SquidSquad without starting a DM agent
  2. Ship a feature — it reaches Pending Ship
  3. No agent picks it up for delivery because PM was told it has zero delivery responsibilities
- **Expected**: PM detects DM is absent and performs delivery work itself (CHANGELOG, version bump, user-facing docs)
- **Actual**: PM does nothing with Pending Ship items except note them. Delivery stalls.

### Discussion

> [2026-03-30 03:30] **pm/qa**: Filed from human report. Human clarified: DM is optional, not required. When DM is absent, PM automatically takes over all delivery responsibilities. This changes the FEAT-035 design — PM needs a DM-presence check that activates its built-in delivery capabilities. The current "fallback" in the PM template (treat Pending Ship as Shipped) is insufficient — it skips delivery instead of doing it.
> [2026-03-30 12:40] **skill-lead**: Fixed by adding new Step 6d (PM Delivery Fallback) to PM template. When `.squidsquad/dm/` doesn't exist, PM now performs full delivery: docs updates, CHANGELOG prep, config/migration checks, marking Shipped, and version bump check with full bump sequence. Removed old "treat as Shipped" inline fallback from Steps 6/6b. Updated both `references/agent-instructions.md` and live `.squidsquad/pm/CLAUDE.md`. Status → Fixed.
> [2026-03-30 13:00] **pm/qa**: Verified — Step 6d PM Delivery Fallback fully implemented. DM presence check via dm/ directory, full delivery pipeline (docs, CHANGELOG prep, config, version bump), delivery:skip handling. Live PM CLAUDE.md updated. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
