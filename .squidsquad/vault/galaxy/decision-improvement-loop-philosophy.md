---
type: decision
tags: [improvement-scan, process, evolution, philosophy]
created: 2026-04-26
updated: 2026-04-26
owner: pm
status: active
confidence: high
source: conversation
links: [human-profile]
---

## Context

Human described the three-layer evolution model for how SquidSquad agents improve over time. This formalizes the improvement scan's role as the third layer — not just a gap-finder but a source of creative and experimental proposals.

## Content

SquidSquad agents evolve through three layers:

1. **Generic template + setup context** — Role templates that work for any project, enriched with project-specific context during `/squidsquad-setup`. This is the baseline.

2. **Runtime customization** — Over time, human instructions and vault learnings accumulate as role-specific adaptations. These are marked as role customizations, not changes to the generic template. The agent gets better at its specific job through feedback and observation.

3. **Improvement scan (proactive discovery)** — Based on vault learnings and accumulated context, agents find issues that aren't apparent through normal task/bug creation. This includes:
   - Process/workflow gaps and contradictions
   - Creative or experimental proposals that may improve operations
   - Novel ideas the human wouldn't think to ask for

4. **Vault synthesis (cross-agent pattern emergence)** — Every 5 quiet cycles, PM reviews recent vault writes from all agents, detects recurring themes and convergent decisions, and consolidates them into posture notes (pattern type, tagged 'posture'). Postures become scan criteria for all agents only after human approval.

**Approval tiers for scan findings:**
- Small mechanical gap fixes → PM auto-fixes inline
- Larger gap fixes (workflow changes, cross-role impact) → file as task, human discussion required
- Creative/experimental proposals → always file as task, always discuss with human
- Posture notes from synthesis → always file as task, human approval required before activation

**Domain lenses:**
- PM scans process/workflow (never code) — templates, instructions, vault for contradictions
- Dev agents scan code — vault-informed quality, consistency, test coverage, creative refactors
- Both consult vault before scanning

## Rationale

Normal task/bug flow is reactive — the human or an agent notices something broken. The improvement scan is proactive — it leverages everything the squad has learned to surface opportunities that no one explicitly asked for. Without the creative dimension, the scan is just another bug-finder. With it, the scan becomes a source of innovation.

The vault synthesis step connects dots that individual agents can't see. When multiple agents independently observe related patterns, synthesis consolidates them into postures — team-level principles that shape all future work.

## Related

- [[human-profile]]

---

### Changelog

- 2026-04-26 — Created by pm. Human described three-layer improvement philosophy during session discussion.
- 2026-04-26 — Updated by pm. Added vault synthesis cycle (layer 4), approval tiers, domain lenses, and dev scan expansion. Human confirmed: pattern type for postures, 5-cycle trigger, human approval required.
