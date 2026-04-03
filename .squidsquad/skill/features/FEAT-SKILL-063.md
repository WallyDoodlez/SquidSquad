## FEAT-SKILL-063 — Self-improvement loop: agents suggest improvements during quiet cycles

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: During quiet cycles (no bugs to fix, no features to implement, no verification work), agents reflect on their own processes and suggest improvements. Instead of idle cycles producing zero output, agents use quiet time productively to identify process inefficiencies, template improvements, workflow gaps, and optimization opportunities.

  **Potential improvement areas agents could identify:**
  - Template wording that causes confusion or drift
  - Missing edge cases in the Ralph Loop
  - Tracker format improvements
  - Sub-skill decomposition opportunities
  - Repeated manual steps that could be automated
  - Workflow bottlenecks observed across cycles

- **Acceptance Criteria**:
  - [ ] Agents detect quiet cycles (no actionable work)
  - [ ] During quiet cycles, agents review their own templates, workflows, and recent history
  - [ ] Improvements are filed as features or bugs to the appropriate tracker
  - [ ] Rate-limited to avoid filing noise (e.g., 1 suggestion per N quiet cycles)
  - [ ] Human can review and approve/reject suggestions
  - [ ] Built as sub-skill under FEAT-SKILL-030 architecture

### Discussion

> [2026-04-03 02:00] **pm/qa**: Filed as FEAT-SKILL-063 (originally mislabeled as 057 in INDEX — 057 is boot script templatization filed by skill-lead). Self-improvement during quiet cycles. Status: Pending — awaiting human approval.
