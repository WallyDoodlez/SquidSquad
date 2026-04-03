## FEAT-SKILL-063 — Self-improvement loop: agents suggest improvements during quiet cycles

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Shipped
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
> [2026-04-03 04:45] **pm/qa**: Phase 2 Discussion complete.
> [2026-04-03 05:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-04-03 05:45] **skill-lead**: Implementation complete.
> [2026-04-03 06:15] **skill-lead**: Fixed GAP-1 (TC-21):
> [2026-04-03 06:30] **pm/qa**: Re-verified — zero gaps. Exclusion list present in improvement-scan.md and all 6 composed templates. TC-21 now passes. 28/28 TCs pass. Status → Pending Ship. Added explicit scan exclusion list (.squidsquad/, node_modules/, vendor/, .git/, build output, generated files, binaries) to Step 3 of improvement-scan.md. Recomposed agent-instructions.md. Status → Pending Test.
> [2026-04-03 06:00] **pm/qa**: Unbiased QA verification: 27/28 PASS, 1 FAIL. Zero-gap gate — back to In Progress. Failure: TC-21 — improvement-scan.md lacks explicit exclusion list for internal directories (.squidsquad/, node_modules/, .git/, vendor/, build output, generated files). Agents could scan SquidSquad's own files instead of the target project. Fix: add exclusion paragraph to Step 3 file selection. Full results in FEAT-SKILL-063-QA-RESULTS.md. Status → In Progress. Created common/improvement-scan.md sub-skill with quiet cycle counter (3 threshold), per-role scan strategies, incremental file selection, scan history, PM-routed findings (max 2 per scan), config toggle. Included in all 6 role templates. Added Improvement Scanning: yes to config.md. All smoke tests passing. Status → Pending Test.
> [2026-04-03 05:00] **pm/qa**: Phase 3 complete — TEST-PLAN.md generated (28 TCs, 6 smoke tests, 7 regression risks). Planning phases complete. Status → Approved. Ready for skill-lead pickup. Depends on FEAT-SKILL-059 (SOUL.md) for the self-improvement lens dimension. — 5 questions resolved. Locked: hybrid auto-detect, default Low priority, no global budget, new scanning status phase, all findings through PM. Key human decision: agents don't file directly — they report to PM who files. PM is the single coordination point. CONTEXT.md written. Human approved Phase 2 gate. This is NOT about agents improving their own templates/processes. It's about agents improving THE TARGET PROJECT during quiet cycles. SquidSquad is a skill applied to repos — the self-improvement loop is a capability it provides to any project. Dev finds code improvements, QA finds missing tests, DM finds doc gaps, designer finds design issues, PM finds process improvements. Findings filed through normal tracker pipeline.
> [2026-04-03 15:30] **dm**: CHANGELOG entry prepared: "FEAT-SKILL-063 — Self-improvement loop: agents scan target project for improvements during quiet cycles". Delivery complete. README updated (new Self-Improvement Scanning feature section). SKILL.md updated (Ralph Loop quiet cycle behavior, new Improvement Scanning config field). New config value: Improvement Scanning (yes/no). Status → Shipped.
