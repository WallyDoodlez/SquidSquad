## Project Operations — SquidSquad

These instructions apply to ALL agents on this project.

### Tracker & Communication

- **GitHub Issues is the single source of truth** for all work tracking. No internal markdown tracker files.
- **Commit messages use role prefix**: `skill:`, `pm:`, `qa:`, `dm:` — always prefix with your role.
- **Status lifecycle**: All transitions go through `python references/scripts/tracker.py transition`. Never construct `gh issue edit` label commands manually.
- **Discussion = issue comments**: append-only. Never edit or delete previous comments.
- **Timestamps from cycle.py only**: Use `python references/scripts/cycle.py timestamp-short` for step markers, `timestamp` for comments. Never guess or fabricate times.
- **Bullet points in issue comments**: Use structured, scannable formatting.
- **Mandatory human approval for features**: Tasks start as `Pending` — a human must explicitly approve before any agent picks them up.

### Cycle & Context

- **Context pressure threshold: 70%**. Checkpoint working state when exceeded, continue normally (Claude Code auto-compresses).
- **Working state file pattern**: Maintain `.squidsquad/<role>/working-state.md` to persist context across resets.
- **Ship threshold: 10**. Iteration cadence is mode-specific — see role L1/L2 layers for trigger semantics.
- **Deterministic work queue**: Pick the first item. No discretion to skip, reorder, or cherry-pick.

### Git Protocol

- **Always `git pull` before starting work.** Never push without pulling first.
- **Atomic writes**: Write to `.tmp` then `mv` for any file other agents or the statusline may read.
- **Branch workflow enabled**: Feature branches per task (pattern from config.md `branch-pattern`, default `squidsquad/task/{number}`).
- **PR flow + auto-merge enabled**: PRs created for feature branches, auto-merged when QA passes (unless `review:human-required`).

### Agent Infrastructure

- **Harness manages agent lifecycle**: PID monitoring via `.claude-pid` (sole liveness signal). Intent state machine via REST API (#4966).
- **Agent lifecycle via `squidsquad_cli.py`** (with `start_team.py` as a backward-compatible shim): Agents do not manage their own or other agents' processes.
- **Context pressure restart**: mechanical detection at the end of each unit of work triggers respawn — same mechanism in both modes; the unit of work differs (a cycle in polling mode, a task in event mode).

### Planning & Verification

- **Planning artifacts (#9184)**: PM produces RESEARCH.md and CONTEXT.md under `.squidsquad/pm/planning/`. QA produces `TEST-PLAN-<NUMBER>.md`, `TEST-<NUMBER>-tests.py`, and `QA-RESULTS-<NUMBER>.md` under `.squidsquad/qa/planning/` when picking up verification. PM does NOT produce a test plan.
- **Clone isolation paths from `.local-config`**: Each agent's clone path resolved via boot_remote.
- **BRIEFING.md staleness check every cycle**: Version, active agents, priorities verified against config.md.
- **Bug fixes need research**: PM runs Phase 1 research before filing, not just "fix this."
- **Any TC failure = back to dev**: Zero-gap gate — all findings must be resolved before shipping.

### Vault

- **Vault PARAG structure**: projects/, areas/, resources/, archives/, galaxy/. All git-tracked.
- **vault-check Level 1 auto-runs**: After every vault-create or vault-update.
