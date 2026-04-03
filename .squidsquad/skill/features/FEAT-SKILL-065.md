## FEAT-SKILL-065 — Vault Phase 3: vault-remember + end-of-cycle reflection

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
- **Depends On**: FEAT-SKILL-064 (vault Phase 2)
- **Description**: Phase 3 of the PARAG memory vault. Adds automatic knowledge capture:

  1. **vault-remember (reactive hooks)**: Fires after work steps in every agent's Ralph Loop. Detects noteworthy context (decisions, patterns, learnings, preferences) and writes directly to the correct vault folder. Rate-limited to 3 captures per cycle. Per-role triggers defined by SOUL.md self-improvement lens.
  2. **End-of-cycle reflection (deterministic)**: On every non-quiet cycle, vault-remember fires one final time at cycle end asking "what did I learn this cycle?" Captures meta-knowledge: process learnings, human preference signals, codebase patterns, pitfalls discovered, what worked/didn't. Goes to `galaxy/learning-*` notes.

  **Two capture mechanisms in one skill:**
  - Reactive: triggered by events during work (decision made, pattern observed)
  - Deterministic: triggered by cycle completion (structured reflection)

- **Acceptance Criteria**:
  - [ ] vault-remember hook integrated into all agent Ralph Loops
  - [ ] Reactive captures fire after work steps (bug fixes, feature implementation, verification, etc.)
  - [ ] End-of-cycle reflection fires on every non-quiet cycle
  - [ ] Rate-limited to 3 captures per cycle (reactive + reflection combined)
  - [ ] Writes directly to correct PARAG folder (no inbox)
  - [ ] Dedup check — doesn't capture what's already in the vault
  - [ ] Confidence field set appropriately (high for human-confirmed, medium for observed, low for inferred)
  - [ ] Per-role triggers aligned with SOUL.md self-improvement lens
  - [ ] Built as common sub-skill

### Discussion

> [2026-04-03 09:00] **pm/qa**: Split from FEAT-SKILL-029. Phase 3 adds automatic capture + end-of-cycle reflection. Human requested deterministic reflection on every non-quiet cycle — "what did I learn?" Meta-knowledge about process, human preferences, codebase patterns. Depends on Phase 2 (needs vault-check for write validation). Planning artifacts from 029 cover this — TCs 34-42.
