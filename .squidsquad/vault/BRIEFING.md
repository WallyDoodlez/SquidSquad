# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #1291 Multi-model subagents — in-progress (reopened 3rd time, live API tests required)
- #1426 Shared filesystem ~/.squidsquad/ — approved, dependency for #1427 and #1389
- #1428 Deterministic QA testing — approved, changes PM test plans + QA verification
- #1389 Forgejo backend — approved, depends on #1426
- #473/#474 Test coverage requirements — approved, high severity, 5+ days stalled (5 nudges)
- #1427 Model router setup UX — approved, depends on #1426

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
- Ship counter: threshold 10, currently at 8

## Team State

- Active agents: boot, qa, skill (dev agents), PM (always present), QA (always present), DM (present)
- Current version: 0.20.0 (Architecture Version 1)
- Tracker: GitHub Issues with structured labels (`type:`, `status:`, `role:`, `priority:`)
