# FEAT-4 Context — Boot Remote Agents Sub-Skill

## Scope

Ship a `boot-remote-agents` sub-skill that any SquidSquad agent can compose into its CLAUDE.md to spawn missing/stalled teammates in their own terminal windows. v1 consumer is PM (auto-boots missing teammates during its cycle). Future consumers: installer (end-of-setup auto-boot), orchestrators, debug utilities.

## Locked Decisions (human decided 2026-04-11 during Phase 2 discussion)

### Q1 — Implementation: Python helper script
- Ship `references/scripts/boot_remote.py` as the deterministic spawn engine
- Sub-skill at `references/sub-skills/common/boot-remote-agents.md` is a thin wrapper that calls `python references/scripts/boot_remote.py --role <role>` and interprets the output
- Same pattern as #335 (health_check.py) — prose is skippable, scripts are not
- `boot_remote.py` shares the `.local-config` parser with `health_check.py` (from #335). Ideally consumes `health_check.py --json` as authoritative input rather than re-implementing detection.

### Q2 — Default ON with strict detection-first
- Config: `Auto Boot Agents: yes` (default)
- **Non-negotiable detection logic** (must be multi-signal, never spawn a running agent):
  - `.stop` sentinel exists in target clone → SKIP (user explicitly stopped it)
  - `.pid` file exists AND PID is alive → SKIP (agent is running)
  - `.pid` file exists BUT PID is dead → SPAWN (agent crashed, revive)
  - No `.pid` AND `current-state` mtime > 2× iteration interval → SPAWN (stalled or never started)
  - No `.pid` AND no `current-state` → SPAWN (fresh state, first boot)
- The detection must be reliable. Hard dependency on #335 (without accurate health data, detection produces duplicate spawns).

### Q3 — One canonical terminal per OS
- **Windows**: `wt.exe` (Windows Terminal) with `cmd /k start-<role>.ps1` fallback if wt is unavailable
- **macOS**: `Terminal.app` via `osascript -e 'tell app "Terminal" to do script "..."'`
- **Linux**: `tmux new-session -d -s squidsquad-<role> "bash start-<role>.sh"` (headless-friendly, works in ssh/Docker/CI)
- **Fallback**: if the canonical terminal is unavailable or spawn fails, print manual boot command and return failure status. Sub-skill exits gracefully so PM doesn't crash.
- Other terminals (iTerm, gnome-terminal, konsole, Git Bash, WSL as Linux) are out of v1 scope. Document as v2 candidates.

### Q4 — Strict sequential ship order: #335 before #4
- #335 (health_check.py) must ship and be verified before #4 starts implementation
- Skill works #335 first in its queue. Then #4.
- This prevents false-positive stalled detection from cascading into false re-boots
- When #4 lands, PM's Step 7 (Agent Health Check) will already be using `health_check.py`, and `boot_remote.py` reuses it for detection

### Q5 — Sub-skill location: `references/sub-skills/common/boot-remote-agents.md`
- Lives in `common/` from day one — signals "shared capability composable by any agent"
- v1 consumer: PM only (composed into PM's CLAUDE.md)
- Future v2+ consumers: installer (end-of-setup auto-boot, follow-up to #328 Q-new21), orchestrators, debug utilities
- No graduation step needed later

## Dev Discretion (skill-lead can choose)

- Exact CLI flags for `boot_remote.py` (e.g. `--role`, `--force`, `--dry-run`, `--all`, `--json`) — just ship what makes sense
- Exact prose wording of the sub-skill markdown (keep domain-only per Q-new14 from FEAT-328 — no SquidSquad internal references)
- Location of rate-limiter state file (`.squidsquad/boot-attempts.log` or similar) — just ship it
- Whether `boot_remote.py` is invoked per-role or in bulk (`--all`) — one implementation choice, not a user question
- Composition anchor placement in PM's CLAUDE.md — where in Step 7 the sub-skill gets called
- Retry/backoff strategy for failed spawns
- Log verbosity and where logs go
- Whether to use `subprocess.Popen` vs `subprocess.run` vs `os.execv` — implementation choice

## Side Effect Mitigations (required)

From RESEARCH.md §8:

1. **False-positive re-boot risk** (H) — HARD DEPENDENCY ON #335. Implementation of #4 must not begin until #335 is verified. `boot_remote.py` should consume `health_check.py --json` output directly rather than re-implementing detection.

2. **`.stop` sentinel must be honored absolutely** (H) — detection logic must ALWAYS check `.stop` first before any other signal. Test case: create `.stop` in a clone with a stale `current-state`, run `boot_remote.py --role X`, verify it does NOT spawn.

3. **Spawn-spam prevention** (M) — boot_remote.py writes to `.squidsquad/boot-attempts.log` (or similar) with timestamp on every spawn attempt. Before spawning, check if the last attempt for the same role was within a cooldown window (suggest 10 min). If yes, skip and log "cooldown active, skipping". This is a v1 requirement, not v2.

4. **Race conditions between multiple PMs** (M) — if two PM clones run on the same machine, they could both try to boot the same missing agent. Use a lock file (`.squidsquad/boot-lock` or similar) with a short TTL (30 sec). Lock is released after spawn completes or fails.

5. **Environment variable inheritance** (M) — spawned terminal should inherit parent env. Document in sub-skill that `CLAUDE_API_KEY` and similar must be set at user-shell level, not at parent-process level only.

6. **Spawn attempt logging** (L) — every spawn attempt logs: timestamp, role, success/failure, reason (stale/crashed/fresh/cooldown/error). Human can audit.

## Acceptance Criteria

- [ ] `references/scripts/boot_remote.py` exists with `--role <name>` and `--all` modes
- [ ] `boot_remote.py` reads `.local-config` and `health_check.py --json` (from #335) for authoritative state
- [ ] Detection logic respects `.stop` sentinel FIRST (before any other check)
- [ ] Detection logic checks `.pid` existence AND process liveness
- [ ] Detection logic handles all 5 states: running / crashed / stalled / fresh / explicitly-stopped
- [ ] Canonical terminal spawn works on Windows (wt.exe), macOS (Terminal.app), Linux (tmux)
- [ ] Fallback prints manual boot instructions when canonical terminal unavailable
- [ ] Rate limiter prevents spawn-spam (cooldown window, state in `.squidsquad/boot-attempts.log`)
- [ ] Lock file prevents race between multiple PM clones
- [ ] `references/sub-skills/common/boot-remote-agents.md` exists with invocation instructions (domain-only per Q-new14)
- [ ] PM's CLAUDE.md composes the sub-skill (in Step 7 or equivalent)
- [ ] `Auto Boot Agents: yes` added to config.md schema, default yes
- [ ] Test: `.stop` sentinel is honored (never spawns stopped agents)
- [ ] Test: running agent is not re-spawned (detection correctly identifies live state)
- [ ] Test: stalled agent (stale current-state) is spawned
- [ ] Test: crashed agent (dead PID) is spawned
- [ ] Test: cooldown window prevents spawn-spam
- [ ] Test: fallback works when canonical terminal absent
- [ ] Test: sub-skill composition into PM's CLAUDE.md renders correctly
- [ ] Manual test: happy-path boot on each of Windows / macOS / Linux (at least two of three)

## Out of Scope

- Multi-terminal support per OS (iTerm, konsole, gnome-terminal, xterm, Git Bash) — deferred to v2
- WSL detection (treat as Linux in v1, revisit in v2)
- Remote machine spawn (different host / SSH) — not in v1
- Auto-boot during installer (`/squidsquad-setup`) — this is the #328 Q-new21 follow-up, separate feature, files after both #328 and #4 ship
- Agent pooling / capacity management (start N agents simultaneously) — v2
- Health metrics / observability beyond the log file — v2
- Auto-disable after repeated spawn failures — v2
- User prompts during spawn (interactive "want to boot this?" flow) — v2, not v1

## Upgrade Path

**For new installs**: the setup wizard's Step 7 (compose role CLAUDE.md files) includes the new sub-skill when composing PM's CLAUDE.md. Automatic.

**For existing installs (this repo)**: PM's live CLAUDE.md must be re-composed to pick up the new sub-skill. Options:
1. Run `/squidsquad-upgrade` which re-composes all role CLAUDE.md files from templates
2. Manually re-run setup's compose step
3. Document as manual step in CHANGELOG — "run /squidsquad-upgrade to enable auto-boot"

Recommend option 1. Confirm with skill that `/squidsquad-upgrade` re-composes PM's CLAUDE.md from the current sub-skill set.

**Migration of existing agents on this repo**: None needed. When PM runs its next cycle after upgrade, it composes the new sub-skill and starts spawning missing teammates on next health-check finding. If no teammates are missing, nothing happens (correct no-op).

## Phase 3 — Test Plan

Test plan subagent will read this CONTEXT.md and RESEARCH.md and produce `FEAT-4-TEST-PLAN.md` covering:

- Unit tests for detection logic (5 states: running / crashed / stalled / fresh / stopped)
- Unit tests for `.stop` sentinel respect
- Unit tests for cooldown / rate limiter
- Unit tests for lock file race prevention
- Integration test: boot a real agent on the test host, verify it comes up
- Integration test: happy-path boot on at least 2 of 3 OSes (manual validation)
- Regression test: PM's existing Step 7 continues to work (detection not broken by the composition)
- Edge: config.md `Auto Boot Agents: no` disables the feature entirely
- Edge: .local-config missing — sub-skill exits gracefully
- Edge: target clone path unreachable (drive missing, permission denied) — sub-skill exits gracefully
- Edge: boot script missing — sub-skill reports and exits gracefully
- Smoke: full cycle with a stalled agent triggering auto-boot end-to-end

## References

- Research: `.squidsquad/skill/planning/FEAT-4-RESEARCH.md`
- Related: #335 (health_check.py — hard dependency)
- Related: #250 (auto-restart wrapper — shipped, orthogonal direction)
- Related: #328 Q-new21 (installer auto-boot — future consumer of this sub-skill)
- Design note: WallyDoodlez/SquidSquad#4 comment thread 2026-04-11
