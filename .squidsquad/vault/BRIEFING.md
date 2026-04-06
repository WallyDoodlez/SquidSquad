# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #2 — Public-facing documentation overhaul and attention-drawing README (approved, awaiting pickup)
- Improvement scanning active — DM filing doc drift bugs as they surface after version bumps
- All shipped through v0.11.0: sub-skill extraction (#30), status bar sub-skill names (#31), timestamped step markers (#52), DM bug triage (#51), agent name aliases (#29)

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

- Test suite exists (`python tests/run_tests.py`) — static analysis + integration tests (#67 shipped)
- PR flow currently disabled
- Ship counter reset after v0.11.0 bump — threshold 10, counter at 0

## Team State

- Active agents: skill-lead, PM (separate), DM
- QA not currently active (PM handles verification in combined mode)
- Current version: 0.11.0 (Architecture Version 1)
- Tracker: GitHub Issues with structured labels (`type:`, `status:`, `role:`, `priority:`)
