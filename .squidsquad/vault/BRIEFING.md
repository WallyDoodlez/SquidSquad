# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- Sub-skill extraction complete (#30) — all 6 role templates now use includes, 15 common + 32 role-specific sub-skills
- Status bar shows active sub-skill name (#31) — format: `phase|sub-skill — description`
- Step markers now timestamped (#52) — `[🦑 HH:MM:SS] description`
- DM bug triage step added (#51) — DM can now fix bugs in its own domain
- Agent name aliases (#29) — pending approval, will enable universal placeholders for sub-skills

## Recent Decisions

- Sub-skill architecture shipped (v0.9.0) — monolithic templates split into layered sub-skills with build-time composition
- GitHub Issues as tracker (v0.9.0) — replaced internal markdown tracker files with GitHub Issues + structured labels
- PM and QA are separate agents — PM coordinates, QA verifies independently
- Feature lifecycle: Pending → Planning → Planned → Approved → In Progress → Pending Test → Pending Ship → Shipped
- `status:planned` gate — human must explicitly approve execution after planning completes
- Improvement scan classifies findings as bugs (broken) or features (new/enhanced)

## Human Preferences

- Never ship with failed test cases — any TC failure sends work back to dev
- PM should not block on human input in Ralph Loop — note availability and continue
- Always query GitHub Issues fresh — never answer from memory about pending items
- DM role is optional — PM auto-activates delivery when DM is absent
- Git is the audit trail for all content
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- No automated test suite — validation is manual SKILL.md review
- PR flow currently disabled
- Ship counter reset after v0.10.0 bump

## Team State

- Active agents: skill-lead, PM (separate), DM
- QA not currently active (PM handles verification in combined mode)
- Current version: 0.10.0 (Architecture Version 1)
- Tracker: GitHub Issues with structured labels (`type:`, `status:`, `role:`, `priority:`)
