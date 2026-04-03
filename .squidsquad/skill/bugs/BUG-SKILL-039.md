## BUG-SKILL-039 — PM attempted to ship feature with open QA gaps

- **Severity**: High
- **Status**: Closed
- **Reported By**: human
- **Assigned To**: skill-lead
- **Description**: PM marked FEAT-SKILL-029 as `Pending Ship` despite the QA agent finding 6 documentation gaps in the vault-protocol. PM rationalized them as "protocol polish, not structural failures" and tried to ship with gaps noted for follow-up. This should NEVER happen — no feature ships with any open QA findings unless the human explicitly overrides.

  **Root cause**: The PM template does not enforce a strict "zero gaps" gate at the Pending Ship transition. The current verification logic allows PM to use judgment about which gaps are "blockers" vs "polish." This discretion must be removed.

  **Required fix**: Update the PM template (and QA template when QA owns verification) to enforce:
  1. ANY gap, ambiguity, missing documentation, or failed check found during verification = back to In Progress
  2. No "noted for follow-up" — all findings must be resolved before Pending Ship
  3. Only exception: human explicitly says "ship with these gaps" (must be recorded in Discussion)
  4. This applies to all QA findings — test case failures, documentation gaps, protocol ambiguities, missing edge case handling

- **Steps to Reproduce**:
  1. Verify a feature with an unbiased QA agent
  2. QA finds gaps (documentation, protocol, edge cases)
  3. PM marks Pending Ship anyway with "gaps noted"
- **Expected**: Feature stays at In Progress until all gaps are closed
- **Actual**: PM marked Pending Ship, human had to catch it and reject

### Discussion

> [2026-04-03 03:15] **pm/qa**: Filed from human. PM incorrectly tried to ship FEAT-SKILL-029 with 6 open gaps. Human caught it: "No shipping unless all gaps closed." This is a template enforcement issue — PM should not have discretion to classify gaps as non-blocking. Fix the verification gate in PM and QA templates.
> [2026-04-03 03:30] **skill-lead**: Fixed.
> [2026-04-03 04:00] **pm/qa**: Verified. Zero-gap gate present in PM (full + lean) and QA templates. Explicit: "ANY gap = back to In Progress", "Do NOT mark Pending Ship with gaps noted." Human override only. Composed output confirmed. Status → Closed. Added "Zero-gap gate" to both PM (pm-agent.md Step 6) and QA (qa-specific/verification.md Step 5) templates. ANY gap/finding = back to In Progress. Only exception: human explicit override recorded in Discussion. Regenerated agent-instructions.md. Status → Fixed.
