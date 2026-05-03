I now have a comprehensive picture. Let me produce the final audit.

---

# AUDIT-4966-R4-SCRIPTS Research — Harness Absorbs Wrapper (Script Change Review)

## Summary

This audit reviews seven scripts changed in #4966 (Harness absorbs wrapper): `harness.py`, `cycle_post.py`, `thin_launcher.py`, `start_team.py`, `boot_remote.py`, `compose.py`, and `health_check.py`. The core architecture change moves agent lifecycle ownership from per-agent wrapper scripts (with respawn loops) into a unified FastAPI harness that monitors PID liveness and manages an intent state machine (running/stopping/restarting). Agents spawn via a thin launcher that simply starts claude, writes `.claude-pid`, and exits — the harness handles all reboot/stop decisions.

The overall design is sound and internally consistent. The PID-based liveness model directly addresses the vault decision [[decision-pid-primary-liveness]] and the human preference for "mechanical checks over state files." However, the review found **6 CRITICAL issues** that must be fixed before ship — most notably a non-existent function call that silently fails, a daemon-thread race in shutdown, dead code writing orphan sentinel files, and stale `.stop-after-cycle` references in all deployed CLAUDE.md templates that agents will read as current instructions.

## Vault Context

- **BRIEFING.md priorities**: #4221 (Agent harness — supervisor process), #4439 (Harness epic — shipped), #4709 (Phase 2 — planned). #4966 is the implementation of harness absorbing wrapper, a direct descendant of #4221/#4439.
- **Related decisions**: [[decision-pid-primary-liveness]] — "PID is primary for liveness, `.health` is informational only." The harness implements this exactly: direct PID check first, `.claude-pid` file fallback, `.health` file only as legacy fallback.
- **Related decisions**: [[decision-reboot-kills-child]] — "Reboot kills claude subprocess, not wrapper." With the harness architecture and thin launcher, this decision is partially obsoleted — there is no wrapper to keep alive, but the shutdown path in harness.py still correctly targets `claude_pid` via `reboot_agent._read_claude_pid` and `_kill_process`.
- **Human preferences**: "Prefer direct/mechanical checks over indirect state files" — the harness's direct PID polling aligns perfectly. "Systems should self-heal: detect stuck states → unstick immediately" — the auto-reboot on unexpected death implements this. "Never ship with failed TCs" — tests exist but coverage gaps remain (no thin launcher integration test, no harness shutdown integration test).
- **Related learnings**: [[learning-powershell-start-job-cwd]] — terminal spawning is OS-aware, which boot_remote.py handles correctly for Windows/macOS/Linux.

## Impact Analysis

- **Files touched**: `harness.py` (new, 903 lines), `cycle_post.py` (modified, 638 lines), `thin_launcher.py` (new, 97 lines), `start_team.py` (modified, 243 lines), `boot_remote.py` (modified, 651 lines), `compose.py` (modified, `boot_role` no-oped), `health_check.py` (deprecation notice added)
- **Behavior changes**:
  - Agent spawn now uses `thin_launcher.py` instead of wrapper scripts
  - Lifecycle decisions (stop/restart) use harness API + intent state machine, not sentinel files
  - `cycle_post.py` queries harness API for intent instead of checking `.stop-after-cycle` file
  - `start_team.py` delegates to harness API, falling back to `.stop` sentinel
  - `compose.py boot_role` is a no-op (wrapper scripts eliminated)
  - Context pressure restarts: agent exits with code 42, harness auto-reboots
- **Dependencies**: `fastapi`, `uvicorn` (new harness deps), `boot_remote`, `health_check`, `reboot_agent` (imported by harness), `state_bus` (imported by cycle_post)

## Side Effects

- **Risk 1**: Harness crash loses in-flight intent state — Severity: **M** — Mitigation: `.harness-state.json` persists intents. However, if harness crashes between setting `intent=stopping` and agent querying it, the agent will never see the stop signal. File-based sentinels don't have this problem (signal survives writer crash). The state file is written on intent change (line 608 `state.save_state()`), and crash recovery loads it (line 349 `state.load_state()`), so a harness restart recovers the intent. If harness is permanently down, the fallback is `start_team.py` writing `.stop` sentinel.

