## FEAT-SKILL-025 — Track token usage per agent per cycle

- **Priority**: Medium
- **Owner**: skill-lead
- **Description**: SquidSquad agents should track token usage each cycle. Each agent logs its token consumption (input + output tokens) in its iteration log. The PM aggregates token usage across all agents in its own iteration log and maintains a running total in `config.md` or a dedicated `pm/token-usage.md` file. This gives the human visibility into how much each agent costs per cycle and over time.

- **Acceptance Criteria**:
  - [ ] Each agent's iteration log includes token usage (input tokens, output tokens, total)
  - [ ] PM iteration log includes per-agent token usage and a cycle total
  - [ ] Running totals are maintained and accessible (cumulative usage over time)
  - [ ] Token data is sourced from Claude's usage metadata (not estimated)
  - [ ] PM template in `references/agent-instructions.md` updated
  - [ ] Dev agent template in `references/agent-instructions.md` updated
  - [ ] SKILL.md documents the token tracking behavior

### Discussion

> [2026-03-29 01:00] **pm/qa**: Filed from human request. Observability improvement — track how many tokens each agent consumes per cycle and cumulatively. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
