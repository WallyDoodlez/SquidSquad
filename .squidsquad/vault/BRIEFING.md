# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm) — paused per 2026-05-24 scope refocus; awaiting human disposition (close / re-scope / keep)
- #9968 EPIC: L1-L4 review + compose-architecture doc (in-progress, medium, role:pm) — HELD pending doc-closure of arch docs
- #10003 Massage docs/VAULT-ARCH.md (in-progress, medium, role:pm) — active PR #10004; current PM focus
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
- #8916 L2 dev: mandate reading CONTEXT.md / TEST-PLAN.md (shipped)
- #8917 PM body sync when planning rewrites scope (shipped)
- #8950 Defense-in-depth gates: code-review/QA/DM check planning artifact (shipped)
- #8081 triage.py: datetime-parsed timestamp comparison replacing fragile string compare (shipped)
- #8082 scan_index.py: record_decision inserts file_coverage row on missing (shipped)
- #7794 PM prohibitions.md: replaced stale 'tracker files' references in PM, DM, installer (shipped)
- #7947 wizard.py: validate_interval — 20 parametrized tests added (shipped)
- #7948 wizard.py: Code Review Model default test coverage added (shipped)
- #7955 cycle_post.py: added 13 tests for _do_tracker_comments and _do_working_state_update (shipped)
- #7793 PM/QA ship counter double-counting — QA now owns counter authoritatively (shipped)
- #7879 squidsquad-upgrade.md: removed .claude/ from upgrade commit staging (shipped)
- #7890 config.md missing Code Review Model field — model_router code-review fix (shipped)
- #6581 Wizard reframing — L3 picks agents, L4 records project specifics (shipped) — v0.38.0
- #7491 compose/sync config.md contamination fix (shipped) — root cause of 10+ QA rejections
- #7285 config.py sync_agents() NameError fix (shipped)
- #7441 harness.py save_state race condition fix (shipped)
- #7440 cycle_post.py dead no-op str.replace (shipped)
- #7191 dev-instructions.md unscoped copy references (shipped)
- #7286 boot_remote.py AppleScript quoting fix (shipped)
- #7589 state_bus.py silent git commit failure (shipped)
- #7590 manifest.py redundant yaml import (shipped)
- #7618 vault_optimize.py lock TOCTOU (shipped)
- #7619 squidsquad_cli.py URLError swallowed (shipped)
- #7622 tc_coverage.py OSError handling (shipped)
- #7624 vault_remember.py decay_scan error handling (shipped)
- #7625 forgejo_setup.py dead code (shipped)
- #6597 deploy-all clone isolation fix (shipped)
- #6261 Fixed team architecture — PM+QA+DM+workers always present (shipped)
- #5423 harness.py INTENT_STOPPED constant

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
