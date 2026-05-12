---
type: area
tags: [human, preferences, profile]
created: 2026-04-05
updated: 2026-05-12
owner: pm
status: active
confidence: medium
source: observation
links: [code-conventions, decision-vault-remember-source-agnostic]
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
- Prefers direct/mechanical checks over indirect state files — "just use PID, it's more direct." OS-level truth (process exists?) beats application-level files (.health) that can go stale. Applies broadly: prefer the most direct verification method available.
- Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose — "any kind of cyclic work needs to be programmed deterministically." LLMs reliably drop steps when context compresses. Agents should react to events, not run multi-step cycles. Drives #7630 (event-driven architecture).

## Product Vision

- SquidSquad is a general-purpose autonomous team skill — not just for developers
- Non-technical teams (marketing, ops, content) should be able to use it without GitHub/git knowledge
- Prefers leveraging existing open-source tools (Forgejo, not custom backends) over building from scratch
- Systems should self-heal: detect stuck states → unstick immediately → file root-cause bug → agent fixes gap

## Design Philosophy

- Vault remember reflection should be source-agnostic — any signal (human, QA, PM, agent) evaluated across all categories. See [[decision-vault-remember-source-agnostic]].
- Thinking about inter-agent conversation/debate system as a prerequisite infrastructure before vault improvements.

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
- 2026-04-18 — Updated by pm. Added preference for direct/mechanical checks over indirect state files (from #1301 discussion).
- 2026-04-18 — Updated by pm. Added Product Vision section: general-purpose skill for all teams, self-healing systems, prefer existing OSS over custom builds.
- 2026-04-26 — Updated by skill-lead. Added Design Philosophy section: source-agnostic vault reflection (human directive), inter-agent conversation system as prerequisite.
- 2026-05-12 — Updated by pm. Added deterministic-cycle preference: mechanical agent work must be programmatic, not LLM prose. Drives #7630.
