## FEAT-SKILL-059 — SOUL.md: Agent personality, behavioral rules, communication style, boundaries

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Approved
- **Description**: Introduce a `SOUL.md` file per role sub-skill that defines the agent's personality, communication style, behavioral rules, and boundaries. Each role gets a distinct, hardcoded personality that shapes how it communicates in Discussion entries, interacts with the human, and collaborates with other agents.

  **Dimensions per role:**
  - **Tone**: Formal vs casual, verbose vs terse
  - **Communication style**: How the agent writes Discussion entries, presents options, reports findings
  - **Boundaries**: What the agent refuses to do, what it escalates
  - **Decision-making style**: Cautious vs bold, ask-first vs act-first
  - **Personality traits**: Distinct per role (e.g., PM = diplomat, QA = skeptic, designer = creative, dev = pragmatist)

  **Implementation:**
  - One `SOUL.md` per role sub-skill in `references/sub-skills/roles/`
  - Composed into the agent template at build time (same as other sub-skills)
  - Hardcoded — ships with the template, not user-configurable
  - Agents reference their SOUL.md for behavioral guidance

- **Acceptance Criteria**:
  - [ ] SOUL.md exists for each role (PM, QA, dev, designer, DM)
  - [ ] Each SOUL.md defines tone, communication style, boundaries, decision-making, personality
  - [ ] SOUL.md is included in template composition via sub-skill architecture
  - [ ] Agent behavior in Discussion entries reflects the defined personality
  - [ ] Personalities are distinct across roles — not generic

### Discussion

> [2026-04-02 11:00] **pm/qa**: Filed from human request.
> [2026-04-03 03:30] **pm/qa**: Human approved. Status → Planning.
> [2026-04-03 04:15] **pm/qa**: Phase 2 Discussion complete.
> [2026-04-03 04:30] **pm/qa**: Phase 3 complete — TEST-PLAN.md generated (18 TCs, 5 smoke tests, 5 regression risks). Planning phases complete. Status → Approved. Ready for skill-lead pickup. — 4 questions resolved. Locked: structure + anti-patterns, 2-3 example Discussion entries per role, vault references for adaptation, one PM soul (lean inherits). CONTEXT.md written. Human approved Phase 2 gate. Key insight from discussion: SOUL.md is a dependency for FEAT-SKILL-063 (self-improvement) — the soul defines the LENS each agent uses when scanning for improvements. Without it, DM just finds missing doc sections; with the right soul, DM thinks about user adoption. Also addresses the DM being too narrow (just a README updater) — the soul expands what agents consider as their responsibility. Beginning Phase 1 Research. Agent personality layer — each role gets a SOUL.md defining how it communicates and behaves. Hardcoded per role sub-skill. Status: Pending — awaiting human approval when ready to plan.
