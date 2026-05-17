# RESEARCH-4792 — Harness Sole-Authority Lifecycle Audit

**Issue**: #4792 (rescoped from "deprecate sentinel files" → "harness sole-authority lifecycle")
**Phase**: 1 (Research, read-only)
**Date**: 2026-05-17
**Author**: pm-lead
**Hard-prereq partner**: #8692 (singleton enforcement — shipped)
**Related on-hold**: #7693 (context-pressure restart not respawning), #8689 (restart endpoint latency — shipped)

## 0. Executive Summary

The harness (`references/scripts/harness.py`) is already the *primary* lifecycle authority via FastAPI on port 7373 plus `.harness-state.json` persistence. The HTTP API exposes `POST /agents/{role}/start|stop|restart`, `POST /agents/all/start|stop`, `POST /shutdown`, and a per-role intent state machine (`running | stopping | restarting | stopped`).

However the system is **split-brain in four distinct ways**, each of which is a parallel control path that can silently override the harness intent:

1. **`.stop` sentinel** — read by `boot_remote._needs_boot()`, `harness.update_health()`, `health_check.check_agent_health()`, `reboot_agent.reboot()`, written by `start_team.cmd_stop()` (only as harness-unreachable fallback) and `harness.restart_agent()` *removes* it. The harness `POST /agents/{role}/stop` does NOT write `.stop` — it only flips intent. So today, an old `.stop` file present from a previous run silently overrides intent=running and prevents `boot_remote.boot_agent()` from re-spawning.
2. **`.stop-after-cycle`** — referenced only in *comments* now (`cycle_pre.py:676`, `cycle_post.py:550`). The actual mechanism was replaced by HTTP-query in `cycle_post._query_harness_intent()`. **The doc/comment debt remains** but no read/write code exists.
3. **`.restart` sentinel** — *write* in `cycle_post._do_restart_sentinel()` (gated by deprecated `restart_needed` field), *clean* in `boot_remote._clean_stale_restart()` and `start_team._clean_stale_sentinels()`. No script reads it for behavior — thin_launcher does not watch it (per `reboot_agent.py:127`). This is a vestigial sentinel; writes happen only if an agent emits the deprecated field.
4. **`.health` legacy fallback** — read by `harness.update_health()` and `health_check.check_agent_health()`. No script in the current tree *writes* `.health` (the old wrapper scripts that did are gone — thin_launcher replaced them). Reads are vestigial; they fire only for legacy wrapper-launched agents which no longer exist in this clone.

In addition there are two ancillary state files the harness owns: `.claude-pid` (written by `thin_launcher`, read by everyone for liveness) and `.booting` (boot-slot lock written/cleared by `boot_remote`). Neither is "split-brain" — both have a single writer — but the cleanup needs to decide whether to keep them as harness-internal artifacts or eliminate them.

**Operator entry-point picture today**:

| Tool | Talks to harness API? | Bypasses? |
|---|---|---|
| `squidsquad_cli.py` | Yes, for all ops | Only spawns the harness itself when not running |
| `start_team.py` | Yes (preferred), with `.stop` sentinel fallback when harness unreachable | Yes (`cmd_boot` bypasses API entirely and calls `boot_remote.boot_agent` directly) |
| `boot_remote.py --all/--role` | No — direct spawn, reads sentinels, writes `.booting` | Full bypass |
| `reboot_agent.py` | No — reads sentinels, calls `boot_remote` + kills PIDs | Full bypass |
| `harness.py` (internal) | Self-API not used; calls `boot_remote.boot_agent` and `reboot_agent._kill_process` directly | N/A (it *is* the harness) |
| `cycle_pre.py` | No lifecycle calls (only event emission) | N/A |
| `cycle_post.py` | Yes, queries `GET /agents/{role}` for intent | N/A |
| `health_check.py` | No — file-based liveness only | Full bypass (this is by design as a legacy fallback) |

The cleanup target is one in which **only the harness** writes any sentinel file (or none at all), **only the harness** spawns or kills processes, and **every operator tool** that needs to start/stop/restart goes through the HTTP API. `boot_remote.py` survives as a harness-internal helper. `reboot_agent.py` is either absorbed by the harness or becomes harness-internal.

---

## 1. Current Agent Lifecycle Code Paths — Complete Inventory

### 1.1 Process lifecycle operations

| Path (file:line) | Op | Goes through harness API? | Sentinel reads/writes |
|---|---|---|---|
| `harness.py:140-282` `HarnessState.update_health()` | Detect death + auto-reboot | N/A (is harness) | reads `.claude-pid` (line 148), reads `.stop` (line 239) |
| `harness.py:274` `boot_remote.boot_agent()` (auto-reboot) | Start (respawn) | N/A | calls `boot_remote.boot_agent` directly |
| `harness.py:705-721` lifespan auto-start | Start (all) | N/A | calls `boot_remote.boot_agent` directly |
| `harness.py:804-827` `POST /agents/all/start` | Start (all) | API target | calls `boot_remote.boot_agent` directly |
| `harness.py:830-865` `POST /agents/all/stop` | Stop (all) | API target | sets intent — does NOT write `.stop` |
| `harness.py:879-906` `POST /agents/{role}/start` | Start | API target | calls `boot_remote.boot_agent` directly |
| `harness.py:1259-1273` `POST /agents/{role}/stop` | Stop | API target | sets intent — does NOT write `.stop` |
| `harness.py:1276-1347` `POST /agents/{role}/restart` | Restart (idle-kill or queued) | API target | reads `.stop` (line 1295, removes it), calls `reboot_agent._read_claude_pid` + `_kill_process` for idle path |
| `harness.py:1350-1427` `POST /shutdown` | Stop all + exit | API target | reads `current-state` for idle wait, calls `reboot_agent._kill_process` for stragglers |
| `harness.py:1639-1683` `_reboot_affected_agents()` | Restart (post-compose) | N/A | sets intent=restarting |
| `harness.py:1889-1950` `CtrlCHandler` | Stop (all) | N/A | sets intent=stopping; force-exit does not kill agents |
| `boot_remote.py:181-184` `_has_stop_sentinel()` | Detect stop | N/A | **reads** `.stop` |
| `boot_remote.py:191-208` `_has_booting_sentinel()` | Detect concurrent boot | N/A | **reads** `.booting` (TTL 30s) |
| `boot_remote.py:211-233` `_write_booting_sentinel()` | Claim boot slot | N/A | **writes** `.booting` (atomic) |
| `boot_remote.py:236-242` `_clear_booting_sentinel()` | Release boot slot | N/A | **deletes** `.booting` |
| `boot_remote.py:245-257` `_clean_stale_restart()` | Cleanup stale | N/A | **deletes** `.restart` |
| `boot_remote.py:262-288` `_read_health_file()` | Detect liveness (legacy) | N/A | **reads** `.health` |
| `boot_remote.py:291-328` `_needs_boot()` | Pre-flight check | N/A | reads `.stop`, `.booting`, `.claude-pid`, `.pid` |
| `boot_remote.py:381-515` `_spawn_*()` | Start (process) | N/A | `subprocess.Popen` for terminal spawn |
| `boot_remote.py:522-578` `boot_agent()` | Start | N/A | reads via `_needs_boot`, writes/clears `.booting`, deletes `.restart`, spawns |
| `boot_remote.py:581-592` `boot_all()` | Start (all) | N/A | iterates `boot_agent` |
| `reboot_agent.py:50-56` `_kill_process()` | Kill | N/A | `taskkill /F` or `os.kill(pid, SIGINT)` |
| `reboot_agent.py:78-90` `_read_claude_pid()` | Read PID | N/A | reads `.claude-pid` |
| `reboot_agent.py:93-118` `_kill_and_respawn()` | Restart (force) | N/A | `_kill_process`, deletes `.pid`/`.claude-pid`, calls `boot_remote.boot_agent` |
| `reboot_agent.py:121-183` `reboot()` | Restart | N/A | **reads** `.stop` (line 134), reads `.pid`, `.claude-pid`, polls `current-state` for idle, kills + respawns |
| `health_check.py:253-467` `check_agent_health()` | Detect liveness | N/A | **reads** `.stop` (line 304), `.health` (line 329), `.claude-pid`, `.pid` |
| `thin_launcher.py:66-83` `_check_singleton()` | Prevent double-boot | N/A | reads `.claude-pid` |
| `thin_launcher.py:86-92` `_write_pid()` | Publish PID | N/A | **writes** `.claude-pid` (atomic) |
| `thin_launcher.py:95-101` `_clear_pid()` | Clear PID on exit | N/A | **deletes** `.claude-pid` |
| `thin_launcher.py:165-193` claude subprocess | Run agent | N/A | `subprocess.Popen("claude")`, waits for exit |
| `cycle_pre.py` | Nothing lifecycle-related | N/A | only mentions `.stop-after-cycle` in a comment (line 676) |
| `cycle_post.py:468-483` `_do_restart_sentinel()` (DEPRECATED) | Self-restart request | N/A | **writes** `.restart` (only if agent set `restart_needed`) |
| `cycle_post.py:486-515` `_discover_harness_port()` | Find harness | N/A | reads `.harness-port` |
| `cycle_post.py:518-536` `_query_harness_intent()` | Query intent | **YES** — `GET /agents/{role}` | replaces sentinel file check |
| `cycle_post.py:539-575` `_do_stop_after_cycle_check()` | Decide exit-42 | **YES** (calls `_query_harness_intent`) | reads `context-pressure` for fallback |
| `start_team.py:74-87` `_write_stop` / `_remove_stop` | Stop fallback / clear | N/A | **writes/deletes** `.stop` |
| `start_team.py:90-95` `_clean_stale_sentinels` | Cleanup | N/A | **deletes** `.restart` |
| `start_team.py:114-124` `cmd_boot()` | Start | NO — direct call to `boot_remote.boot_agent` | clears `.stop`, `.restart` |
| `start_team.py:127-166` `cmd_reboot()` | Restart | **YES** — `POST /agents/{role}/restart` (preferred) | falls back to direct kill+spawn via `boot_remote`+`reboot_agent` on `--force` |
| `start_team.py:169-179` `cmd_stop()` | Stop | **YES** — `POST /agents/{role}/stop` (preferred) | falls back to `_write_stop()` if harness unreachable |
| `squidsquad_cli.py:122-238` all commands | start / stop / restart / status / shutdown | **YES** for all ops (calls `_api_call`) | no sentinel reads/writes |

