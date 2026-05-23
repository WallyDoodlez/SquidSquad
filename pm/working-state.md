# Working State

- **Task**: #9968 architectural reframe escalated cycle 1619: sub-skills should be real Claude skills (hybrid model). #9965 skill batch #6: 48→27 over 6 cycles.
- **Status**: monitoring (skill steady; major doc reframe pending human direction)
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-23 19:03)
- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external untriaged
- 1 approved (long-running): #3 (DM lane, going-public)
- 2 in-progress:
  - #9965 (6274.2/AC2.8) — skill steady:
    - cycles 1315-1320 (16:44→18:36): 48→47→41→36→31→27
    - 6 cycles, -21 failures total, avg -3.5/cycle, zero regressions
    - Trajectory: ~7-8 more cycles to 0 if rate holds
  - #9968 (EPIC: L1-L4 doc) — v1.3 (8b33aebd) shipped cycle 1616. Three architectural conversations layered this session:
    - Cycle 1617: 20-gap analysis (3 tiers)
    - Cycle 1618: manifest elimination (4 jobs analyzed; all displaced by frontmatter + config.md)
    - Cycle 1619: sub-skills as Claude skills (hybrid: mandatory inline + situational as Claude skills)
  - No doc edits committed for any of the above; human deferred each time
- 1 pending (gated): #9966 (6274.3)
- 3 issues at status:open: #9967, #9969, #9970
- shipped_since_bump=6 of 10

## #9968 reframe captured cycle 1619
Human's new direction: sub-skills should BE Claude skills.
- Factual correction PM made: today sub-skills are NOT Claude skills — they're plain markdown fragments at references/sub-skills/*.md that compose inlines. No SKILL.md frontmatter, no .claude/skills/ registration.
- User's target: convert to real Claude skills, composed CLAUDE.md just mentions which to use.
- PM-surfaced tension: Claude skills are discretionary (model decides when to invoke). But mandatory procedures (cycle-runner, boot-bootstrap, context-pressure, agent-lifecycle) cannot be optional — they MUST execute every cycle/boot. Pure Claude-skills model risks reliability regression.
- PM recommendation: hybrid tier system
  - **Mandatory tier**: inlined into small composed CLAUDE.md (5-10KB instead of today's 50KB+). Includes cycle-runner, boot-bootstrap, context-pressure, status transitions, identity, soul.
  - **Situational tier**: real Claude skills with SKILL.md frontmatter. Includes vault-remember, improvement-scan, code-review, issue-filing, soul-shepherd, etc.
  - Maps to `load: always | on-demand` from cycle 1618 discussion.
- This invalidates much of v1.3 doc's compose-pipeline emphasis. Doc would need significant rewrite to position compose as ONLY handling the small mandatory CLAUDE.md, with the bulk of behavior moving to Claude's skill registry.

Pending decisions (none filed as tasks; all in working state):
- T1 (cycle 1618): sub-skill cruft audit
- T2 (cycle 1618): doc v1.4 §15 Schemas
- T3 (cycle 1618): §6.5 wake-mode revision
- T4 (cycle 1619): convert situational sub-skills to Claude skills (SKILL.md format)
- T5 (cycle 1619): test mandatory-procedure reliability under Claude skill mechanism (does description-matching reliably trigger every cycle?)
- T6 (cycle 1619): redefine `compose.py` scope to just the small mandatory CLAUDE.md
- T7 (cycle 1619): doc #9968 v2.0 rewrite (scope expansion beyond what v1.3 captured)

## #9965 — standard monitoring
- Skill execution remains exemplary; no PM action needed
- shipped_since_bump=6/10 — under threshold, no bump

## #9966 — unchanged
- Conditions: AC2.8 ships, cutover date passed
