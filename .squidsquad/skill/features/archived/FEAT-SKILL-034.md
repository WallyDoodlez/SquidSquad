## FEAT-SKILL-034 — Planning process must always consider upgrade and migration paths

- **Priority**: High
- **Status**: Shipped
- **Requested By**: human
- **Description**: The Feature Intake Process (Phases 1-3) must always include upgrade and migration path analysis as a required section. Every feature that adds config values, new files, template changes, or behavioral changes must have explicit upgrade/migration steps documented in RESEARCH.md and CONTEXT.md. This should be baked into the research subagent prompt and the CONTEXT.md template so it's never forgotten.
- **Rationale**: FEAT-SKILL-033 needed multiple rounds of human feedback to add upgrade steps. This should be automatic — the planning process should always ask: "How do existing installs get this?"
- **Acceptance Criteria**:
  - [ ] Research subagent prompt (Phase 1) includes explicit instruction to analyze upgrade/migration impact
  - [ ] RESEARCH.md template includes an "Upgrade & Migration" section
  - [ ] CONTEXT.md template includes a "Locked Decisions — Upgrade Path" section
  - [ ] TEST-PLAN.md template includes upgrade verification tests
  - [ ] `references/agent-instructions.md` Phase 1 and Phase 2 updated with upgrade/migration requirements

### Discussion

> [2026-03-29 13:05] **pm/qa**: Filed from human feedback during FEAT-SKILL-033 planning. Human noted that upgrade/migration paths should be a standard part of every feature's planning process, not something added after human prompting. Status: Pending — awaiting human approval.
> [2026-03-29 20:10] **pm/qa**: Human approved. Decision: Upgrade & Migration section is ALWAYS required in RESEARCH.md — even trivial features get "N/A — no upgrade impact." This ensures nothing slips through. Light-mode intake — no separate RESEARCH/CONTEXT files needed, feature is self-contained. Status → Approved.
> [2026-03-29 20:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 20:35] **skill-lead**: Complete. Updated `references/agent-instructions.md`: (1) Phase 1 research list now includes item 5 "Upgrade & migration" as always-required, (2) RESEARCH.md template has new "Upgrade & Migration" section with 5 sub-fields, (3) CONTEXT.md template has new "Upgrade Path (required)" section, (4) Phase 3 test plan subagent prompt includes "Upgrade verification tests" as item 4. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 20:40] **pm/qa**: Verified all 5 acceptance criteria. Phase 1 research prompt has "Upgrade & migration" as item 5 (always required). RESEARCH.md template has 5-field Upgrade & Migration section. CONTEXT.md template has "Upgrade Path (required)". TEST-PLAN.md subagent prompt has "Upgrade verification tests" as item 4. CHANGELOG updated. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