### 1.2 Subprocess / process-API call sites

Direct process operations (`subprocess.Popen`, `os.kill`, `signal.signal`, kill helpers):

| Site | Purpose |
|---|---|
| `harness.py:30, 1977-1991, 1442, 1461, 1498, 1508, 1656, 1818` | Various: `subprocess.run` for `tracker.py`/`compose.py`/git/gh; `signal.signal(SIGINT)` for Ctrl+C |
| `harness.py:1318-1322` | `reboot_agent._kill_process(claude_pid)` for `/restart` idle-path |
| `harness.py:1407` | `reboot_agent._kill_process(claude_pid)` for `/shutdown` stragglers |
| `harness.py:1423` | `os._exit(0)` after shutdown |
| `harness.py:1947, 1950` | `os._exit(1)` on 3rd Ctrl+C |
| `boot_remote.py:163-178` `_is_process_alive` | `tasklist` (Win), `os.kill(pid, 0)` (Unix) |
| `boot_remote.py:412, 434, 470, 502` `_spawn_*` | `subprocess.Popen` for terminal spawn (wt/cmd/osascript/tmux) |
| `reboot_agent.py:45-56` | `_is_process_alive` + `_kill_process` (taskkill/SIGINT) |
| `thin_launcher.py:55-63` | `tasklist` / `os.kill(pid, 0)` liveness check |
| `thin_launcher.py:165-169` | `subprocess.Popen([claude_exe, ...])` |
| `health_check.py:217-224` | `tasklist` / `os.kill(pid, 0)` liveness check |
| `squidsquad_cli.py:257-302` `_spawn_harness` | `subprocess.Popen` to launch harness in new terminal (only when harness not running) |
| `start_team.py:144-153` `cmd_reboot` `--force` | calls `reboot_agent._kill_process` |

### 1.3 Harness HTTP API call sites (clients)

| Site | Method/Path |
|---|---|
| `cycle_post._query_harness_intent` (`cycle_post.py:528`) | `GET /agents/{role}` |
| `event_bus.emit` (`event_bus.py:82`) | `POST /events` |
| `event_bus.ack` (via `emit`) | `POST /events` (event_type=ack) |
| `event_bus_reader` / `event_poll` | various event endpoints |
| `start_team._harness_api` (`start_team.py:60-66`) | `POST /agents/{role}/stop`, `POST /agents/{role}/restart` |
| `squidsquad_cli._api_call` | `POST /agents/all/start`, `POST /agents/all/stop`, `POST /agents/{role}/stop`, `POST /agents/{role}/restart`, `GET /status`, `POST /shutdown` |
| `diagnostics.py:136-173` | `POST /agents/all/start`, `POST /agents/{role}/stop`, `POST /agents/all/stop`, `POST /agents/{role}/restart` |

---

## 2. Sentinel File Semantics — What Each One Means Today

### 2.1 Path convention

All per-role sentinels live in **each agent's own clone** at `<clone_root>/.squidsquad/<role>/<name>`. With clone isolation (`.local-config`), the *primary* repo (`D:\Dev\Dev\SquidSquad`) holds only the harness + its own role state; each dev/QA/DM/PM agent clone is a separate path.

The harness-state files (`.harness-port`, `.harness-state.json`, `.event-state.json`) live in the primary repo's `.squidsquad/` (and `.harness-port` is also distributed to clone-local `.squidsquad/.harness-port` for client discovery — see `harness.py:678-690`).

### 2.2 Per-sentinel table