- **Risk 2**: Thin launcher agents don't write `.health` files — Severity: **L** — Mitigation: The harness uses direct PID checks as primary. The `.health` fallback in `update_health()` (lines 183-197) only triggers when no PID is found, which won't happen for thin-launcher agents. Legacy wrapper agents still write `.health` files and are handled correctly in the fallback path.

## Edge Cases

- **Agent starts and crashes before first health poll**: The harness won't have registered the agent yet (`agent.claude_pid` is None, `.claude-pid` file was written then cleared by crash). On the next poll, `_read_claude_pid` returns `(None, False)`, the `.health` fallback runs, and the agent is marked unknown. Auto-reboot only triggers when `prev_status == "running"`, so this agent is **never auto-rebooted**. The agent must be manually restarted. This is by design for crash-loop prevention but may surprise users.

- **Agent exits with code 42 but harness has crashed**: The thin launcher propagates exit code 42, but nobody reads it. The harness would have seen the dead PID and auto-rebooted (if intent=running). If harness is down and restarts, crash recovery loads the state, sees the agent was "running," and the health poll detects the dead PID → auto-reboots. This is correct.

- **Rapid stop/start/stop sequence**: If a user rapidly issues stop → start → stop via the API, the intent transitions could race. The lock protects in-memory state, but there's no debounce. `stop_all()` (line 463) checks if agent is already `INTENT_STOPPING` and skips — but a rapid stop→start→stop could leave intent in an inconsistent state. Mitigation: intent is set under lock, and the health poller resolves conflicts (e.g., if intent=stopping but status=running, the poller waits for death).

- **Port conflict during startup**: `find_free_port()` (line 731) gracefully finds an alternative port. The port discovery file is written atomically. If two harness instances start simultaneously, the second gets a different port. No collision.

## Integration Risks

- **`reboot_agent.py` is wrapper-centric but still imported by harness**: The harness shutdown path (line 701) calls `reboot_agent._read_claude_pid(Path(clone_path), role)` and `reboot_agent._kill_process(claude_pid)`. These are pure utility functions that work regardless of wrapper/thin-launcher architecture, so this is safe. However, `reboot_agent.py`'s main `reboot()` function (line 108) writes `.restart` sentinels and relies on wrapper processes — calling it for thin-launcher agents would be incorrect. The harness does NOT call `reboot_agent.reboot()` (test at line 400 mocks it but the actual restart endpoint doesn't invoke it). **However**, the test at line 400 of `test_harness.py` patches `reboot_agent.reboot` — this mock is misleading because the actual endpoint doesn't call it.

- **`cycle_post.py` REST call to harness on every cycle**: Every agent cycle now makes an HTTP call to `127.0.0.1:{port}/agents/{role}`. This adds ~5ms latency per cycle (localhost). The 5-second timeout is generous. If harness is slow or unresponsive, the agent defaults to "continue running" — safe default. However, if the harness port changes (port conflict), the port file discovery in `_discover_harness_port()` (line 446) walks parent directories — if the agent clone is a sibling of the repo, the walk may not find the port file. Mitigation: `_discover_harness_port` falls back to default port 7373.

- **CLAUDE.md template staleness**: All four deployed agent CLAUDE.md files (`.squidsquad/{dm,pm,qa,skill}/CLAUDE.md`) still describe the `.stop-after-cycle` sentinel-based lifecycle, wrapper mechanics, and `start_team.py --reboot` writing sentinel files. Agents reading these will try to use mechanisms that no longer exist. **This is the highest-risk integration gap** — agents must be recomposed (`compose.py deploy-all`) after #4966 ships.

## Upgrade & Migration

