# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm) — DM ready, awaiting human greenlight (21+ days stalled)
- #3963 EPIC: Web dashboard — visual interface for SquidSquad agent interaction — pending (high, role:skill)
- #3955 Stale sub-skill lifecycle templates — pending-ship (QA verified, awaiting DM delivery)
- #3415 EPIC: Real-time communication layer — Telegram-first. 2/6 sub-tasks shipped. 4 remaining (#3418-#3421). Pending approval.
- #3464 Human-in-the-loop execution — pending (medium)
- #3465 Layered role definition architecture — pending (medium)

## Recently Shipped (2026-04-26/27 session)

- #3302, #3340, #3341, #3347, #3348, #3349, #3360, #3377 (boot lifecycle + clone fixes)
- #3416, #3417 (epic:comms-layer foundation: adapter interface + sub-skills)
- #1470 (DeepSeek base_url), #3466 (PR creation restored)

## Core Architecture

- **Clone isolation**: Each agent in own clone, project-local paths. See `[[decision-clone-isolation-architecture]]`.
- **Branching**: Code → main. State → squid-squad. Feature branches when branch workflow on.
- **Communication layer** (NEW): Platform-agnostic adapter interface + deterministic sub-skills. Telegram-first. Feature flag controlled.

## Recent Decisions

- Communication layer (v0.27.0+) — deterministic sub-skills over mechanical adapters, Telegram-first, one bot per agent, feature flag
- Clone isolation (v0.25.0), Sub-skill architecture (v0.9.0), GitHub Issues tracker (v0.9.0)
- Feature lifecycle: Pending → Planning → Planned → Approved → In Progress → Pending Test → Pending Ship → Shipped

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- Ship counter: threshold 10, currently at 14 (v0.28.0) — bump overdue, likely held for v1.0.0 decision
- Boot detection: heartbeat-based with boot lock (#3347/#3348/#3349)

## Team State

- Active agents: pm, qa, skill, dm — all present and healthy
- Current version: 0.28.0
