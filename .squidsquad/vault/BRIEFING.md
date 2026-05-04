# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #4709 EPIC Harness Phase 2: Event bus + agent communication (planned, high, role:skill)
- #3963 EPIC: Web dashboard — visual interface for SquidSquad (pending, high, role:skill)
- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm)
- #5557 Prohibit direct edits to composed CLAUDE.md + compose.py guard (pending-test, high, role:skill)

## Pending Tasks (filed this session, awaiting approval)

- #5170 L4 dev customization: DeepSeek code review before pending-test (pending, medium)
- #5171 Harness loads config.md and serves configuration via REST endpoint (pending, medium)
- #5159 Status bar shows agent 'awaiting restart' state from harness intent API (pending, low)

## Recently Shipped

- #5385 diagnostics.py log rotation before write
- #5378 cycle_pre pull() crash + _do_pull() false error reporting
- #5344 reboot_agent._spawn_wrapper delegates to boot_remote
- #5125 model_router.py yaml dedup + error handling
- #4966 Harness absorbs wrapper — full agent lifecycle ownership

## Core Architecture

- **Layered roles**: L1 (base) → L2 (role) → L3 (domain) → L4 (project). compose.py assembles.
- **Harness**: Agent lifecycle owned by harness (REST API intent, .harness-state.json). Wrapper scripts eliminated (#4966).
- **Branching**: Code → main. State → squid-squad. Feature branches when branch workflow on.
- **PM boundaries**: PM does not rebase, merge PRs, or perform git ops on dev branches (#5234).
- **Tracker**: GitHub Issues with structured labels.

## Recent Decisions

- Harness owns all agent lifecycle — zero sentinel files, REST API intent (v0.32.0)
- PM never intervenes in code or branch management — detect, report, nudge only (#5234)
- cycle_pre.py verifies agent on configured working branch at cycle start (#5208)
- DeepSeek code review gate planned for dev agent L4 (#5170)
- Harness config endpoint planned — centralized config reads/writes (#5171)

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- PM should not intervene in code or branch management
- Dev agent disagreements with external code review escalate to human
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- #4966 shipped — upgrade sequence needed (stop → clean sentinels → recompose → start via harness)
- Phase 2 (#4709) planned, awaiting human approval

## Team State

- Active agents: pm, qa, skill, dm
- Current version: 0.31.0
