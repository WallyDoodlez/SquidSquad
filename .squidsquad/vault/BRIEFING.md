# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #4765 compose.py L4 role filtering fix (pending-test, medium, role:skill)
- #4709 EPIC Harness Phase 2: Event bus + agent communication (planned, high, role:skill)
- #4221 Agent harness — supervisor process for all agents (pending, high, role:skill)
- #3963 EPIC: Web dashboard — visual interface for SquidSquad (pending, high, role:skill)
- #3969 DM doc improvement loop — staleness detection (pending-test, high, role:dm)
- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm)

## Recently Shipped

- #4449 L4 project instructions: PM/DM verify distribution packaging
- #4439 EPIC: SquidSquad Harness — unified agent platform
- #4541 Agent-driven composition (compose.py LLM pipeline)
- #4179 Dev L2 SOUL: divide-and-conquer instinct
- #4084 Draft PR workflow for dev agents

## Core Architecture

- **Layered roles**: L1 (base) → L2 (role) → L3 (domain) → L4 (project). compose.py assembles.
- **Branching**: Code → main. State → squid-squad. Feature branches when branch workflow on.
- **Communication layer**: Platform-agnostic adapter interface + deterministic sub-skills. Telegram-first. Feature flag controlled.
- **Tracker**: GitHub Issues with structured labels.

## Recent Decisions

- Agent-driven composition replaces deterministic compose.py (v0.30.0)
- Draft PRs: agents create drafts, auto-ready on pending-test (v0.30.0)
- Clone isolation (v0.25.0), Sub-skill architecture (v0.9.0), GitHub Issues tracker (v0.9.0)
- Feature lifecycle: Pending → Planning → Planned → Approved → In Progress → Pending Test → Pending Ship → Shipped

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- Boot detection: heartbeat-based with boot lock
- Harness epic (#4439) shipped; Phase 2 (#4709) planned, awaiting human approval

## Team State

- Active agents: pm, qa, skill, dm, designer
- Current version: 0.31.0
