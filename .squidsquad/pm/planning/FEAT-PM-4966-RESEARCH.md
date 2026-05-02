Now I have a comprehensive understanding. Let me produce the structured research document.

---

# FEAT-PM-4966 Research — Harness Absorbs Wrapper: Full Agent Lifecycle Ownership

## Summary

This task proposes a fundamental architectural shift: the harness (FastAPI process on localhost) absorbs all wrapper-script responsibilities (spawn, monitor, heartbeat, respawn, stop) and eliminates sentinel files `.health`, `.pid`, `.claude-pid`, `.stop`, and `.restart`. The harness would directly spawn `claude` subprocesses, hold PIDs in-memory, write heartbeats itself, and manage the full lifecycle loop — replacing the current model where wrapper shell scripts (`start-{role}.ps1/.sh`) run in per-agent terminal windows and the harness is a thin HTTP layer over sentinel-file polling.

**Recommendation**: Feasible with significant caveats. The wrapper scripts currently perform 8 distinct functions (pre-flight checks, PID singleton lock, git checkout/pull, heartbeat background job, claude spawn with `.claude-pid` tracking, Ctrl+C handling, crash backoff, sentinel-based restart/stop logic). Moving these into the harness is architecturally clean (aligns with vault decision `[[decision-pid-primary-liveness]]` — "just use PID, it's more direct") and the human preference for direct/mechanical checks over indirect state files. However, the *visible terminal* constraint (#4439 locked decision: "Agents stay visible") is the primary design risk — the harness runs in its own terminal, and spawning claude as a child process would make it invisible unless each agent still gets a terminal window. The generated shell scripts are also *stale* vs the templates (the templates have the loop-based architecture from #3807 but were never regenerated), meaning the current running agents are on an older, simpler code path — this must be reconciled before any harness absorption.

## Vault Context

- **BRIEFING.md priorities**: #4439 Harness shipped, #4709 Harness Phase 2 planned — this task is a continuation of the harness epic
- **Related decisions**: [[decision-pid-primary-liveness]] — PID is primary for liveness, `.health` is informational only. This task eliminates `.health` entirely in favor of direct process monitoring. Strongly aligns.
- **Related decisions**: [[decision-reboot-kills-child]] — `.pid` = wrapper, `.claude-pid` = claude. Reboot kills claude (child), not wrapper (parent). If harness owns both, this distinction collapses into a single PID per agent.
- **Related decisions**: [[decision-watchdog-supervisor]] — centralized lifecycle management. The harness absorbing the wrapper is the logical conclusion of this decision: the harness becomes the sole lifecycle owner.
- **Related decisions**: [[decision-self-healing-sentinel]] — two-tier self-healing (unstick + file root-cause bug). Harness direct ownership enables Tier 1 immediately (restart dead agents without sentinel polling latency).
- **Human preferences**: "just use PID, it's more direct" and "prefer direct/mechanical checks over indirect state files" — this task is directly in line. Also: agents stay in visible terminal windows (locked from #4439).
- **Related learnings**: [[learning-powershell-start-job-cwd]] — PowerShell background jobs have CWD issues. Relevant if harness spawns on Windows.

## Impact Analysis

- **Files touched**:
  - `references/scripts/harness.py` — major rewrite: direct claude spawn, PID ownership, heartbeat, respawn loop, new endpoints
  - `references/templates/start-role.ps1` — **deleted** (wrapper eliminated)
  - `references/templates/start-role.sh` — **deleted** (wrapper eliminated)
  - `.squidsquad/start-{role}.ps1` (all roles × clones) — **deleted** or replaced with thin harness-launch stubs
  - `.squidsquad/start-{role}.sh` (all roles × clones) — **deleted** or replaced
  - `.squidsquad/start-squad.ps1` / `.squidsquad/start-squad.sh` — **deleted** (harness replaces)
  - `references/scripts/boot_remote.py` — spawn logic absorbed into harness; kept as library fallback; `_needs_boot()`, `_find_boot_script()`, `_spawn_terminal()` deprecated
  - `references/scripts/reboot_agent.py` — absorbed into harness restart endpoint; kept as shim
  - `references/scripts/health_check.py` — `.health` file reading removed; PID-only liveness check remains
  - `references/scripts/cycle_post.py` — `.stop-after-cycle` handling remains (line ~454-479 `_do_stop_after_cycle_check`); the rest of sentinel logic removed
  - `references/scripts/cycle_pre.py` — no sentinel changes, but may need harness-aware health reporting
  - `references/scripts/start_team.py` — redirected to harness API calls; sentinel-writing functions removed
  - `references/scripts/compose.py` — `boot_role()` / `boot_all()` removed or repurposed
  - `references/scripts/squidsquad_cli.py` — new `health` and `config` subcommands added
  - `references/sub-skills/common/agent-lifecycle.md` — rewritten for harness-owned model
  - `references/sub-skills/common/self-restart.md` — removed (harness owns restart)
  - `references/sub-skills/common/cycle-runner.md` — updated for new exit flow
  - `.squidsquad/config.md` — possible new harness config fields

- **Behavior changes**:
  1. **Wrapper scripts eliminated**: Agents no longer have per-role shell scripts. Harness spawns claude directly via `subprocess.Popen` with appropriate terminal window (wt.exe on Windows, Terminal.app on macOS, tmux on Linux).
  2. **PID ownership**: Harness holds agent PIDs in-memory (not in `.pid` / `.claude-pid` files). Liveness = `_is_process_alive(pid)` directly — no `.health` polling.
  3. **Heartbeat**: Harness monitors agent process liveness via PID check every ~5s. No `.health` file written by background job.
  4. **Respawn loop**: Harness implements the crash-backoff-respawn loop currently in wrapper templates. On claude exit: check `.stop-after-cycle` → respawn; check crash count → backoff or `.stop`. 
  5. **Ctrl+D graceful shutdown**: Harness intercepts Ctrl+D (EOF on stdin) in its console, triggers graceful agent shutdown (write `.stop-after-cycle`, wait for idle, kill if timeout).
  6. **New endpoints**: `GET /agents/{role}/health` returns live health (PID alive, current phase, uptime). `GET /agents/{role}/config` returns role configuration.
  7. **`.stop-after-cycle` remains**: Kept as harness→agent signal (harness writes it, `cycle_post.py` reads it at line ~454, exits with code 42). `cycle_post.py` deletes it after reading (already does at line ~454-456 implicitly via the check).
  8. **`.stop` eliminated**: Harness stops agents by killing the process directly, not by writing a sentinel file that the wrapper polls.

- **Dependencies**:
  - FastAPI + uvicorn (already present)
  - `subprocess.Popen` with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` on Windows
  - `tasklist` / `os.kill(pid, 0)` for liveness (already in `boot_remote._is_process_alive`)
  - Terminal spawning: `wt.exe` (Windows), `osascript` (macOS), `tmux` (Linux) — already in `boot_remote._spawn_terminal`

## Side Effects

- **Risk 1: Visible terminal constraint** — Severity: H — The harness spawns agents via wt.exe (fire-and-forget), same as today. But if the harness spawns claude as a *child process* (without wt.exe), agents become invisible (headless). The locked #4439 decision requires visible terminals. **Mitigation**: Harness must still spawn each agent in its own terminal window via wt.exe/Terminal.app/tmux — same as `boot_remote._spawn_terminal()` today. The harness cannot directly subprocess.Popen claude and hold the PID unless it's also the terminal owner. This may mean the harness spawns a *thin terminal launcher* (not the full wrapper) or uses the existing terminal-spawn-then-poll-PID approach. The harness would then discover the claude PID from the spawned process.

- **Risk 2: Pre-flight checks must move to harness** — Severity: H — Wrapper scripts currently perform: `gh auth status`, working branch checkout, `git pull --ff-only`, permissions injection, config sync, state bus init. These must move to harness or to `cycle_pre.py`. `cycle_pre.py` already handles git pull (line ~106-116) and branch enforcement (line ~119-148), but gh auth check and permissions injection are wrapper-only. **Mitigation**: Move gh auth check to harness pre-spawn. Move permissions injection to harness or compose.py. `cycle_pre.py` already handles pull + branch — harness doesn't need to duplicate.

- **Risk 3: Generated scripts are stale vs templates** — Severity: M — The actual `.squidsquad/start-skill.ps1` (line ~139-196) has the OLD single-shot restart pattern (one `.restart` check, one crash retry). The template `references/templates/start-role.ps1` (line ~148-221) has the NEW loop architecture (indefinite respawn, `.stop-after-cycle`, `.stop`, exponential backoff). The templates were updated for #3807 but `compose.py boot-all` was never run. This means: (a) running agents use old logic, (b) the harness absorption task must reconcile which architecture to absorb. **Mitigation**: Absorb the loop-based template architecture (it's the intended design). The task becomes simpler because the templates already have the exact logic harness needs to own.

- **Risk 4: Clone isolation — multiple clone directories** — Severity: M — Each agent runs from a different clone directory (`_get_clone_path(role)` from `.local-config`). The harness must manage processes across multiple filesystem paths, each with its own git state. The wrapper scripts handled this because each ran `cd`'d to its clone root. **Mitigation**: Harness spawns each agent with `cwd=clone_path`. This is already how `boot_remote._spawn_terminal` works (line ~395-406: `cwd=str(clone_root)`).

- **Risk 5: `.stop-after-cycle` semantics change** — Severity: M — Currently the wrapper reads `.stop-after-cycle` after claude exits and respawns. Under the new model, harness reads it and respawns. The file must still be written to the agent's clone directory (not the harness's repo root) since agents run in different clones. **Mitigation**: Harness knows each agent's clone path from `.local-config`. It monitors `.stop-after-cycle` in `{clone_path}/.squidsquad/{role}/.stop-after-cycle`.

## Edge Cases

- **Agent crashes mid-cycle (before cycle_post runs)**: Harness detects claude process exit (non-zero), applies crash backoff. No `.stop-after-cycle` written. Same as current wrapper behavior but centralized in harness.

- **Harness crashes while agents are running**: Agents survive (they're in independent terminal windows via wt.exe). On harness restart, it must rediscover agent PIDs. Without `.pid` files, it can't. **Mitigation**: Harness writes its own PID registry to `.squidsquad/.harness-pids.json` (or memory-only with recovery via `tasklist` scanning for claude processes). Or: keep `.pid` files as harness-written (not wrapper-written), making them the harness's durable state.

- **Agent process killed externally (Task Manager, SIGKILL)**: Harness detects PID is dead via liveness poll. If `.stop` was not intended, harness respawns (respecting backoff). No `.health` staleness issue because the check is direct PID liveness.

- **Multiple harness instances (port collision)**: Existing port discovery (`find_free_port`, `.harness-port` file) handles this. The singleton lock for harness itself is the port file + PID check.

- **Agent in different clone needs git pull before cycle**: `cycle_pre.py` handles git pull (line ~106). Harness doesn't need to pull — it just spawns. The agent's `cycle_pre.py` runs inside its clone and pulls there. **However**, the wrapper currently does a pre-flight pull before first claude spawn. If harness spawns a fresh agent for the first time, the clone might be stale. **Mitigation**: Harness runs `git pull` in the agent's clone directory before first spawn, or relies on `cycle_pre.py` handling it on cycle 1.

- **Ctrl+D vs Ctrl+C**: The task specifies Ctrl+D for graceful shutdown. On Windows terminals, Ctrl+D is not a standard signal (it's EOF on Unix). Ctrl+C sends SIGINT which uvicorn already catches (line ~622-623). **Mitigation**: Use Ctrl+C for graceful shutdown (same as current harness behavior) and document it. If Ctrl+D must work, it requires custom stdin handling in the harness console loop.

## Integration Risks

- **State branch commits**: `cycle_post.py` commits state to `squid-squad` branch after agent cycle. The `.stop-after-cycle` check in `cycle_post.py` (line ~563) runs AFTER commit (line ~549), so state is preserved. If harness kills agent mid-cycle, `cycle_post.py` never runs → state not committed. Same as current wrapper behavior — acceptable.

- **Watchdog compatibility**: The vault references a `watchdog.py` that was planned ([[decision-watchdog-supervisor]]) but the source file exists only in `__pycache__/` (no `.py` source). The harness absorbing lifecycle management effectively replaces the planned watchdog — harness IS the watchdog. This is a consolidation, not a conflict.

- **start_team.py / squidsquad_cli.py**: Both currently write sentinel files (`.stop`, `.stop-after-cycle`). After harness absorption, `start_team.py` becomes a thin CLI that calls harness API endpoints (same as `squidsquad_cli.py`). These two scripts partially overlap — consolidation opportunity.

- **add_role.py --boot**: Currently calls the role's `start-{role}.ps1` directly. After wrapper elimination, it must call the harness API or use harness spawn logic. Low impact — only used at initial setup.

- **statusline.sh**: Reads `.squidsquad/{role}/current-state` for status display. This file is written by `cycle.py status-bar` (called by agents and `cycle_pre.py`/`cycle_post.py`), not by the wrapper. No impact.

## Upgrade & Migration

- **New config values**: 
  - `Harness` → `Enabled`: already exists (line ~119-122 of config.md)
  - `Harness` → `Port`: already exists
  - Potential new: `Harness` → `CrashBackoffMax` (default: 5), `Harness` → `HeartbeatInterval` (default: 5)

- **New files**: 
  - `.squidsquad/.harness-pids.json` — durable PID registry for crash recovery (or harness keeps in-memory only)

- **Template changes**: 
  - `references/templates/start-role.ps1` — **deleted**
  - `references/templates/start-role.sh` — **deleted**
  - Agent CLAUDE.md sub-skills updated: `self-restart.md` removed, `agent-lifecycle.md` rewritten
  - `cycle-runner.md` updated for new exit flow (no `restart_needed` field)

- **Upgrade steps**:
  1. Stop all running agents (existing wrappers)
  2. Deploy new harness with direct spawn capability
  3. Clean stale sentinel files across all clones (`.health`, `.pid`, `.claude-pid`, `.restart`, `.stop`)
  4. Run `compose.py deploy-all` to regenerate CLAUDE.md files with updated sub-skills
  5. Delete all `start-{role}.ps1/.sh` scripts from clone directories
  6. Start agents via harness: `squidsquad start`

- **Graceful degradation**: If harness is not running, agents cannot be spawned. Existing `boot_remote.py` and `start_team.py` can be kept as fallback (direct terminal spawn without harness) during transition. The old wrapper scripts could be kept for one version as emergency fallback.

## Open Questions

- **Q1: How does the harness spawn agents in visible terminals while holding their PIDs?** — **Why**: `wt.exe new-tab` returns immediately (fire-and-forget). The harness gets the `wt.exe` PID, not the claude PID. To hold the claude PID directly, the harness would either: (a) spawn a thin terminal launcher that reports back the claude PID (e.g., via a file or HTTP), or (b) use `Start-Process -PassThru` inside the terminal which writes `.claude-pid` — but this recreates the sentinel file pattern. The PID ownership goal conflicts with the visible terminal requirement unless there's a way to get the child PID from wt.exe.

- **Q2: Should the harness write a durable PID registry for crash recovery?** — **Why**: If harness crashes and restarts, it needs to rediscover running agent processes. Without `.pid` files, the only option is scanning all processes for claude instances — fragile and slow. A `.harness-pids.json` file would be a sentinel file by another name, partially defeating the purpose.

- **Q3: Where do pre-flight checks live after wrapper elimination?** — **Why**: Currently: wrapper does gh auth, branch checkout, git pull, permissions injection, config sync, state bus init. Some overlap with `cycle_pre.py`. If harness does all of these before spawn, it couples harness to git/auth operations. If `cycle_pre.py` does them, the first cycle starts with potentially stale code.

- **Q4: Ctrl+D vs Ctrl+C — which signal for graceful shutdown?** — **Why**: The task specifies Ctrl+D but on Windows this is not a standard process signal. Ctrl+C is already handled by uvicorn (KeyboardInterrupt at line ~622). The human uses Windows 11 primarily. Getting this wrong means the graceful shutdown flow doesn't work on the primary platform.

## Recommendation

**Feasible with caveats.** The architectural direction is correct and aligns with vault decisions. The primary blocker is resolving the tension between "harness owns PIDs directly" and "agents stay in visible terminal windows." The most practical path is:

1. **Phase A**: Harness spawns agents via wt.exe (visible terminals) with a thin launcher script that writes the claude PID to a known location. The harness reads this PID after spawn. This preserves visible terminals while giving harness PID ownership. The `.pid` and `.claude-pid` files become harness-managed (harness writes them, not wrapper).

2. **Phase B**: Move all wrapper-loop logic (respawn, crash backoff, `.stop-after-cycle` handling) into the harness. The terminal launcher becomes a one-shot "spawn claude and write PID" script — no loop, no sentinel logic.

3. **Phase C** (future): If/when headless agents become acceptable, harness can spawn claude as a direct child process and own PIDs without any terminal indirection.

The two new endpoints (`/agents/{role}/health`, `/agents/{role}/config`) are straightforward additions to the harness with no architectural risk.

## Vault Candidates

- **Type**: decision — "Harness is the agent lifecycle owner; wrapper scripts eliminated" — **Why**: This is the culmination of PID-primary-liveness, watchdog-supervisor, and reboot-kills-child decisions. Archival of the wrapper→harness transition reasoning will be essential for future contributors.

- **Type**: pattern — "Terminal-spawn-then-PID-discovery pattern" — **Why**: The wt.exe fire-and-forget constraint forces a specific pattern (spawn terminal, poll for PID file written by launcher) that's reusable for any Windows terminal-based process management.

- **Type**: learning — "Generated scripts can drift from templates when compose.py boot-all is not run after template changes" — **Why**: Discovered during this research: `references/templates/start-role.ps1` has the #3807 loop architecture but actual `.squidsquad/start-skill.ps1` does not. This is a process gap worth documenting — template changes without regeneration = silent drift.

- **Type**: learning — "Pre-flight check duplication between wrapper and cycle_pre.py" — **Why**: Both wrapper scripts and `cycle_pre.py` do git pull and branch checkout. Consolidating these into `cycle_pre.py` alone (as #3807 proposed) would eliminate ~30 lines of duplicated logic per agent per platform. The harness absorption task is the right time to finish this consolidation.

- **Type**: decision — "Ctrl+C as universal graceful shutdown signal (not Ctrl+D)" — **Why**: Windows lacks Ctrl+D process signaling. The harness already handles KeyboardInterrupt. Standardizing on Ctrl+C for graceful shutdown across all platforms avoids platform-specific signal handling complexity.