## FEAT-SKILL-063 — Self-improvement loop: agents suggest improvements during quiet cycles

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Planning
- **Description**: During quiet cycles (no bugs to fix, no features to implement, no verification work), agents use their domain expertise to find improvements in **the target project** that SquidSquad is applied to. This is a skill SquidSquad provides to any repo it manages — turning idle agent time into proactive project improvement.

  **Per-role improvement focus (on the target project):**
  - **Dev**: Code quality — refactoring opportunities, dead code, performance issues, missing error handling, outdated dependencies, code smells
  - **Designer**: Design consistency — mismatched patterns, accessibility gaps, missing states, design system violations, UX improvements
  - **QA**: Test coverage — edge cases not tested, regression risks, acceptance criteria gaps, missing test cases, flaky test detection
  - **DM**: Documentation — outdated README sections, missing API docs, changelog inconsistencies, public-facing material improvements
  - **PM**: Process — backlog grooming, stale features, priority rebalancing, workflow bottlenecks

  **Flow**: Agent detects quiet cycle → scans target project for improvements in its domain → files findings as features or bugs to the appropriate tracker → human reviews and approves/rejects through normal pipeline.

- **Acceptance Criteria**:
  - [ ] Agents detect quiet cycles (no actionable work in tracker)
  - [ ] During quiet cycles, agents scan the target project codebase/docs/tests for improvements
  - [ ] Each role focuses on its domain expertise (dev=code, QA=tests, designer=design, DM=docs, PM=process)
  - [ ] Improvements filed as features or bugs through normal tracker pipeline
  - [ ] Rate-limited to avoid filing noise (e.g., 1 suggestion per N quiet cycles)
  - [ ] Human can review and approve/reject suggestions like any other work item
  - [ ] Built as sub-skill under FEAT-SKILL-030 architecture
  - [ ] Works on any project SquidSquad is applied to, not just SquidSquad itself

### Discussion

> [2026-04-03 02:00] **pm/qa**: Filed as FEAT-SKILL-063 (originally mislabeled as 057 in INDEX). Status: Pending.
> [2026-04-03 02:30] **pm/qa**: Critical reframe from human.
> [2026-04-03 02:45] **pm/qa**: Human approved. Status → Planning. Beginning Phase 1 Research.
> [2026-04-03 04:45] **pm/qa**: Phase 2 Discussion complete — 5 questions resolved. Locked: hybrid auto-detect, default Low priority, no global budget, new scanning status phase, all findings through PM. Key human decision: agents don't file directly — they report to PM who files. PM is the single coordination point. CONTEXT.md written. Human approved Phase 2 gate. This is NOT about agents improving their own templates/processes. It's about agents improving THE TARGET PROJECT during quiet cycles. SquidSquad is a skill applied to repos — the self-improvement loop is a capability it provides to any project. Dev finds code improvements, QA finds missing tests, DM finds doc gaps, designer finds design issues, PM finds process improvements. Findings filed through normal tracker pipeline.
