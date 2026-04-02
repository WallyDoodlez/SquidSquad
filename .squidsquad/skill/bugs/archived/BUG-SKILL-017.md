## BUG-SKILL-017 — No process to update README.md and developer docs when features ship

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The skill-lead's Ralph Loop includes updating CHANGELOG.md when implementing features (Step 3.7), but there is no equivalent step to update **README.md** or other developer-facing documentation. The README was rewritten once in FEAT-SKILL-014 but will drift out of date as new features ship.

  **Fix needed:**
  1. Add a step to the skill-lead's Ralph Loop (after CHANGELOG update) to check if the change affects user-facing behavior documented in README.md
  2. If so, update README.md to reflect the new functionality
  3. Same applies to any other developer documentation (e.g., SKILL.md's feature descriptions, setup instructions)
  4. PM QA pass should verify that README.md is consistent with shipped features

  This applies to the dev agent template in `references/agent-instructions.md` and the generated `skill/CLAUDE.md`.

- **Steps to Reproduce**:
  1. Ship a user-visible feature (e.g., auto-versioning)
  2. Check README.md — it won't mention the new feature
- **Expected**: README.md and developer docs updated as part of shipping
- **Actual**: Only CHANGELOG.md updated; README.md drifts out of date

### Discussion

> [2026-03-28 08:25] **pm/qa**: Reported by human. README and developer docs need to stay in sync with shipped features. Currently only CHANGELOG gets updated during implementation.
> [2026-03-28 08:50] **skill-lead**: Fixed. Added Step 8 "Update docs" to dev agent template in agent-instructions.md (between smoke tests and status update) — checks if change affects user-facing behavior and updates README.md + SKILL.md accordingly. Also updated generated skill/CLAUDE.md. Status → Fixed.
> [2026-03-28 08:55] **pm/qa**: Verified. Dev template line 147 has Step 8 "Update docs" — checks user-facing behavior, updates README.md + SKILL.md. Generated skill/CLAUDE.md line 106 matches. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
