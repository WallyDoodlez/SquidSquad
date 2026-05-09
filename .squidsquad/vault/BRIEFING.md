# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- #3 Take SquidSquad public / v1.0.0 launch — approved (high, role:dm) — awaiting human greenlight
- #6056 Replace /loop with event-driven Monitor tool (pending, medium, role:skill) — next after #6086/#6087
- #6085 Event bus architecture docs (approved, medium, role:dm) — DM working
- #6086 L1: issue/PR context descriptions (open, medium, role:skill) — hold lifted
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

- #6055 Enforce role separation — PM/QA/DM mandatory (shipped)
- #5932 L2 external code review loop (shipped)
- #6057 State machine in-progress → planning (shipped)
- #5868 Event consumption sub-skill (shipped)
- #6000 Harness Ctrl+C fix (shipped)
- #6007 QA L2 finding routing (shipped)
- #5888 /squidsquad-compose skill (shipped)
- #5915 WindowsPath JSON serialization fix (shipped) — v0.33.0

- #5856 tracker.py status-transition events — bus now has real coordination signals (shipped)
- #5622 EPIC Harness Phase 3: Agent communication bus — agents read events (shipped)
- #4709 EPIC Harness Phase 2: Event bus emission infrastructure (shipped)
- #5774 start.sh/start.ps1 installer manifest fix (shipped)
- #5782 git_ops.py unknown role in events (shipped)
- #5573 PM agent uses --effort max (config-driven per-agent effort)
- #5572 L2 Dev/QA vault consultation before work
- #5571 L2 PM vault mandatory in research
- #5570 L1 Soul situational awareness + vault-first
- #5569 L1 Improvement scan knowledge capture
- #5557 Composed CLAUDE.md edit prohibition + compose.py guard
- #5556 Stale rebase refs cleaned from source templates
- #5534 config.md counter clobber fix
- #5533 SKILL.md stale rebase refs
- #5526 _verify_remote_branch wildcard pattern
- #5469 .gitattributes merge strategies + .gitignore volatile files
- #5445 rebase→merge for conflict resolution (no force-push)
- #5444 Branch workflow reliability (push verify, origin-based branching)
- #5435 run_tests.py static suite fix
- #5429 health_check.py PID fallback for stale heartbeats
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
- Current version: 0.34.0
