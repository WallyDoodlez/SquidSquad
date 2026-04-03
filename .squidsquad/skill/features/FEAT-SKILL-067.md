## FEAT-SKILL-067 — Vault Phase 6: Evaluation and tuning after real-world usage

- **Priority**: Low
- **Owner**: pm
- **Status**: Pending
- **Depends On**: FEAT-SKILL-066 (vault Phase 4) — all vault phases deployed and running for a while
- **Description**: After all vault phases (1-5) are deployed and the vault has been actively used across multiple cycles and features, come back to evaluate:

  1. **What got captured?** Review the vault contents — are the notes useful? High signal or noise? Are agents capturing the right things?
  2. **What's missing?** Are there patterns, decisions, or learnings that should have been captured but weren't? Gaps in the auto-remember triggers?
  3. **What's noise?** Are there low-value captures cluttering the vault? Is the rate limit (3/cycle) too high or too low?
  4. **Is it being used?** Are agents actually querying the vault during work? Is BRIEFING.md helping? Or is the vault a write-only graveyard?
  5. **Tune the skills**: Based on findings, adjust vault-remember triggers, reflection prompts, confidence thresholds, capture rate limits, search patterns, and BRIEFING.md content.
  6. **Template adjustments**: Do the note templates need new fields? Are some fields unused? Should the PARAG folder structure change?
  7. **End-of-cycle reflection quality**: Are the "what did I learn?" reflections producing real insights or generic observations?

  This is NOT a feature to build — it's a scheduled evaluation checkpoint. The output is tuning adjustments filed as bugs/features against the vault skills.

- **Acceptance Criteria**:
  - [ ] Vault has been actively used for at least 2 weeks / 50+ agent cycles
  - [ ] Review vault contents: note count per folder, quality assessment, signal-to-noise
  - [ ] Review vault usage: are agents reading from it? grep logs for vault-search usage
  - [ ] Identify gaps: what should have been captured but wasn't
  - [ ] Identify noise: what was captured that shouldn't have been
  - [ ] File tuning adjustments as bugs/features
  - [ ] Adjust vault-remember triggers, rate limits, reflection prompts as needed

### Discussion

> [2026-04-03 09:15] **pm/qa**: Filed from human request. Evaluation checkpoint after all vault phases are deployed and running. Not a feature to build — a scheduled review to assess vault quality, usage, and tune the skills. Come back to this after the vault has real data.