- **New config values**: `harness-enabled` (Harness/Enabled in config.md), `harness-port` (Harness/Port in config.md). Both already have `FIELD_MAP` entries confirmed by tests (line 196-208 of test_harness.py).
- **New files**: `references/scripts/harness.py`, `references/scripts/thin_launcher.py`, `.squidsquad/.harness-state.json` (runtime), `.squidsquad/.harness-port` (runtime)
- **Template changes**: `compose.py boot_role` is a no-op. Wrapper templates (`start-role.ps1/.sh`) are eliminated. All deployed CLAUDE.md files need recomposition to remove `.stop-after-cycle` references.
- **Upgrade steps**:
  1. Run `python references/scripts/compose.py deploy-all` to regenerate CLAUDE.md files with updated lifecycle docs
  2. Stop all running wrapper-based agents (they'll be replaced by thin-launcher spawns)
  3. Start harness: `python references/scripts/harness.py`
  4. Use `start_team.py --all` to boot agents via harness
  5. Remove stale `.restart` sentinel files from `.squidsquad/{role}/` directories
- **Graceful degradation**: If harness is not running, `cycle_post.py` `_query_harness_intent()` returns `None` and agents continue running. `start_team.py` falls back to writing `.stop` sentinel. Legacy wrapper agents continue to work — `boot_remote._find_boot_script()` prefers thin launcher but falls back to wrapper scripts. The `.health` file fallback in `harness.update_health()` handles legacy wrapper agents.

## Open Questions

- **Q1**: Should `_do_restart_sentinel()` in `cycle_post.py` be fully removed (not just deprecated) since thin launcher has no sentinel-checking loop? — **Why**: It writes `.restart` files to disk that nothing reads. Keeping it risks confusing operators who see `.restart` files and assume they do something. If backward compat is needed, it should at least be gated behind a "is legacy wrapper" check.
- **Q2**: Should the harness implement a "pending intent" queue for the case where harness crashes between setting intent and agent querying? — **Why**: File-based sentinels survive writer crashes; API-based intent doesn't. The state-file crash recovery partially addresses this, but if harness is permanently down, the stop signal is lost.
- **Q3**: Should `start_team.py --force` path be removed since `_kill_agent` doesn't exist? — **Why**: It's dead code that silently fails. Either implement `_kill_agent` in `reboot_agent.py` or remove the force-reboot path.

## Recommendation

**Feasible with caveats** — The harness architecture is sound and well-tested (44 unit tests pass for the harness). However, the 6 CRITICAL issues below must be resolved before shipping. The CLAUDE.md template staleness is the most urgent because it actively misinforms running agents about how lifecycle works.

## Critical Issues

### C1: `start_team.py:145` calls non-existent `reboot_agent._kill_agent(role)` — **Broken force reboot**
- **File**: `references/scripts/start_team.py`, line 145
- **Problem**: `reboot_agent.py` has no `_kill_agent` function. The call `reboot_agent._kill_agent(role)` raises `AttributeError`, silently caught by `except (ImportError, AttributeError): pass` on line 146. Force reboot (`start_team.py --reboot skill --force`) silently does nothing after this point.
- **Fix**: Either implement `_kill_agent(role)` in `reboot_agent.py` that kills via PID discovery, or replace the call with the harness API `POST /agents/{role}/restart` and remove the force-kill path.

### C2: `harness.py:648-722` — **Shutdown daemon thread race with `os._exit(0)`**
- **File**: `references/scripts/harness.py`, lines 648-722
- **Problem**: `/shutdown` endpoint spawns a daemon thread (`_do_shutdown`) that waits for agents to idle (up to 30s), kills claude processes, cleans up port file, then calls `os._exit(0)`. Daemon threads are terminated abruptly when the parent process exits. If uvicorn's event loop exits before the thread completes, agents are left running. Additionally, `time.sleep(1)` before `os._exit(0)` (line 719) is fragile — process kill may take longer.
- **Fix**: Use a non-daemon thread and signal the main thread to exit after shutdown completes. Or use `asyncio.to_thread` with an explicit shutdown event. The `os._exit(0)` call should only happen after the thread sets a completion flag.

### C3: `cycle_post.py:436-443` — **Dead code: `_do_restart_sentinel` writes `.restart` that nothing reads**
- **File**: `references/scripts/cycle_post.py`, lines 428-443 and call at line 609
- **Problem**: `_do_restart_sentinel()` writes `.restart` sentinel to disk. The thin launcher has no sentinel-checking loop — it just waits for claude to exit. The harness uses PID monitoring, not `.restart` files. The file is written and never consumed. This is dead code that persists orphan files.
- **Fix**: Remove `_do_restart_sentinel()` entirely. The `_do_stop_after_cycle_check()` (line 619) already handles exit code 42 for harness respawn. If backward compat with legacy wrappers is needed, gate behind a "wrapper exists" check.

### C4: `harness.py:147-149` — **Silent failure on missing `.local-config`**
- **File**: `references/scripts/harness.py`, lines 146-149
- **Problem**: `boot_remote._get_all_roles()` calls `_parse_local_config()` which calls `sys.exit(2)` if `.local-config` is missing. The harness catches `(SystemExit, Exception)` and silently returns `None`. This means the health poller silently stops working — no agents are discovered, no auto-reboot, no logging. The harness appears healthy (`/status` returns 200) but does nothing.
- **Fix**: Log a prominent warning when `_get_all_roles()` fails. Consider making `.local-config` optional for harness (it only needs clone paths for PID file location). At minimum, surface the failure in the `/status` endpoint.

### C5: All deployed CLAUDE.md files reference obsolete `.stop-after-cycle` sentinel mechanics
- **Files**: `.squidsquad/{dm,pm,qa,skill}/CLAUDE.md` (15+ references across 4 files)
- **Problem**: Agent instructions describe: "cycle_post.py writes `.stop-after-cycle` mechanically when pressure exceeds threshold", "start_team.py --reboot writes `.stop-after-cycle`", "Sentinel files: `.stop-after-cycle` (graceful restart)". All of this is obsolete after #4966. Agents reading these instructions will try to use mechanisms that don't exist. The harness intent API replaces all of this.
- **Fix**: Run `python references/scripts/compose.py deploy-all` after updating the source templates. The source templates in `references/roles/` and `references/sub-skills/` must also be audited for `.stop-after-cycle` references and updated to describe the harness intent API.

### C6: `reboot_agent.py` architecture is wrapper-centric but still the canonical "reboot" module
- **File**: `references/scripts/reboot_agent.py`, lines 108-234
- **Problem**: The `reboot()` function checks "if wrapper is running" (line 126), reads `.pid` as "wrapper PID" (line 127), writes `.restart` sentinel (line 192), and assumes a wrapper loop will process it. For thin-launcher agents, there is no wrapper. The harness restart endpoint (line 615-644) sets `intent=restarting` and lets the agent exit naturally — it does NOT call `reboot_agent.reboot()`. But the test (test_harness.py:400) patches `reboot_agent.reboot`, which is misleading since the actual endpoint doesn't invoke it. The harness only uses `reboot_agent._read_claude_pid` and `reboot_agent._kill_process` from this module (utility functions that work fine).
- **Fix**: Either: (a) update `reboot_agent.py` to be thin-launcher-aware (use harness API for restart, fall back to wrapper sentinel), or (b) deprecate `reboot_agent.reboot()` and move the utility functions to `boot_remote.py`. Fix the misleading test mock.

---

## Non-Critical Issues

### N1: `start_team.py:201` — Stale help text
- **File**: `references/scripts/start_team.py`, line 201
- **Problem**: `help="Graceful restart (write .stop-after-cycle)"` — the code calls harness API, not write sentinel.
- **Fix**: Update to `help="Graceful restart via harness API"`.

### N2: `wizard.py:1057-1067` — Calls no-op `compose.boot_role`
- **File**: `references/scripts/wizard.py`, lines 1057-1067
- **Problem**: `compose.boot_role` is now a no-op (line 922-930 of compose.py). The wizard still calls it and prints a "WARNING: Failed to generate boot scripts" on failure, which will never happen because it's a no-op.
- **Fix**: Remove the boot script generation step from wizard, or replace with thin launcher validation.

### N3: `add_role.py:310,312` — Stale manual boot instructions
- **File**: `references/scripts/add_role.py`, lines 310, 312
- **Problem**: Prints instructions referencing `.squidsquad/start-{role}.ps1` / `.sh` wrapper scripts that are being eliminated.
- **Fix**: Update to reference `thin_launcher.py` or `start_team.py`.

### N4: `harness.py:795-856` — 3rd Ctrl+C calls `os._exit(1)` bypassing all cleanup
- **File**: `references/scripts/harness.py`, lines 848-856
- **Problem**: `_force_kill()` at line 848 calls `os._exit(1)` which immediately terminates the process. The lifespan shutdown handler (port file cleanup, poller stop) never runs. While `_force_kill` does try to unlink the port file (line 853), the state file is not saved, the poller thread is not stopped.
- **Fix**: Call `state.stop_poller()` and `state.save_state()` before `os._exit(1)`. Also consider using `sys.exit(1)` instead to allow finally blocks and `__del__` to run.

### N5: Port file cleanup fragmented across 3 locations
- **Files**: `harness.py` lines 380-388 (lifespan shutdown), 708-716 (shutdown thread), 853-855 (Ctrl+C force kill), 897-899 (main finally)
- **Problem**: Four different code paths try to clean the port file. While `missing_ok=True` prevents crashes, this is fragile maintenance-wise.
- **Fix**: Extract a single `_cleanup_port_file()` function.

### N6: `cycle_post.py:517-526` — Context pressure fallback silently ignores read errors
- **File**: `references/scripts/cycle_post.py`, lines 517-526
- **Problem**: If `cycle-output.json` lacks `context_pressure`, the code reads `cycle-input.json` directly. If the fallback read fails (e.g., file missing, JSON parse error), `ctx` stays empty, `exceeded` defaults to False, and context-pressure-triggered restart is silently skipped.
- **Fix**: Log a warning when the fallback fails. Consider whether the fallback should default to `exceeded=True` to be safe (restart rather than risk degraded performance).

### N7: `health_check.py:5-8` — DEPRECATION notice but still fully functional
- **File**: `references/scripts/health_check.py`, lines 5-8
- **Problem**: The script is labeled "deprecated" and "legacy fallback" but is still imported and used by `harness.update_health()` (line 186). It's the only health-checking mechanism for legacy wrapper agents. Labeling it deprecated while it's still in active use is misleading.
- **Fix**: Remove the deprecation notice, or add a comment that it's "legacy compat only, not needed for thin-launcher agents."

## Vault Candidates

- **Type**: decision — **"Intent API vs sentinel files: API loses in-flight signals on crash"** — **Why**: The harness intent state machine represents a tradeoff (API simplicity vs file persistence). The `.harness-state.json` crash recovery partially mitigates this, but the core design choice is worth documenting for future lifecycle changes.
- **Type**: learning — **"Thin launcher has no respawn loop — must not write restart sentinels"** — **Why**: The `_do_restart_sentinel` dead code in `cycle_post.py` exists because the migration from wrapper→thin launcher wasn't complete. Future migrations should audit for orphan consumers of sentinel files.
- **Type**: pattern — **"Daemon threads + os._exit = race condition"** — **Why**: The shutdown path in harness.py uses a daemon thread that calls `os._exit(0)`. This is a recurring anti-pattern in SquidSquad (also seen in reboot paths). A vault pattern documenting the safe approach (non-daemon thread + signal main loop) would prevent future occurrences.
- **Type**: learning — **"CLAUDE.md recomposition must follow lifecycle changes"** — **Why**: All 4 deployed CLAUDE.md files still describe obsolete `.stop-after-cycle` mechanics. The compose→deploy pipeline must be part of every lifecycle-affecting change. This is a process gap worth remembering.

## Verdict

**FAIL** — The 6 CRITICAL issues must be resolved before shipping. C1 (non-existent function) and C2 (shutdown race) are correctness bugs that cause silent failures. C3 (dead restart sentinel) and C5 (stale CLAUDE.md templates) are operational risks that will confuse both agents and operators. C4 (silent failure on missing config) is a diagnostic gap. C6 (wrapper-centric reboot module) is an architectural inconsistency. The non-critical issues are cosmetic/cleanup items that can be addressed post-ship.