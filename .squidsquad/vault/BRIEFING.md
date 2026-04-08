# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- Improvement scanning active — DM filing doc drift bugs as they surface after version bumps
- Shipped through v0.14.0: #2 README overhaul, #251 self-diagnostics, #149 runtime SOUL.md, #239 CONTRIBUTING/CODE_OF_CONDUCT, #232 community infra (LICENSE, issue templates), #189 sub-skill guide, #190 ARCHITECTURE.md, #240 boot-time agent registration, #211 phantom fix prevention
- 13 pending DM doc bugs from improvement scans awaiting triage

## Recent Decisions

- Sub-skill architecture shipped (v0.9.0) — monolithic templates split into layered sub-skills with build-time composition
- GitHub Issues as tracker (v0.9.0) — replaced internal markdown tracker files with GitHub Issues + structured labels
- Runtime SOUL.md (v0.14.0) — agent personalities are separate files, editable without redeploying templates
- Self-diagnostics (v0.14.0) — `/squidsquad-bug` command for upstream bug reporting with sanitized context
- Community infrastructure (v0.14.0) — AGPL-3.0 license, GitHub Issue templates, going-public docs
- Feature lifecycle: Pending → Planning → Planned → Approved → In Progress → Pending Test → Pending Ship → Shipped

## Human Preferences

- Never ship with failed test cases — any TC failure sends work back to dev
- PM should not block on human input in Ralph Loop — note availability and continue
- Always query GitHub Issues fresh — never answer from memory about pending items
- DM role is optional — PM auto-activates delivery when DM is absent
- Git is the audit trail for all content
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- Test suite exists (`python tests/run_tests.py`) — static analysis + integration tests
- PR flow currently disabled
- Ship counter reset after v0.14.0 bump — threshold 10, counter at 0

## Team State

- Active agents: skill-lead, PM (separate), DM
- QA not currently active (PM handles verification in combined mode)
- Current version: 0.14.0 (Architecture Version 1)
- Tracker: GitHub Issues with structured labels (`type:`, `status:`, `role:`, `priority:`)
