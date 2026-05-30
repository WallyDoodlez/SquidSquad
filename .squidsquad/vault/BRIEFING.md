# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm) — paused per 2026-05-24 scope refocus; awaiting human disposition (close / re-scope / keep)
- #9968 EPIC: L1-L4 review + compose-architecture doc (in-progress, medium, role:pm) — current PM focus; advanced by PRs #10378 + #10379 this session
- PR #10378 (in flight) — multi-doc TRD polish across COMPOSE/AGENT-RUNTIME/HARNESS/INSTALLER, 13 commits + 5 DS audit rounds; INSTALLER×COMPOSE cross-audit converged to 0 contradictions; awaiting human review
- PR #10379 (in flight) — Agent Skill Dev Team preset rename + L1-L3 (`references/seed-v2/*`) + L4 (`.squidsquad/project/<role>.md`) new-compose-model seed; awaiting human review with 4 memory-vs-old-L4 contradictions surfaced for triage
- #5855 Vault is static decision log, not living memory (pending, high, role:skill)
- #3963 EPIC: Web dashboard — Harness Phase 4 (pending, high, role:skill)
- #5620 L3 PM stuck-rebase recovery (pending, high, role:skill)
- #6574 Zero-prereq install — gh repo creation + local forge fallback (pending, medium, role:skill)
- #5783 L3: bug investigation boundary — PM symptoms, dev RCA (pending, medium, role:skill)
- #5773 Document start.sh as boot entry point (pending, medium, role:dm)

## Recently Shipped

- #6274 Generalize 'dev' to 'worker' across architecture (shipped 2026-05-23) — terminology rename: dev→worker, qa→verifier across L1-L4
- #9184 PM defines ACs only / QA owns TEST-PLAN + CQs (shipped 2026-05-19, cycle 1499) — workflow restructure across pm/dev/qa sub-skills + L3 CQ directive rewrite + #8950 patch
- #9243 Harness /status exposes code_version (shipped 2026-05-19, cycle 1498)
- #7630 EPIC: Event-driven agent architecture (shipped) — harness owns cycle, agents react to events
- #8917 PM body sync when planning rewrites scope (shipped)
- #8950 Defense-in-depth gates: code-review/QA/DM check planning artifact (shipped)
- #6581 Wizard reframing — L3 picks agents, L4 records project specifics (shipped) — v0.38.0
- #6261 Fixed team architecture — PM+QA+DM+workers always present (shipped)
- _Older entries graduated to_ [[shipped-pre-2026-05-19]] _(25 individual fixes/tests/dead-code removals — not strategic, kept for audit)_

## Core Architecture

- **Layered roles**: L1 (base) → L2 (role) → L3 (domain) → L4 (project). compose.py assembles.
- **Harness**: Agent lifecycle owned by harness (REST API intent, .harness-state.json). Wrapper scripts eliminated (#4966).
- **Branching**: Code → main. State → squid-squad. Feature branches when branch workflow on.
- **PM boundaries**: PM does not rebase, merge PRs, or perform git ops on dev branches (#5234).
- **Tracker**: GitHub Issues with structured labels.

## Recent Decisions

- Agents use merge (not rebase) for conflict resolution — no force-push (#5445)
- .gitattributes auto-resolves state file conflicts (union for logs, ours for overwrite/config) (#5469)
- Sentinel files (.health, .claude-pid, .booting) are gitignored (#5469)
- Branch creation always from origin/<working>, never from local HEAD (#5444)
- L1 Soul: agents have situational awareness + vault-first knowledge (#5570)
- All agents consult vault before work (PM in research, dev/QA before pickup) (#5571, #5572)
- Improvement scans capture up to 3 vault writes per scan (#5569)
- Skill never edits composed CLAUDE.md — source templates only (#5557)
- PM agent uses --effort max for extended thinking (#5573)
- Harness owns all agent lifecycle — REST API intent (v0.33.0)
- Compose is its own skill (/squidsquad-compose) — single entry point (#5888)
- git_ops.py commit_code/task_end reverts config.md to prevent branch contamination (#7491)
- Wizard reframing: preset manifest owns domain variants, hybrid L4 writer, all roles get domain variant (#6581)
- Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose — drives #7630

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- PM should not intervene in code or branch management
- Dev agent disagreements with external code review escalate to human
- Mechanical cycle operations should be deterministic code, not LLM prose interpretation
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- Harness unreachable (#9242) — agents tolerate via direct gh CLI for tracker ops, but event wakes blocked. Human restart pending.
- Large pending backlog (~40 tasks) awaiting human approval — pipeline idle when no work is approved
- Event-driven architecture epic #7630 SHIPPED (PR #8620 merged). Monitor tool available in agent sessions.

## Team State

- Active agents: pm, qa, dm, skill (Dev Agents: skill; PM/QA/DM always present per config.md)
- Current version: 0.43.0
