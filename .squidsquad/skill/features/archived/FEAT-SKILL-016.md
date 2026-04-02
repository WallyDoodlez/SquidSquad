## FEAT-SKILL-016 — Deep research-driven Feature Intake Process with interactive questioning

- **Priority**: Critical
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Replace the PM's shallow Feature Intake Process with a deep, GSD-inspired 5-phase feature lifecycle. Full design doc: `.squidsquad/pm/FEAT-SKILL-016-design.md`.

  **The 5 phases:**
  1. **Research (PM)** — Spawn research agent: codebase impact, side effects, edge cases, integration risks → RESEARCH.md
  2. **Discussion (PM + Human)** — Present findings, ask targeted questions with WHY, capture locked decisions vs dev discretion → CONTEXT.md
  3. **Planning (PM)** — Write feature entry informed by research + discussion, AND create test cases upfront → TEST-PLAN.md
  4. **Execution (Dev)** — Implement reading RESEARCH.md + CONTEXT.md + TEST-PLAN.md, run smoke tests before Pending Test
  5. **QA (PM)** — Execute test cases from TEST-PLAN.md, record pass/fail per case, only ship when all pass

  **Locked decisions:**
  - Light mode for trivial features (PM judgment — skip research for cosmetic/doc changes)
  - Research agent token cost is acceptable
  - Planning files auto-deleted after ship (git preserves)
  - Bugs excluded — current lightweight flow stays
  - PM can recommend rejection → new `Rejected` status
  - Planning files stored in `.squidsquad/[role]/planning/FEAT-XXX-*.md`

- **Acceptance Criteria**:
  - [ ] PM Feature Intake Process in `references/agent-instructions.md` replaced with 5-phase flow
  - [ ] Phase 1: Research agent produces FEAT-XXX-RESEARCH.md (impact, side effects, edge cases, integration risks, open questions)
  - [ ] Phase 2: PM presents research, asks questions with WHY, captures locked vs discretion decisions in FEAT-XXX-CONTEXT.md
  - [ ] Phase 3: Feature entry references planning artifacts; TEST-PLAN.md created with test cases, smoke tests, regression risks
  - [ ] Phase 4: Dev agent template updated to read planning artifacts and run smoke tests before Pending Test
  - [ ] Phase 5: PM QA step executes test cases from TEST-PLAN.md, records results, only ships on all-pass
  - [ ] Light mode: PM can skip research for trivial/cosmetic features
  - [ ] Rejection path: PM can recommend `Rejected` status with research justification; human can override
  - [ ] Planning files auto-deleted after ship
  - [ ] `.squidsquad/[role]/planning/` directory structure documented in SKILL.md
  - [ ] RESEARCH.md, CONTEXT.md, TEST-PLAN.md file formats documented
  - [ ] Generated PM and dev CLAUDE.md files updated
  - [ ] Bugs excluded from this flow — current process unchanged

### Discussion

> [2026-03-28 04:20] **pm/qa**: Filed from human request. The current intake process is too shallow — the statusLine feature (FEAT-SKILL-003) is a concrete example of an impulse requirement that caused BUG-SKILL-009 because side effects weren't considered. The PM needs to do GSD-level research before writing requirements, then ask the human deep questions. Status: Pending — awaiting human approval.
> [2026-03-28 04:45] **pm/qa**: Design doc created at `.squidsquad/pm/FEAT-SKILL-016-design.md`. Researched GSD's workflow in depth. Mapped GSD phases to SquidSquad roles: research+discussion+planning on PM, execution on dev, QA on PM. Added Phase 5 (QA test execution) per human input. 5 open questions resolved by human: light mode yes, token cost acceptable, auto-cleanup yes, bugs excluded, PM can reject. Human accepted and approved. Status → Approved.
> [2026-03-28 04:50] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 05:00] **skill-lead**: Complete. Replaced 4-step Feature Intake with 5-phase lifecycle in PM template. Phase 1 research agent with structured RESEARCH.md output. Phase 2 interactive discussion with CONTEXT.md. Phase 3 planning with TEST-PLAN.md. Phase 4 dev reads planning artifacts + smoke tests. Phase 5 PM executes test cases. Light mode, rejection path, auto-cleanup. Dev template updated to read artifacts. SKILL.md documented. Generated CLAUDE.md files updated. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 05:10] **pm/qa**: QA verified — all 13 acceptance criteria pass. 5-phase flow in PM template, research/context/test-plan artifacts, dev reads artifacts + smoke tests, PM QA executes test cases, light mode, rejection path, auto-cleanup, bugs excluded. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
