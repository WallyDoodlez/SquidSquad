---
type: decision
tags: [vision, non-technical, team-presets, forgejo, architecture]
created: 2026-04-18
updated: 2026-04-18
owner: pm
status: active
confidence: high
source: conversation
links: [decision-self-healing-sentinel, human-profile]
---

## Context

Human clarified SquidSquad's long-term vision during discussion about non-GitHub backends. SquidSquad is not just a dev tool — it's a general-purpose autonomous team skill for all types of work.

## Content

**SquidSquad is for all teams, not just developers.** Non-technical teams (marketing, ops, content, project management) should be able to use the same agent coordination without requiring GitHub or git knowledge.

Key decisions:
- **Self-hosted forge backend**: Deploy Forgejo (GitHub-API-compatible) locally for teams that don't use GitHub. Setup automates deployment.
- **Team presets**: Record which "bus" system to use (github, forgejo-local, etc.). Dev teams use GitHub. Non-technical teams use self-hosted Forgejo.
- **Same agent behavior**: All agents work identically regardless of backend. tracker.py abstracts the difference.
- **Plug-and-play providers**: Like model providers, bus providers should be discoverable at setup time.

## Rationale

Human's vision: SquidSquad creates a skill that is generally for all work. Non-technical workflows assume users who can't use GitHub, so a different GH-like backend bus is needed. Forgejo was chosen because it's GitHub-API-compatible — minimal code changes to support.

## Related

- [[human-profile]]
- [[decision-self-healing-sentinel]]

---

### Changelog

- 2026-04-18 — Created by pm. Human-confirmed architectural vision for non-technical team support via Forgejo.