| File | Writers | Readers | Decision made on read | Disagreement risk |
|---|---|---|---|---|
| `.stop` | `start_team._write_stop` (harness-unreachable fallback only) | `boot_remote._has_stop_sentinel` (line 181), `boot_remote._needs_boot` (line 300), `harness.update_health` (line 239), `health_check.check_agent_health` (line 304), `reboot_agent.reboot` (line 134). Also **deleted** by `start_team._remove_stop`, `start_team.cmd_boot`, `harness.restart_agent` (line 1297). | Skip boot / mark stopped / refuse respawn / refuse reboot | **HIGH** — harness API `POST /stop` flips intent without writing `.stop`. If a stale `.stop` exists from a previous run, `_needs_boot` returns `False` and the agent never respawns; `harness.update_health` returns status=stopped; `reboot_agent.reboot` prints "explicitly stopped" and exits. The harness `/restart` deletes `.stop`, but `/start` does not — so a stale `.stop` silently breaks startup. This is the exact split-brain the rescope cites. |
| `.stop-after-cycle` | **No writer in current tree** (replaced by harness API intent). | **No reader in current tree** — only mentioned in comments at `cycle_pre.py:676` and `cycle_post.py:550`. | N/A (vestigial) | NONE today; doc debt only. The label `_do_stop_after_cycle_check` in `cycle_post.py:539` is kept as the function name but the body queries `GET /agents/{role}` instead. |
| `.health` | **No writer in current tree** (legacy wrapper scripts gone; thin_launcher writes `.claude-pid` instead). `health_check.py:230-250` and `boot_remote.py:262-288` still know how to *parse* both heartbeat-epoch and legacy `alive\|booting\|restarting\|backoff\|dead\|error\|...` formats. | `harness.update_health` (line 208, only when no `.claude-pid` and no stored PID), `health_check.check_agent_health` (line 329) | Mark agent healthy/stalled/stopped/error | NONE in practice because nothing writes it. **Doc/code debt**: 27 references across `boot_remote.py`/`health_check.py` for a feature that no longer has a producer. Even agent CLAUDE.md files still claim "PID monitoring (primary), `.health` file (legacy fallback)" (skill 1411, pm 1979, qa 1174, dm 1087). |
| `.restart` | `cycle_post._do_restart_sentinel` (line 480) — gated on deprecated `restart_needed` cycle-output field. | **No active reader.** `reboot_agent.py:127` explicitly notes "thin_launcher.py does not watch sentinel files." | N/A — vestigial in practice | NONE in behavior today, but the file is *deleted* by `boot_remote._clean_stale_restart` (line 252) and `start_team._clean_stale_sentinels` (line 94) to avoid feeding old wrappers. |
| `.booting` | `boot_remote._write_booting_sentinel` (line 211) — atomic write to claim boot slot. | `boot_remote._has_booting_sentinel` (line 191) — TTL 30s. | Skip boot ("another boot in progress") | NONE — single writer, single reader, both inside `boot_remote`. This is a harness-internal lock. |
| `.claude-pid` | `thin_launcher._write_pid` (line 89) — atomic. Cleared by `thin_launcher._clear_pid` on exit, `reboot_agent._kill_and_respawn` line 106. | `harness.update_health` (line 148), `boot_remote._needs_boot` (line 309), `boot_remote._is_process_alive` (transitively), `reboot_agent._read_claude_pid` (line 83), `health_check._read_claude_pid_file` (line 193), `thin_launcher._check_singleton` (line 73). | Detect liveness; refuse double-boot (#8692) | NONE — single writer (thin_launcher), well-defined contract. PID file is the *system of record* for liveness. |
| `.pid` (legacy) | **No writer in current tree** (the old PowerShell wrapper wrote it; gone). | `boot_remote._read_pid_file` (line 142), fallback in `_needs_boot` (line 321); `reboot_agent.py:141` reads `pid_file`; `health_check._read_pid_file` (line 175). | Liveness check (fallback) | NONE in practice — no producer; reads are vestigial. |
| `.harness-port` | `harness.py:664-689` (primary repo + distribute to all clone roots) | `event_bus._discover_port`, `cycle_post._discover_harness_port`, `start_team._discover_harness_port`, `squidsquad_cli._read_port`, `diagnostics.py:40`, `event_bus_reader`, `event_poll`. | Find the harness HTTP server | NONE — clearly owned by harness. |
| `.harness-state.json` | `harness.save_state` (line 305) | `harness.load_state` (line 336) for crash recovery | Restore intents on harness restart | NONE — single writer, single reader. |
| `.event-state.json` | `EventLifecycleManager._persist` (`harness.py:482`) | `EventLifecycleManager.load` (`harness.py:505`) | Restore event stream on harness restart | NONE — harness internal. |

### 2.3 The one split-brain that matters

Only **`.stop`** is genuinely split-brain today: it has multiple readers across multiple scripts and is **not** written by the harness API stop endpoint. If anyone (operator, leftover state, a `start_team --stop` issued while the harness was down) writes `.stop`, all the readers will silently refuse to operate on that agent. The harness can flip intent to `running` and call `boot_remote.boot_agent` — `_needs_boot` will return `False` because of `.stop`, and the auto-reboot never happens.

The other "sentinels" are doc/code debt: parsers/writers for files nothing else produces or consumes. They should be removed but their continued presence is not actively breaking anything.

---

## 3. Harness HTTP API Surface

Authoritative source: `harness.py`.

### 3.1 Endpoints

| Endpoint | File:line | Behavior |
|---|---|---|
| `GET /status` | 781-794 | Calls `update_health()` then returns `{harness: {...}, agents: [...]}`. |
| `GET /agents` | 797-801 | Same as `/status` minus the harness block. |
| `GET /agents/{role}` | 868-876 | `_validate_role`, `update_health`, returns `AgentState.to_dict()` (includes `intent`). This is what `cycle_post._query_harness_intent` reads. |
| `POST /agents/all/start` | 804-827 | Iterate roles → call `boot_remote.boot_agent(role)`. Set in-memory status=starting, intent=running, boot_time, terminal_pid. Persist. |
| `POST /agents/all/stop` | 830-865 | Iterate roles → check intent/`_needs_boot` → flip intent to STOPPING. No `.stop` write, no process kill. |
| `POST /agents/{role}/start` | 879-906 | Skip if already running. Else call `boot_remote.boot_agent(role)`. |
| `POST /agents/{role}/stop` | 1259-1273 | Set intent=stopping in memory, save state. No process kill, no sentinel write. cycle_post observes via `GET /agents/{role}` next cycle boundary. |
| `POST /agents/{role}/restart` | 1276-1347 | Set intent=restarting. **Delete `.stop` sentinel** (1297). If `current-state` starts with `idle` and `.claude-pid` is alive → call `reboot_agent._kill_process(claude_pid)` for immediate respawn (#8689). Else queued — agent exits at cycle end and auto-reboots. |
| `POST /shutdown` | 1350-1427 | Background thread: set intent=stopping on all running roles; wait up to 30s for `current-state` to start with `idle`; kill any remaining alive `claude-pid`s via `reboot_agent._kill_process`; unlink `.harness-port`; `os._exit(0)`. |
| `GET /agents/{role}/health` | 909-943 | Returns role/alive/status/last_cycle/current_phase/context_pressure (reads `current-state` and `context-pressure` files from local `.squidsquad/<role>/`). |
| `GET /agents/{role}/config` | 946-963 | Returns the agent's view of selected config.md fields. |
| `POST /events` | 1048-1089 | Event ingress (event bus). Side effect: `event_type==ack` with `result==stop-confirmed` flips intent=STOPPING (line 1080). |
| `GET /events`, `GET /events/for/{role}`, `POST /events/{id}/complete`, `GET /events/in-flight/{role}`, `GET /events/lifecycle` | 1092-1256 | Event-bus surface (#7630). Not lifecycle, but the `complete` and `ack` paths can flip agent intent (1080). |
| `POST /merge` | 1528-1636 | Async PR merge + compose + selective agent reboot via `_reboot_affected_agents`. |

### 3.2 Endpoints that write sentinel files

Exactly one: `POST /agents/{role}/restart` deletes the `.stop` sentinel at line 1297 (`stop_file.unlink(missing_ok=True)`). This is a workaround for the split-brain — without it, an old `.stop` would block re-spawn. It's a *clean* operation, not a write of intent.

No endpoint writes `.stop`, `.stop-after-cycle`, `.restart`, or `.health`. Internal harness state is `intent` in memory + `.harness-state.json`.

### 3.3 The boot path inside the harness

When the harness needs to spawn an agent (lifespan auto-start, `/agents/{role}/start`, `/agents/all/start`, or auto-reboot from `update_health`), it ultimately calls:

```
boot_remote.boot_agent(role)
  → boot_remote._needs_boot(role)
      → reads .stop, .booting, .claude-pid, .pid
  → boot_remote._write_booting_sentinel(...)
  → boot_remote._clean_stale_restart(...)
  → boot_remote._find_boot_script(...)
  → boot_remote._spawn_terminal(...)
      → subprocess.Popen([wt|cmd|osascript|tmux ...] python thin_launcher.py <role>)
  → thin_launcher writes .claude-pid, runs claude, clears .claude-pid on exit
```

So even the harness API uses `boot_remote` as the spawn engine. The two are tightly coupled. `boot_remote` is currently both a CLI (with its own `main()` accepting `--all`, `--role`, `--dry-run`, `--json`) **and** a library imported by harness. The CLI surface is the "parallel control path" the rescope wants to eliminate.

### 3.4 The stop path inside the harness

`POST /agents/{role}/stop` does **only** `state.set_agent → save_state`. It relies on `cycle_post._do_stop_after_cycle_check` to query `GET /agents/{role}` at the next cycle boundary and exit code 42 to actually terminate the agent. There is no immediate kill — the design is "wait for the agent to finish its cycle and exit cleanly." This is fine for `pending → stopping` graceful flow.

`POST /shutdown` is the *real* hard stop: flips intent, waits 30s for `idle`, then kills `.claude-pid` via `reboot_agent._kill_process`.

The Ctrl+C handler in `CtrlCHandler` (1889-1950) is yet another stop entry-point: it raises `KeyboardInterrupt` to drive `uvicorn` shutdown, but does *not* kill agents — agents survive in their terminals.

### 3.5 The restart path inside the harness

Two modes coexist (#8689 added the idle-path):

- **Idle path** (current-state startswith "idle" AND `.claude-pid` is alive): intent=restarting, kill claude process, let `update_health`'s auto-reboot fire within `HEALTH_POLL_INTERVAL=5s`.
- **Queued path** (mid-cycle, no claude-pid, or kill failed): intent=restarting only; cycle_post queries intent at cycle end, exits 42, harness auto-reboots.

The auto-reboot logic in `update_health` (224-258) reads:
```
if is_dead and was_alive and intent in (RUNNING, RESTARTING):
    reboot_roles.append(role)
```
This is the central point where the harness decides to respawn. Note that `was_alive == True` is required — if the agent was already `starting` or `stalled` when it died, it won't be auto-rebooted. This is suspicious and may be related to the on-hold #7693 bug.

### 3.6 Note on `was_alive` gate (potential #7693 root cause)

`harness.py:248` requires `prev_status == "running"` for auto-reboot. After a `cycle_post` exit 42 in a thin-launcher session:

1. `claude` exits with code 42.
2. `thin_launcher` clears `.claude-pid` and exits.
3. The terminal window remains open (depending on terminal type) but `claude_pid` in `AgentState` still points at the old PID.
4. Next `update_health` poll: `_is_process_alive(old_pid)` → False, `_read_claude_pid` → file is gone → `alive=False`.
5. Status transition: was `running` (assuming prior poll saw it alive) → now dead → fires reboot.

This *should* work. Need to verify whether the on-hold #7693 case is:
- (a) `claude` exits 42 but the terminal window keeps running thin_launcher (i.e., thin_launcher does not propagate exit) — no, `thin_launcher.py:180` does `proc.wait()` then returns the exit code, and the script itself exits.
- (b) The harness was not running, so no auto-reboot. (Possible in interactive sessions where PM ran without a harness.)
- (c) `prev_status` was not "running" when `update_health` saw the dead PID — e.g., status was already `starting` or `unknown` because the agent died too fast for a single poll cycle to record `running`.
- (d) The harness was up but `update_health` never ran while agent was alive — would require an extremely tight death window. Unlikely.

Phase 2 should ask: is the on-hold #7693 actually still broken now that #4966 + #8689 have shipped, or is it now subsumed?

---

## 4. Wrapper Script Behavior

### 4.1 `boot_remote.py`

**Today's calling sites**:

- `harness.py` lifespan auto-start (`harness.py:707-721`)
- `harness.py:274` auto-reboot inside `HarnessState.update_health`
- `harness.py:812, 893` POST start endpoints
- `harness.py:849, 1370` (via `_needs_boot`) for the stop endpoints
- `reboot_agent._spawn_wrapper` (line 74) calls `boot_remote.boot_agent`
- `start_team.cmd_boot` (line 120) calls `boot_remote.boot_agent` **bypassing harness API**
- `start_team.cmd_reboot` line 136 fallback when agent not running
- Direct CLI `python boot_remote.py --all` (still supported per docstring and `main()`)

**Function**: pre-flight check (`_needs_boot`), boot lock (`.booting`), find boot script (prefers thin_launcher), spawn terminal.

**Recommendation**: keep as **harness-internal library**. Remove the `main()` CLI entry-point and the `--all`/`--role`/`--dry-run`/`--json` flags so it cannot be invoked as an operator tool. All operator-facing boot goes through harness API. Document as `# Internal — invoked by harness only`.

### 4.2 `reboot_agent.py`

**Today's calling sites**:

- `harness.py:1316, 1320, 1404, 1407` (uses `_read_claude_pid` and `_kill_process`)
- `start_team.py:144-153` `cmd_reboot --force` (calls `_kill_process`, then `boot_remote.boot_agent`)
- Direct CLI `python reboot_agent.py <role>` or `--all`

**Function**: kill claude PID (immediately or after waiting for `idle`), then call `boot_remote.boot_agent` to respawn. Reads `.stop` and refuses to respawn stopped agents.

**Recommendation**: this script has two distinct uses:
1. As a **library** providing `_read_claude_pid`, `_kill_process`, `_is_process_alive` — used by `harness.py` and `start_team.py --force`.
2. As an **operator CLI** for safe reboot.

Both functions are now superseded by `POST /agents/{role}/restart` (queued or idle-path #8689). The CLI is redundant. The library helpers (`_kill_process`, `_read_claude_pid`) should move *into* `harness.py` (or a shared `process_ops.py` helper) so the harness doesn't depend on a CLI tool.

Removing the operator CLI eliminates one parallel control path. The reading of `.stop` (`reboot_agent.py:134`) goes away with the sentinel.

### 4.3 `start_team.py`

**Today's calling sites**:

- Operator runs directly (`python references/scripts/start_team.py --all` / `--role` / `--stop` / `--reboot`)
- Documented in every role's CLAUDE.md `agent-lifecycle` sub-skill
- Documented as the canonical operator entry-point (`references/sub-skills/common/agent-lifecycle.md`)

**Function**: dispatcher.
- `--all` / `--role` boot → bypasses harness, calls `boot_remote.boot_agent` directly
- `--reboot` → calls `POST /agents/{role}/restart`, falls back to direct kill+spawn on `--force`
- `--stop` → calls `POST /agents/{role}/stop`, falls back to **writing `.stop` sentinel** when harness unreachable

**Recommendation**: convert to **thin client of harness API**, like `squidsquad_cli.py`. The fallback `.stop` write is precisely the split-brain we are removing. Boot operations must also go through `POST /agents/all/start` (which already exists) rather than bypassing into `boot_remote`.

`squidsquad_cli.py` already does most of this correctly — it always uses the API, never writes sentinels. The simplest endpoint convergence is: deprecate `start_team.py` in favor of `squidsquad_cli.py` (renamed to `squidsquad` or similar), or rewrite `start_team.py` to be `squidsquad_cli.py` semantics under the existing flag surface. Either way, the operator entry-point is one client.

---

## 5. cycle_pre / cycle_post Lifecycle Interactions

### 5.1 `cycle_pre.py`

- Reads `boot_results` from `cycle-input.json` (PM-only `_build_pm_input` line 678) — **always empty** today, kept "for backward compat until all agents redeployed" (line 677).
- No sentinel reads or writes.
- No harness PID check.
- Does not query the harness for lifecycle state.
- Only mentions `.stop-after-cycle` in a stale comment (line 676).

**No lifecycle behavior in cycle_pre today.** That makes it the *least* affected by the cleanup — but it also means cycle_pre is **not** the place where an agent confirms the harness is alive at start-of-cycle. Phase 2 question: should cycle_pre check harness PID before doing any work, and exit cleanly if dead? This is mentioned in the issue body ("Wrapper scripts check harness PID before each task/cycle; dead PID = exit cleanly").

### 5.2 `cycle_post.py`

- `_query_harness_intent` (518-536): `GET /agents/{role}` over HTTP, returns `intent`. 5s timeout. Fail-open (returns None → continue running).
- `_do_stop_after_cycle_check` (539-575): if intent ∈ {stopping, restarting} → exit 42; else if `context_pressure.exceeded` → exit 42.
- `_do_restart_sentinel` (468-483): **DEPRECATED** — writes `.restart` only if agent set `restart_needed` in cycle-output (which no current agent template instructs). Comment says "kept for one version of backward compatibility only."
- Exit code 42 signals respawn to harness — caught by `update_health` auto-reboot (was_alive + intent in {running, restarting}).

**Stop after cycle is signaled via HTTP GET, not a file.** This is the clean path. The legacy `.stop-after-cycle` file is gone.

### 5.3 Context-pressure exit 42 → respawn

Full path:
1. Statusline hook writes `.squidsquad/<role>/context-pressure` after each assistant message.
2. `cycle_pre._read_context_pressure` reads it into `cycle-input.json` → `context_pressure: {used_pct, threshold, exceeded}`.
3. Agent's creative phase: if exceeded, checkpoint working-state.md and continue (Claude Code auto-compresses).
4. `cycle_post._do_stop_after_cycle_check` reads `context_pressure.exceeded` from output (or input as fallback). If true, returns True → main returns 42.
5. `thin_launcher.proc.wait()` returns 42 → `thin_launcher` clears `.claude-pid`, prints "claude exited with code 42", returns 42.
6. `update_health` poll within 5s sees dead PID + intent=running → adds role to `reboot_roles` → calls `boot_remote.boot_agent` → respawns claude in a new (or existing) terminal window.

**Potential failure points** (re #7693):

- (a) If `prev_status` wasn't "running" at the moment of death, the gate `was_alive = prev_status == "running"` fails and no reboot fires. This is the most likely cause of "claude session keeps running" — but it requires the bug reporter's claude session to be the one *not* spawned by thin_launcher. The #7693 report describes "the Claude Code session continues running normally — does NOT restart," which suggests the claude process did NOT exit. That implies `cycle_post` returned 42, the thin_launcher proc.wait() picked it up, but the *parent claude session* kept running.

  Wait — `cycle_post.py` is invoked from inside the agent's session as a tool call. Returning 42 from `cycle_post` does NOT terminate the parent claude session by itself. The Ralph-loop instructions in CLAUDE.md document this as "the harness detects the exit, sees intent=running, and respawns" — but the agent's session is not the same process as `cycle_post.py`. The exit code 42 only matters if a *wrapper* is checking it. **For thin_launcher to see exit 42, claude itself must exit 42.** This is the disconnect:

  - In the (gone) legacy wrapper model, the wrapper invoked claude, claude exited (somehow), wrapper saw the exit code, respawned.
  - In the thin_launcher model, claude is a long-running interactive process. cycle_post is a tool call inside that claude. Exiting `cycle_post.py` with code 42 produces a `42` exit code visible to the bash tool, but does not terminate claude itself.

  So **the harness will never see the agent die unless something kills claude**. This appears to be the #7693 root cause: the documented self-restart mechanism is non-functional outside the legacy wrapper. Phase 2 needs to confirm and decide the new mechanism — likely the agent must explicitly call `POST /agents/{role}/restart` (or set `restart_needed`) and the *harness* kills the claude PID and respawns. Or `cycle_post.py` itself calls `reboot_agent._kill_process(claude_pid_from_thin_launcher)` after detecting exceeded pressure, which would surface as "agent kills self via PID."

  This is significant for #4792 because the "sole-authority" principle says **the harness kills, not the agent**. So the agent emits a request (event or HTTP) and the harness performs the kill. That's a meaningful design decision for Phase 2.

- (b) Harness unreachable when `_query_harness_intent` runs: returns None → "safe default, continue running." No respawn happens regardless. This is *intentional* but means a harness restart during a cycle could miss a stop request.

### 5.4 cycle_pre / cycle_post writes that the cleanup affects

| Write | File | Concern |
|---|---|---|
| `_do_restart_sentinel` | `.restart` | DEPRECATED, safe to remove |
| `_write_status_bar` | `current-state` | Not a sentinel — status display only |
| `_advance_event_cursor` | `working-state.md` | Not a sentinel — agent's own state |
| `_do_working_state_update` | `working-state.md` | Not a sentinel — agent's own state |

---

## 6. start_team.py Operator Entry Point

Today's surface:
- `--all` boot
- `--role <name>` boot
- `--reboot <name>` (graceful via API, `--force` for immediate kill)
- `--reboot --all`
- `--stop <name>` (graceful via API, `.stop` fallback if harness unreachable)
- `--stop --all`

`cmd_boot` is the **only** command that always bypasses the harness API. It calls `boot_remote.boot_agent(role)` directly and writes nothing. Conceptually it should call `POST /agents/{role}/start` or `POST /agents/all/start`.

`cmd_reboot` and `cmd_stop` prefer the API and only fall back to file writes when the harness is down — and the file write is exactly the split-brain.

The agent CLAUDE.md `agent-lifecycle` sub-skill (`references/sub-skills/common/agent-lifecycle.md`) documents only `start_team.py` for operators. `squidsquad_cli.py` is the cleaner thin client but it's not documented as the canonical interface. Phase 2 question: pick one canonical operator entry-point.

---

## 7. Inter-script Signal Flow — Graceful Stop

Target: "operator wants skill to stop gracefully at next cycle boundary."

### 7.1 Path through `start_team.py` (today)

```
operator: python references/scripts/start_team.py --stop skill
  start_team.cmd_stop(["skill"])
    _harness_api("POST", "/agents/skill/stop")
      → harness.stop_agent(role="skill")
          state.get_agent("skill").intent = STOPPING
          state.save_state()
      → response 200
  ...
  (next cycle boundary, ~30 min later)
  agent runs cycle_post.py
    _do_stop_after_cycle_check(data, role)
      _query_harness_intent("skill")  →  GET /agents/skill  →  intent="stopping"
      returns True
    cycle_post.main → returns 42
  ⚠  exit 42 is not propagated to claude itself (see §5.3) — the agent does not actually die
```

If `_harness_api` fails (harness down) → `_write_stop("skill")` writes `.stop` in **the primary repo** `.squidsquad/skill/.stop`, **not** in the agent's clone (because `start_team.py` resolves paths from primary repo's `SQUIDSQUAD_DIR`, line 32). The agent's clone path is *different* — see `boot_remote._get_clone_path("skill")`. So the `.stop` file is **written to the wrong directory** in clone-isolated setups. This is a secondary bug to surface.

### 7.2 Path through `squidsquad_cli.py`

```
operator: python references/scripts/squidsquad_cli.py stop skill
  cmd_stop("skill")
    _api_call(port, "POST", "/agents/skill/stop")  →  intent=STOPPING
  (rest identical)
```

No fallback path; if harness is down, it errors out cleanly.

### 7.3 Path through harness Ctrl+C (graceful, 1st press)

```
operator: Ctrl+C in harness terminal
  CtrlCHandler._graceful_stop
    for role in all_roles:
      if status=="running": intent=STOPPING
    state.save_state()
    raise KeyboardInterrupt  →  uvicorn graceful shutdown
  (cycle_post observes via API as above)
```

Sentinel-file involvement in graceful-stop today: **only the fallback** in `start_team.cmd_stop`. Removing that and pointing start_team at squidsquad_cli semantics eliminates the last writer.

### 7.4 Re §5.3 unresolved question

For graceful-stop to actually kill the agent, the harness must observe the exit. Today, only the `claude` process exit drives that. If `cycle_post.py` exiting 42 does not kill `claude` (it doesn't — see §5.3), then no actual stop occurs. The intent stays at STOPPING forever and the agent keeps running.

Phase 2 must lock how graceful stop *really* kills the claude process. Options:
- (a) `cycle_post.py` itself kills the claude PID before exiting (agent self-kill).
- (b) `cycle_post.py` POSTs a `stop-confirmed` ack to `POST /events`, harness kills the claude PID.
- (c) Harness's `update_health` poller actively kills claude PIDs whose intent is STOPPING+last_cycle_end is recent (e.g., agent just finished a cycle but didn't exit).
- (d) Make the agent's claude session itself periodically poll harness and self-exit via `/quit` slash command or equivalent.

(c) is the "sole-authority" answer.

---

## 8. Inter-script Signal Flow — Hard Stop / Kill

Target: "kill skill now."

### 8.1 Path through `squidsquad_cli.py shutdown` (whole team)

```
operator: python references/scripts/squidsquad_cli.py shutdown
  cmd_shutdown
    _api_call(port, "POST", "/shutdown")
      harness.shutdown()  (background thread)
        for role: flip intent=STOPPING
        wait up to 30s for current-state startswith "idle"
        for role with alive .claude-pid:
          reboot_agent._kill_process(pid)
        unlink .harness-port
        os._exit(0)
```

No sentinels involved. Harness owns the kill.

### 8.2 Path through `start_team.py --reboot --force <role>`

```
operator: python references/scripts/start_team.py --reboot --force skill
  start_team.cmd_reboot(["skill"], force=True)
    boot_remote._needs_boot("skill")  →  alive
    reboot_agent._read_claude_pid(clone_path, "skill")  →  (pid, alive)
    reboot_agent._kill_process(pid)            ← BYPASSES HARNESS
    time.sleep(2)
    boot_remote.boot_agent("skill")           ← BYPASSES HARNESS
```

Two bypasses. Should both go through the harness:
- Kill → `POST /agents/{role}/restart` with `force=true` query (need a new flag — today the endpoint does idle-kill only).
- Respawn → harness auto-reboot from observed dead PID.

### 8.3 Path through `reboot_agent.py` (CLI)

```
operator: python references/scripts/reboot_agent.py skill --force
  reboot("skill", force=True)
    reads .stop  → if present, refuse                    ← SENTINEL READ
    reads .pid  → launcher_pid
    reads .claude-pid  → claude_pid
    _kill_process(claude_pid)
    deletes .pid, .claude-pid
    boot_remote.boot_agent(role)
```

Several sentinel reads/writes here. Fully bypasses harness. Should be removed entirely or rewritten as a harness API thin client.

---

## 9. Restart and Respawn

### 9.1 Exit-42 → respawn (working path, harness running, prev_status=running)

```
cycle_post.py main returns 42
  thin_launcher: proc.wait()  →  42
  thin_launcher._clear_pid()       (deletes .claude-pid)
  thin_launcher process exits
  ⚠  parent claude process must already be dead for this to fire (see §5.3 caveat)

5 seconds later: harness HEALTH_POLL_INTERVAL elapses
  update_health()
    role: prev_status="running"
    claude_pid stored → _is_process_alive(pid) → False
    fallback: _read_claude_pid file → file gone → file_alive=False
    fallback .health → not present → still dead
    intent = RUNNING
    is_dead=True, was_alive=True, should_reboot=True
    reboot_roles.append(role)
  outside lock:
    boot_remote.boot_agent(role)
      _needs_boot: .stop check, .booting check, .claude-pid check, .pid check → True (no .stop, .claude-pid gone, .pid gone)
      _write_booting_sentinel
      _spawn_terminal → wt/cmd/osascript/tmux → thin_launcher → claude
    state.save_state()
```

### 9.2 Where it can fail (#7693)

Per §5.3 the most likely failure is that the **parent claude process never exits** when `cycle_post.py` returns 42. cycle_post.py is a bash subprocess inside claude's tool execution; its exit code does not propagate. Only if the agent's CLAUDE.md instructs it to *also* quit the session (or to invoke `/quit`) after a 42 exit would claude actually die.

Reading `.squidsquad/pm/CLAUDE.md:#### Self-Restart (Context Pressure Only)`:
> 5. The harness detects the exit, sees intent=running, and respawns the agent.

It assumes claude exits. But claude is the *parent*. So the docs are aspirational w.r.t. the current architecture. This is the audit gap to flag for Phase 2.

Other failure modes:
- Harness was not running when `cycle_post` returned 42 → `_query_harness_intent` returns None → exit 0 anyway → no restart.
- thin_launcher was bypassed (operator launched claude manually) → no `.claude-pid` written → harness doesn't know agent exists → no auto-reboot.
- Status was never `running` (agent died before first health poll observed it as such) → was_alive=False → no auto-reboot. Possible but tight window.

### 9.3 Where it can fail (#8689 — now fixed)

The shipped fix in `POST /agents/{role}/restart` (#8689) handles idle agents: kill PID immediately, harness auto-reboot picks it up. Tested and verified per the issue's QA comment. Mid-cycle agents still rely on cycle_post → exit 42 → §9.2 chain, which has the #7693 problem.

---

## 10. Related Bugs and Their Interaction

### 10.1 #8689 — restart endpoint latency on idle (SHIPPED)

Implemented: `POST /agents/{role}/restart` now reads `current-state`; if it startswith "idle" and `.claude-pid` is alive, kills the process immediately. Auto-reboot then fires within `HEALTH_POLL_INTERVAL` (5s). Response includes `immediate: bool` and `killed_pid` so operators see the path taken.

**Interaction with #4792**: this code path uses `reboot_agent._read_claude_pid` and `reboot_agent._kill_process` from inside the harness (line 1316, 1320). These should be absorbed into harness internals as part of the cleanup. It also still deletes `.stop` (line 1297) which becomes a no-op once the `.stop` sentinel is fully removed.

### 10.2 #7693 — context-pressure restart not respawning (ON HOLD)

Per the audit in §5.3 and §9.2: the documented self-restart mechanism is broken because `cycle_post.py` exit 42 does not kill the parent claude process. The fix probably requires *one* of:
- cycle_post explicitly kills the agent's own claude PID (read from .claude-pid) before exiting → simple but breaks "harness sole authority"
- cycle_post POSTs a stop-confirmed ack → harness kills the agent
- agent's CLAUDE.md instructs claude to issue `/quit` after detecting context pressure

This bug is on-hold because #7630 (event-driven) was assumed to replace the mechanism. With #4792 establishing sole-authority, the proper fix is the harness-kills option. **Phase 2 of #4792 should resolve #7693 by design.**

### 10.3 #4221 — original harness epic (CONTEXT)

The original harness epic was the umbrella for the lifecycle work. #4966 shipped the FastAPI harness, `.claude-pid` mechanism, intent state machine, and crash recovery. **Sentinel-file removal was always intended but not shipped** because the harness work was time-boxed to the API surface plus thin-launcher integration. The sentinel removal (#4792) is the remaining audit-cleanup of that epic.

### 10.4 #8692 — singleton enforcement (SHIPPED, hard prereq partner)

Added `_check_singleton` to `thin_launcher.py` (lines 66-83): reads `.claude-pid`, checks liveness, refuses boot if alive (exit 3) unless `--force`. The harness path via `boot_remote._needs_boot` already gated this; #8692 closes the hole for manual invocations.

**Interaction with #4792**: the singleton check uses `.claude-pid` as the authoritative liveness signal. This is correct and stable — `.claude-pid` is NOT a sentinel in the split-brain sense; it's a single-writer state file. The cleanup should preserve `.claude-pid` as-is.

---

## 11. The 7 Scripts Inventory — Annotated

### 11.1 `harness.py` (2011 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | `.stop` (line 239 in update_health), `.stop` (1295 in /restart, removes if present), `.claude-pid` (148 in _read_claude_pid), `.harness-port` (664-689 distribute), `.harness-state.json` (336 load), `.health` (via health_check fallback, line 208) |
| Sentinel writes | `.harness-port` (664-689), `.harness-state.json` (305 save), `.event-state.json` (482 EventLifecycleManager). **Deletes** `.stop` (1297 in /restart). |
| subprocess calls | uvicorn (1991), `_emit_event` git/gh helpers (1492, 1508, 1818), tracker.py (1442, 1461), compose.py (1600), `reboot_agent._kill_process` (1320, 1407) |
| `os.kill`/`signal` | `os._exit` (1423, 1947, 1950), `signal.signal(SIGINT, ctrl_c.handle)` (1977) |
| Harness API calls | None — it is the API |
| Recommendation | **Refactor**: (a) absorb `reboot_agent._kill_process`/`_read_claude_pid` into harness internals or shared `process_ops.py`; (b) eliminate `.stop` read at 239 and `.stop` cleanup at 1295 once sentinel is gone; (c) remove `.health` fallback in update_health (208) — no producers; (d) maintain `.harness-state.json`, `.harness-port`, `.event-state.json` as harness-owned state. |

### 11.2 `boot_remote.py` (647 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | `.pid` (146), `.stop` (183, 300), `.booting` (197, 222), `.health` (271), `.restart` (252), `.claude-pid` (309) |
| Sentinel writes | `.booting` (211 atomic write); **deletes** `.booting` (238), `.restart` (252) |
| subprocess calls | `tasklist`/`os.kill` for `_is_process_alive` (170-178); `subprocess.Popen` for terminal spawn × 4 (412, 434, 470, 502); `subprocess.run` for tmux session kill (492) |
| `os.kill`/`signal` | `os.kill(pid, 0)` for Unix liveness (175) |
| Harness API calls | None |
| Recommendation | **Refactor + de-CLI**: (a) remove `_has_stop_sentinel` (181-184) and the `.stop` check in `_needs_boot` (299-302); (b) remove `_read_health_file` (262-288) — dead code; (c) remove `_read_pid_file` (141-160) and `.pid` fallback in `_needs_boot` (320-326) — legacy; (d) remove `_clean_stale_restart` (245-257) once `.restart` is gone; (e) keep `.booting` lock as harness-internal boot serialization (single writer/reader inside boot_remote); (f) keep `.claude-pid` handling unchanged — that's the auth signal; (g) **remove `main()` and CLI flags** — no longer an operator entry-point. |

### 11.3 `reboot_agent.py` (218 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | `.stop` (134), `.pid` (141), `.claude-pid` (83 via `_read_claude_pid`) |
| Sentinel writes | **Deletes** `.pid` and `.claude-pid` (105-110, after kill) |
| subprocess calls | `taskkill /F /PID` (53), `_is_process_alive` via boot_remote (47) |
| `os.kill`/`signal` | `os.kill(pid, signal.SIGINT)` (56) |
| Harness API calls | None |
| Recommendation | **Remove or absorb**: the operator CLI is fully redundant with `POST /agents/{role}/restart`. The library helpers (`_kill_process`, `_read_claude_pid`, `_kill_and_respawn`) are used by harness — move them into harness internals or a shared `process_ops.py`. Then delete `reboot_agent.py`. The `.stop` check at line 134 vanishes with the sentinel. |

### 11.4 `health_check.py` (586 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | `.stop` (304), `.health` (329), `.claude-pid` (193), `.pid` (177) |
| Sentinel writes | None |
| subprocess calls | `tasklist` for Win liveness (217) |
| `os.kill`/`signal` | `os.kill(pid, 0)` (223) |
| Harness API calls | None — file-based |
| Recommendation | **Remove or thin-out**: the script's docstring already says (line 4) "DEPRECATION NOTE (#4966): The harness now monitors agent liveness via direct PID checks." It survives as the legacy fallback inside `harness.update_health` (208-219). Once `.health` is gone (no producer today) and the harness owns liveness, this script's purpose collapses to "human-facing diagnostic." Phase 2 question: keep as a read-only thin client of `GET /status` (zero file access), or delete entirely (the CLI is now `squidsquad_cli.py status`)? Either way, all `.stop` / `.health` / `.pid` reads go. |

### 11.5 `cycle_pre.py` (1071 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | None |
| Sentinel writes | None (writes only `cycle-input.json`, status bar, working state) |
| subprocess calls | many — `tracker.py`, `triage.py`, `config.py`, `health_check.py --json` (PM/QA), `git_ops.py`, `git`, `gh` |
| `os.kill`/`signal` | None |
| Harness API calls | None (only event_bus.emit indirectly via `event_bus_reader` for queries) |
| Recommendation | **Keep**, but: (a) remove the stale `.stop-after-cycle` comment at line 676; (b) remove the empty `boot_results` list and the PM-only field once `cycle_pre` is no longer expected to surface boot results; (c) Phase 2 question: should cycle_pre check harness PID at start-of-cycle and exit cleanly if dead? The issue body says yes. Today it doesn't. |

### 11.6 `cycle_post.py` (747 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | None |
| Sentinel writes | `.restart` (480, DEPRECATED, only on `restart_needed`) |
| subprocess calls | many — tracker.py, git_ops.py, config.py, cycle.py, git, gh |
| `os.kill`/`signal` | None |
| Harness API calls | `GET /agents/{role}` (528 `_query_harness_intent`) |
| Recommendation | **Refactor**: (a) delete `_do_restart_sentinel` (468-483); (b) rename `_do_stop_after_cycle_check` to e.g. `_check_harness_intent` to reflect that it queries the API; (c) the comment at line 550 ("replaces .stop-after-cycle file check") can stay as a historical note in a CHANGELOG but remove from active code; (d) **address #7693**: decide whether cycle_post should kill the agent's claude PID, or POST a stop-confirmed ack, when intent==stopping/restarting OR context_pressure exceeded. Phase 2. |

### 11.7 `start_team.py` (249 lines)

| Aspect | Findings |
|---|---|
| Sentinel reads | `current-state` for idle check (100-107) |
| Sentinel writes | `.stop` (74-80 `_write_stop`); **deletes** `.stop` (83-87 `_remove_stop`), `.restart` (90-95) |
| subprocess calls | None directly (relies on imports of boot_remote and reboot_agent) |
| `os.kill`/`signal` | Via reboot_agent (144-153 in cmd_reboot --force) |
| Harness API calls | `POST /agents/{role}/restart` (160), `POST /agents/{role}/stop` (173) |
| Recommendation | **Rewrite as thin API client** or **delete in favor of squidsquad_cli.py**: (a) `cmd_boot` must call `POST /agents/{role}/start` instead of `boot_remote.boot_agent`; (b) `cmd_stop` must drop the `.stop` fallback; (c) `cmd_reboot --force` must call a new harness endpoint (`POST /agents/{role}/restart?force=1`) rather than killing directly; (d) `_clean_stale_sentinels`, `_write_stop`, `_remove_stop` all deleted. End state: identical surface to `squidsquad_cli.py` semantics. |

---

## 12. Risks the Cleanup Introduces

Each row is a removal we plan; the column "Could break" lists every downstream reader/writer that depends on the removed pair. If any reader stays after the writer is removed, the reader silently always-true or always-false: silent breakage class.

| Removal | What it depends on / impacts | Could break |
|---|---|---|
| Remove `.stop` writes in `start_team._write_stop` | No reader update needed if all readers also removed simultaneously. If only the writer is removed, every existing `.stop` file becomes permanent (no way for operator to clear without removing readers too). | `boot_remote._needs_boot` (300) will keep refusing to boot any role with a leftover `.stop`. `harness.update_health` (239) will report stopped forever. `reboot_agent.reboot` (134) refuses respawn. `health_check.check_agent_health` (304) reports STOPPED. **Mitigation**: a one-shot cleanup task in compose.py or harness lifespan that deletes any leftover `.stop` files at upgrade. |
| Remove `.stop` reads | Operators using `start_team --stop` *before harness ships* lose graceful-stop fallback when harness is down. | Edge case — only matters when harness is unreachable. The acceptable behavior is "errors out, cannot stop." Document. |
| Remove `.restart` writes (`cycle_post._do_restart_sentinel`) | Removes the deprecated agent-emitted restart request. | No active reader exists today (thin_launcher doesn't watch it). Safe. Confirm no agent template still instructs setting `restart_needed=true`. |
| Remove `.restart` reads | `boot_remote._clean_stale_restart` becomes a no-op. | Safe. |
| Remove `.health` reads | Both readers (`harness.update_health` fallback at 208, `health_check.check_agent_health` at 329) drop the file branch. | No producers exist; reads were dead. **But**: confirm no third-party / out-of-tree agent still writes `.health` (project has been migrating; old wrappers on disk might still write). Mitigation: keep parser one release as warn-and-ignore. |
| Remove `.pid` reads | Both readers in `boot_remote` and `health_check`. | No producers in current tree. Same caveat as `.health`. |
| Remove `boot_remote.py` CLI (`main()`) | Any operator script or test that runs `python boot_remote.py --all` | Search for shell-level callers. `start_team.py` imports `boot_remote` as a module, not a subprocess — safe. Run a global grep for `boot_remote.py` invocations. |
| Remove `reboot_agent.py` CLI (or whole script) | Operators or other scripts running it directly | `start_team.cmd_reboot --force` imports `reboot_agent._kill_process` and `_read_claude_pid` — must move these helpers first. `harness.py` imports `reboot_agent._read_claude_pid`, `_kill_process` (1316, 1320, 1404, 1407) — same. Move helpers, then delete the script. |
| Convert `start_team.cmd_boot` to API call | Operators who run start_team with harness down (greenfield boot scenario) | Today they can boot agents with the harness down; this becomes impossible. **Mitigation**: `start_team --all` either auto-spawns the harness (like `squidsquad_cli start` does) or refuses with a clear error. |
| Add cycle_pre harness PID check | Operators running cycles without a harness (current dev workflow) | This would refuse to start cycles when harness is down. **Mitigation**: configurable behavior or warn-only mode. Phase 2 question. |

### 12.1 Existing inter-script silent-skip pairs (today)

These are pairs that already exist and the cleanup must remove together:

- Writer: `start_team._write_stop` → Readers: `boot_remote._needs_boot`, `harness.update_health`, `health_check.check_agent_health`, `reboot_agent.reboot`.
- Writer: `cycle_post._do_restart_sentinel` → Readers: none active (already silently broken).
- Writer: (gone) → Readers of `.health`: `harness.update_health`, `health_check.check_agent_health` (currently always-no-data path).
- Writer: (gone) → Readers of `.pid`: `boot_remote._read_pid_file`, `reboot_agent` reads `.pid` (gone path).

The cleanup is well-defined as long as **all readers and writers of a given sentinel are touched in the same change**.

---

## 13. Open Design Questions for PM (Phase 2)

These are the decisions Phase 2 must lock before a test plan can be written.

1. **Operator entry-point convergence.** Today there are three operator-facing tools: `start_team.py`, `squidsquad_cli.py`, `boot_remote.py --all`. Phase 2 must pick one canonical operator interface and either delete or thin-wrap the others. (Leading recommendation: `squidsquad_cli.py` is already API-pure — make it canonical, rewrite `start_team.py` as an alias or delete it, remove `boot_remote.py main()`.)

2. **Should `boot_remote.py` survive at all?** Two options:
   - (a) Survive as a harness-internal library `boot_remote.py` (no `main()`, no CLI flags) — minimal change.
   - (b) Absorb into `harness.py` as private functions — eliminates a file but bloats the harness module.

3. **Should `reboot_agent.py` survive at all?** Now that `POST /agents/{role}/restart` handles both idle-kill (#8689) and queued-restart, plus the only library uses are `_kill_process` and `_read_claude_pid`, the script is largely dead. Options:
   - (a) Delete entirely; move helpers into a new `process_ops.py` or into `harness.py`.
   - (b) Keep as harness-internal library (no `main()`).

4. **Does `health_check.py` still have a purpose?** With the harness owning liveness via `.claude-pid` and `GET /status`, the standalone script is duplicated work. Options:
   - (a) Delete; redirect all callers (only PM/QA cycle_pre and human ops) to `GET /status` via a thin Python helper.
   - (b) Keep as offline-fallback (when harness is down) but make it strictly read-only (no sentinel decisions, just process listing).

5. **Operator UX for "stop the team."** Today: `start_team --stop --all` → `POST /agents/all/stop`. Decision: keep per-role and all-roles endpoints both, or rationalize? (Recommendation: keep both — operators use both.)

6. **PID-based liveness vs heartbeat events.** The harness polls `.claude-pid` every 5s. Phase 5 (#7630) introduces an event bus that could carry agent heartbeats. Should the cleanup move liveness to event-bus heartbeats now, or stay PID-based until the event flip? (Strong recommendation: stay PID-based. Heartbeats are derived; PID is OS truth. #4792 should not change the liveness mechanism.)

7. **#7693 — how does graceful stop actually kill claude?** Per §5.3 / §9.2 the current docs claim "harness detects exit and respawns" but cycle_post.py exit 42 does NOT terminate claude. Phase 2 must pick the mechanism:
   - (a) `cycle_post.py` kills its own claude PID (read from `.claude-pid`) before exiting — easiest but violates "sole authority."
   - (b) `cycle_post.py` POSTs a `stop-confirmed` ack (already handled at `harness.py:1080`) → harness kills the claude PID in the next health poll if intent is STOPPING.
   - (c) Harness's poller actively kills claude PIDs whose intent is STOPPING/RESTARTING and whose `last_cycle_end` is recent (i.e., "agent finished cycle but didn't exit — finish the job").
   - (d) Have the agent's claude session invoke `/quit` itself when context exceeds threshold.
   - Recommendation: (b)+(c) hybrid. The ack is the request, the harness poll is the enforcer.

8. **Should cycle_pre.py check harness PID at start-of-cycle?** The issue body says wrapper scripts should check harness PID before each task/cycle and exit cleanly if dead. cycle_pre runs *inside* the agent, not as a wrapper. Decision points:
   - (a) Yes — cycle_pre does `GET /status`; if harness is unreachable, write status bar "no harness — idle" and skip the cycle. Risks: cycle never runs while harness is down, including for interactive dev.
   - (b) No — agents can run without harness. Harness intent and lifecycle are *additive*. (Current behavior.)
   - Recommendation: (b) for autonomy, but emit a clear warning in cycle-input.json so the agent can flag it.

9. **Should `.booting` sentinel survive?** It's a boot-slot lock owned entirely by `boot_remote`. Single writer, single reader, atomic write. It's not "split-brain" but it IS a sentinel file. Phase 2 decision: keep as a harness-internal lock (recommended) or replace with an in-memory lock inside harness.py? In-memory lock is fine for single-harness setups (which we are), but the file-based lock survives a harness crash mid-boot.

10. **Crash recovery semantics.** If the harness crashes between a `/stop` API call and the agent's next cycle, what happens?
    - Today: `.harness-state.json` persists intent. On restart, harness reads it and resumes monitoring. cycle_post next time queries intent → sees STOPPING → exits 42. So state survives.
    - Once `.stop` is gone, this is the *only* mechanism — confirm it works in all crash scenarios.

11. **Distribution / packaging audit.** Removed scripts (potentially `reboot_agent.py`, `boot_remote.py main()`) must be removed from `installer-files.txt` and `packages/cli/package.json`. Phase 2 test plan should include this.

12. **Agent CLAUDE.md sub-skill updates.** The `agent-lifecycle` fragment at `references/sub-skills/common/agent-lifecycle.md` references `start_team.py` and `.claude-pid` but not `.stop`. Other CLAUDE.md fragments still mention `.health` legacy fallback in the "Agent Infrastructure" section. After cleanup:
    - Remove `.health` legacy-fallback mentions (skill 1411, pm 1979, qa 1174, dm 1087).
    - Confirm `agent-lifecycle.md` matches the chosen canonical operator entry-point (question 1).
    - Compose-stack recompose all roles.

13. **Upgrade path.** Existing installs have leftover `.stop`, `.restart`, `.health` files on disk. Phase 2 must decide:
    - (a) Harness lifespan cleans them up on first boot post-upgrade.
    - (b) `compose.py deploy` or `wizard.py upgrade` cleans them up.
    - (c) Document manual cleanup ("`rm .squidsquad/*/.stop .squidsquad/*/.restart .squidsquad/*/.health`") — risky.
    - Recommendation: (a).

14. **#8692 interaction.** Singleton enforcement in `thin_launcher` uses `.claude-pid` as the auth signal. Confirm that the cleanup keeps `.claude-pid` exactly as-is (read by singleton check, written atomically by thin_launcher). Anything that touches `.claude-pid` rewrite semantics is out of scope.

15. **Diagnostic / observability.** `diagnostics.py` is also an API client (lines 136-173). Confirm it stays as a pure API client and isn't accidentally bypassed.

16. **Backward-compat window.** Phase 2 must decide whether to keep `.health` *parsing* (warn-and-ignore) for one release in case a stale agent still writes it, or delete the parser immediately. Same for `.pid`.

17. **start_team.py path bug (secondary).** `start_team._write_stop` writes `.stop` in **primary repo's** `.squidsquad/<role>/`, not in the agent's clone path (line 76: `SQUIDSQUAD_DIR / role`). When clone isolation is in effect, the file is in the wrong place. This bug will vanish with the cleanup but should be acknowledged so QA test cases verify primary-vs-clone path behavior.

---

## Appendix A — File:line bookmarks for reviewers

Key code anchors used in this audit, for fast jump-back:

- `harness.py:140` `HarnessState.update_health()` — central liveness + auto-reboot
- `harness.py:239` reads `.stop` in update_health
- `harness.py:1276-1347` `POST /agents/{role}/restart`
- `harness.py:1295-1298` deletes `.stop` on restart
- `harness.py:1350-1427` `POST /shutdown`
- `harness.py:1889-1950` `CtrlCHandler` 3-stage Ctrl+C
- `boot_remote.py:181-184` `_has_stop_sentinel`
- `boot_remote.py:211-242` `.booting` lock
- `boot_remote.py:262-288` `_read_health_file` (vestigial)
- `boot_remote.py:291-328` `_needs_boot` — gatekeeper read of every sentinel
- `boot_remote.py:381-515` `_spawn_*` family
- `boot_remote.py:522-578` `boot_agent`
- `reboot_agent.py:121-183` `reboot()` — `.stop` read at 134
- `reboot_agent.py:93-118` `_kill_and_respawn`
- `health_check.py:253-467` `check_agent_health` — `.stop` at 304, `.health` at 329
- `cycle_pre.py:676` stale comment for `.stop-after-cycle`
- `cycle_post.py:468-483` `_do_restart_sentinel` (DEPRECATED)
- `cycle_post.py:518-536` `_query_harness_intent` — HTTP path
- `cycle_post.py:539-575` `_do_stop_after_cycle_check`
- `cycle_post.py:741-743` exit 42
- `start_team.py:74-87` `_write_stop` / `_remove_stop`
- `start_team.py:114-179` `cmd_boot`, `cmd_reboot`, `cmd_stop`
- `thin_launcher.py:66-83` `_check_singleton` (#8692)
- `thin_launcher.py:86-101` `_write_pid` / `_clear_pid`
- `squidsquad_cli.py:122-238` pure API client commands
- `references/sub-skills/common/agent-lifecycle.md` — operator-facing doc

## Appendix B — Sentinels by status

| File | Status today | Action in cleanup |
|---|---|---|
| `.stop` | **Split-brain** — multiple readers, occasional fallback writer | **Remove** (writer + readers) |
| `.stop-after-cycle` | Doc debt only | **Remove comments** |
| `.restart` | Vestigial — writer exists but no behavior reader | **Remove writer + cleaner** |
| `.health` | Vestigial — no writer, parsers remain | **Remove parsers** |
| `.pid` (legacy) | Vestigial — no writer, fallback readers remain | **Remove readers** |
| `.booting` | Working — boot-slot lock, single writer/reader | **Keep** (harness-internal) |
| `.claude-pid` | Working — auth signal for liveness + singleton | **Keep unchanged** |
| `.harness-port` | Working — port discovery | **Keep unchanged** |
| `.harness-state.json` | Working — intent persistence | **Keep unchanged** |
| `.event-state.json` | Working — event-bus persistence | **Keep unchanged** |
