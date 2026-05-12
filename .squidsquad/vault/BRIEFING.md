# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm) — awaiting human greenlight
- #6274 Generalize 'dev' to 'worker' across architecture (pending, medium, role:skill) — awaiting approval
- #6056 Replace /loop with event-driven Monitor tool (pending, medium, role:skill)
- #6087 L2: status line redesign (pending, medium, role:skill) — needs approval to plan
- #5855 Vault is static decision log, not living memory (pending, high, role:skill)
- #3963 EPIC: Web dashboard — Harness Phase 4 (pending, high, role:skill) — depends on #5622
- #5783 L3: bug investigation boundary — PM symptoms, dev RCA (pending, medium, role:skill)
- #5775 Move pipeline sentinel from PM cycle to harness TUI (pending, medium, role:skill)
- #5773 Document start.sh as boot entry point (pending, medium, role:dm)
- #5620 L3 PM stuck-rebase recovery (pending, high, role:skill)
- #5613 Phase 3+ event types (pending, low, role:skill)

## Pending Tasks (filed this session, awaiting approval)

- #5170 L4 dev customization: DeepSeek code review before pending-test (pending, medium)
- #5171 Harness loads config.md and serves configuration via REST endpoint (pending, medium)
- #5159 Status bar shows agent 'awaiting restart' state from harness intent API (pending, low)
## Recently Shipped

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

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- PM should not intervene in code or branch management
- Dev agent disagreements with external code review escalate to human
- See `[[human-profile]]` for full preferences

## Constraints & Blockers

- #4966 shipped — upgrade sequence needed (stop → clean sentinels → recompose → start via harness)
- Harness Phase 2 + 3 shipped — event bus bidirectional (emit + read) is live

## Team State

- Active agents: pm, qa, skill, dm
- Current version: 0.38.0
