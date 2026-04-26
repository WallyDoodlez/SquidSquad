# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm) — DM ready, awaiting human greenlight (21 days)
- #3393 Inter-agent real-time communication layer — pending (high, role:pm) — large initiative, running doc in vault/projects/
- #2495 Rewrite /squidsquad-upgrade — pending (high, role:skill) — awaiting human approval
- Recently shipped: #3302, #3341, #3340, #3377, #3348, #3347, #3349 (agent lifecycle + clone remote fixes)

## Core Architecture

- **Clone isolation**: Each agent runs in its own repo clone. PM in primary repo, dev agents in sibling clones (`../RepoName-role`). Paths configured in `.squidsquad/.local-config`. Never use global `~/.squidsquad/clones/`. See `[[decision-clone-isolation-architecture]]`.
- **Branching**: Code → main branch. State → `squid-squad` branch. Feature branches when branch workflow is on.

## Recent Decisions

- Clone isolation (v0.25.0) — each agent in own clone, project-local paths only, after cross-project contamination incident
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
- Ship counter: threshold 10, currently at 3 (v0.27.0 bumped 2026-04-25 by DM)
- Test suite: 986 passing (up from ~920 at v0.27.0 — 66 new regression tests added)

## Team State

- Active agents: qa, skill (dev agents), PM (always present), QA (always present), DM (present)
- Current version: 0.27.0
- Tracker: GitHub Issues with structured labels (`type:`, `status:`, `role:`, `priority:`)
- Boot detection now runs automatically in cycle_pre.py (#2724 shipped 2026-04-25)
