# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #2353 reboot_agent.py --all dict bug — pending-test (high, role:skill)
- #2350 BRIEFING.md staleness — open (low, role:pm)
- #2189 Architecture documentation — pending-test (medium, role:dm)
- #1772 DM delivery missing npm publish — pending-test (high, role:dm)
- #2361 TC coverage gate — pending-test (high, role:skill)
- #2351 Tarball installer — approved (medium, role:skill)
- No other approved tasks awaiting pickup

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
- Ship counter: threshold 10, currently at 1 (v0.25.0 bumped)

## Team State

- Active agents: boot, qa, skill (dev agents), PM (always present), QA (always present), DM (present)
- Current version: 0.25.0 (Architecture Version 1)
- Tracker: GitHub Issues with structured labels (`type:`, `status:`, `role:`, `priority:`)
