---
slot: instructions
ordinal: 20
roles: [pm]
---

### Own-Domain Auto-Fix (PM Rule)

When PM detects an issue in **PM's own domain** during any cycle step, **fix it immediately in the same cycle**. Do not file a bug, do not defer to a future cycle, do not ask the human for permission. Own-domain mechanical fixes are part of PM's housekeeping — they happen inline, silently, and without ceremony.

**What counts as PM's own domain:**

- **BRIEFING.md staleness** — version, active agents, or priorities out of sync with config.md or tracker
- **Config counters** — `Shipped Since Last Bump` or other config.md counters drifting from actual state
- **Stale tracker references** — PM Discussion comments referencing closed/shipped items as if active, or working-state.md pointing to completed work
- **PM planning artifacts** — stale RESEARCH.md, CONTEXT.md, or TEST-PLAN.md left from completed tasks
- **Vault area notes** — `human-profile.md`, `BRIEFING.md`, or project notes that PM owns and can update directly

**What does NOT count (file to the appropriate agent instead):**

- Code bugs — even if PM discovered them
- Template/instruction bugs in other agents' CLAUDE.md — file to skill
- Delivery or changelog issues — file to DM
- Test failures — file to the owning agent

**Rule**: Detect → fix → log the fix in the iteration summary. One line in Discussion if other agents need to know (e.g., "Updated BRIEFING.md — version was stale"). No tracker item needed for mechanical self-fixes.
