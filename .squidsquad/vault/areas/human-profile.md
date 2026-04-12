---
type: area
tags: [human, preferences, profile]
created: 2026-04-05
updated: 2026-04-12
owner: pm
status: active
confidence: medium
source: observation
links: []
---

## Overview

Profile of the human collaborator. Captures preferences, values, communication style, and technical expectations. Used by all agents to tailor their behavior. Entries marked `confidence: medium` are inferred — update to `high` when the human confirms.

## Communication Style

- Terse, direct communication preferred — no unnecessary summaries or preamble
- Uses shorthand and typos freely (expects agents to interpret intent)

## Quality Expectations

- Expects all tests to pass before marking work complete
- Values working code over documentation

## Technical Preferences

- Primary platform: Windows 11
- Uses Python for scripting, bash for shell operations
- Repository: SquidSquad autonomous agent framework
- Context pressure threshold: 70% (human considers 80% too high — agents degrade before hitting 80%)

## Decision-Making Style

- Delegates operational decisions to agents, steps in for approvals
- Prefers agents to act first on clear requirements, ask when ambiguous

## Schedule & Availability

_Not yet observed._

## Related

_Wikilinks to related notes: [[code-conventions]]_

---

### Changelog

- 2026-04-05 — Seeded by skill-lead (vault-remember). Pre-populated from observed interactions. Confidence: medium (awaiting human review).
- 2026-04-12 — Updated by skill-lead. Added context pressure threshold preference (70%, human directive via #378).
