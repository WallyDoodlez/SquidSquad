Now I have all the information needed to produce the research document. Let me compile it.

---

# FEAT-PM-4966-SENTINEL Research — Replace .stop-after-cycle sentinel FILE with harness API endpoint

## Summary

This extension to #4966 proposes eliminating the last remaining sentinel file — `.stop-after-cycle` — by replacing it with a harness API call. Currently, the harness writes `.stop-after-cycle` into the agent's clone directory and `cycle_post.py` checks for the file at cycle end. Under the proposed change, `cycle_post.py` would instead call `GET /agents/{role}/intent` (or a similar endpoint) on the harness HTTP API. The harness already maintains an in-memory `intent` field per agent (`running`, `stopping`, `restarting` — see `harness.py` lines 69-75), so the information already exists; the file is a duplicate communication channel.

**Recommendation**: Feasible with caveats. The primary risk is harness unavailability — if the harness is down when `cycle_post.py` calls the intent endpoint, the agent cannot determine whether it should stop. This is a hard failure mode that the current file-based approach never has (files always work even if the harness is dead). The second risk is clone isolation: `cycle_post.py` runs inside a per-agent clone directory and has no direct way to discover the harness port (the `.harness-port` file lives in the primary repo's `.squidsquad/`, not the clone's). Both risks are solvable but require deliberate design.

## Vault Context

- **BRIEFING.md priorities**: #4439 Harness shipped, #4709 Harness Phase 2 planned, #4221 Agent harness supervisor process — this task directly extends the harness epic
- **Related decisions**: [[decision-pid-primary-liveness]] — "just use PID, it's more direct" — replacing file I/O with API calls aligns with preferring direct verification over indirect state files
- **Related decisions**: [[decision-watchdog-supervisor]] — centralized lifecycle management; the harness is already the lifecycle owner, this completes the centralization
- **Related decisions**: [[decision-self-healing-sentinel]] — two-tier self-healing; removing the sentinel file removes a failure mode (stale file) in favor of direct API
- **Human preferences**: "prefer direct/mechanical checks over indirect state files" — this change is a strong alignment. The human explicitly prefers OS-level/PID-level truth over application-level files that can go stale
- **Related learnings**: [[learning-powershell-start-job-cwd]] — CWD issues with spawned processes; relevant because `cycle_post.py` must resolve the harness port from its clone CWD

## Impact Analysis

- **Files touched**:
  - `references/scripts/harness.py` — add new `GET /agents/{role}/intent` endpoint (or similar); remove `.stop-after-cycle` file writes from stop/restart/shutdown handlers (lines 374, 441, 465, 525)
  - `references/scripts/cycle_post.py` — rewrite `_do_stop_after_cycle_check()` (lines 437-479) to call harness API instead of reading/writing files; add harness port discovery logic
  - `references/scripts/start_team.py` — `_write_stop_after_cycle()` (lines 40-46) replaced with harness API call; `_wait_for_exit()` (lines 85-98) updated
  - `references/scripts/squidsquad_cli.py` — any sentinel-writing paths redirected to API
  - `references/templates/start-role.ps1` — `.stop-after-cycle` file check in wrapper loop (lines 164-180) may be removed if wrappers are already being deleted per #4966
  - `references/sub-skills/common/agent-lifecycle.md` — updated to document API-based intent instead of sentinel file
  - `references/sub-skills/common/self-restart.md` — already describes `cycle_post.py` as the mechanical decision-maker; needs updating for API path
  - `tests/test_cycle_post.py` — `TestStopAfterCycleCheck` class (lines 336-380) rewritten for API mock
  - `tests/test_harness.py` — new tests for intent endpoint

- **Behavior changes**:
  1. **No more `.stop-after-cycle` file**: Harness sets intent in-memory only. `cycle_post.py` queries the harness API. The file is neither written nor read anywhere.
  2. **cycle_post.py becomes a harness client**: It must discover the harness port, make an HTTP request, and handle connection failures gracefully.
  3. **harness stop/restart endpoints become simpler**: Currently they write both intent AND the file (e.g., lines 430-448 in `stop_agent`). They'd only set intent.
  4. **Context pressure still triggers exit**: `cycle_post.py` still checks context pressure from `cycle-input.json`. If exceeded, it still exits with code 42. It may also POST to harness to report the context-pressure-triggered exit, rather than writing a file that the wrapper loop would detect.
  5. **wrapper loop becomes unnecessary**: Since #4966 eliminates wrappers entirely, the wrapper's `.stop-after-cycle` reading (lines 164-180 in `start-role.ps1`) is removed as part of the wrapper deletion.

- **Dependencies**:
  - `urllib.request` or `httpx` (already available in Python stdlib via `urllib` — `squidsquad_cli.py` already uses it, line 30)
  - Harness must be running and reachable on localhost
  - Port discovery mechanism (`.harness-port` file or well-known port)

## Side Effects

- **Risk 1: Harness is down when cycle_post queries intent** — Severity: H — If the harness crashes or hasn't been started, `cycle_post.py`'s API call fails. The agent has no way to know whether it should stop. Under the file-based approach, a harness crash doesn't prevent cycle_post from reading an already-written file. **Mitigation**: (a) `cycle_post.py` treats a connection failure as "no intent to stop" (safe default — agent continues running), with a warning log. (b) The harness writes a persistent intent file as a fallback only if it goes down (write-through cache pattern). (c) On harness restart, it re-syncs by checking agent process state and re-applying intent. The safe default (continue on failure) prevents agents from stopping unnecessarily but means a stop command issued just before a harness crash may be missed — acceptable since a crashed harness is a human-visible event.

- **Risk 2: Clone isolation — cycle_post can't find the harness port** — Severity: H — `cycle_post.py` runs inside the agent's clone directory (`{clone_path}/references/scripts/cycle_post.py`). It resolves `SQUID_DIR` as `{clone_path}/.squidsquad/` (line 29-30). But `.harness-port` is written by the harness to the *primary* repo's `.squidsquad/` directory (harness.py line 37-38: `SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"`). The clone does not have this file. **Mitigation**: Three options: (1) `cycle_post.py` walks parent directories until it finds `.squidsquad/.harness-port` — clones are children of the primary repo on disk, so walking up will find it. (2) The harness writes `.harness-port` to all known clone `.squidsquad/` directories on startup (harness already knows clone paths via `boot_remote._get_clone_path`). (3) Use a well-known default port (7373, harness.py line 40) as primary with port file as fallback. **Recommendation**: Option 3 (default port 7373 + port file fallback) combined with Option 1 (parent-directory search). This is simple, robust, and requires no intermediate file synchronization.

- **Risk 3: Context pressure exit becomes a network call away from being a disk read** — Severity: M — Currently, context pressure detection in `_do_stop_after_cycle_check` (lines 458-477) reads `cycle-input.json` from local disk (instant). The API call adds ~1-50ms latency. This is negligible for a cycle that takes seconds to minutes, but the function must not block indefinitely. **Mitigation**: Set a short HTTP timeout (e.g., 5 seconds) on the harness API call. If timeout fires, treat as "no intent" and continue.

- **Risk 4: Two sources of truth for context pressure exit** — Severity: M — Currently `_do_stop_after_cycle_check` does two things: (a) checks for externally-written `.stop-after-cycle` file, (b) checks context pressure and self-writes `.stop-after-cycle`. If (b) moves to a self-initiated exit (code 42 without any external signal), the function no longer needs to check anything external for context pressure. But the harness intent API is only for external stop/restart commands. This creates a split: context pressure = self-determined, harness intent = external. The function needs to handle both. **Mitigation**: The function becomes: (1) check context pressure from `cycle-input.json` → if exceeded, return True (exit 42), (2) call harness API → if intent is stopping/restarting, return True. Both paths independently trigger exit 42.

- **Risk 5: Race condition — harness sets intent between cycle_pre and cycle_post** — Severity: L — The question asks whether an intent set after `cycle_pre.py` runs but before `cycle_post.py` finishes would be missed. Under the file model: the file persists on disk, so cycle_post always sees it. Under the API model: intent is in-memory, so cycle_post always sees the *current* intent at the moment it calls the API. **This is strictly better than the file model.** The API call happens at the very end of `cycle_post.py` (line 563), so any intent set at any time before that call is visible. There is no window where intent is "lost" — the API returns the instantaneous state. The file model has a subtle race: if the harness writes the file while cycle_post is between the `sentinel.exists()` check (line 454) and the end of the function, and cycle_post then deletes `cycle-output.json` (line 556) — the file remains. Not a problem in practice because the check is the last operation, but the API model eliminates any TOCTOU concern entirely.

## Edge Cases

- **Harness not running at agent startup**: If `cycle_post.py` cannot reach the harness on its first cycle, it logs a warning and continues (safe default: no intent to stop). The agent runs normally. When the harness starts later, subsequent cycles will discover it. The harness's health poller will also detect the running agent and register it.

- **Harness crashes between cycles**: Agent completes `cycle_post.py` → harness was up during check → agent continues. Next cycle: harness is down → API call fails → agent treats as "no intent" and continues. The harness restart recovers intent from its state machine (currently memory-only; may need persistence for crash recovery). Acceptable — a harness crash is a human-visible event that requires intervention anyway.

- **Multiple agents querying intent simultaneously**: The harness FastAPI server handles concurrent requests natively (async endpoints via uvicorn). No file locking concerns, no Windows file sharing issues. This is a reliability improvement over the file model.

- **Agent running in clone that was moved/deleted**: The harness port discovery (parent-directory walk) would fail if the clone is moved outside the repo tree. Mitigation: fall back to default port 7373 + localhost. If the harness doesn't respond on default port, treat as "no intent."

- **Network interface issues on localhost**: localhost (127.0.0.1) is the loopback interface — it never goes down as long as the TCP/IP stack is running. The only failure mode is the harness process not listening. This is identical to the harness process not running.

- **Switching from file to API mid-upgrade**: During the transition, the harness may still write `.stop-after-cycle` while `cycle_post.py` starts calling the API. Graceful degradation: `cycle_post.py` checks the API first; if that succeeds, it ignores any stale file. If the API fails, it falls back to checking the file. After one version, the file fallback is removed.

## Integration Risks

- **start_team.py --reboot currently waits for file disappearance**: `_wait_for_exit()` (start_team.py lines 85-98) polls for `.stop-after-cycle` disappearance as proof the agent consumed the signal. Under the API model, this mechanism changes: `start_team.py` calls harness API to set intent=restarting, then polls harness `GET /agents/{role}` to check if the agent's status has transitioned (e.g., `current-state` shows `idle` or `restarting`). This is feasible but requires the harness to expose agent phase information.

- **Wrapper loop (start-role.ps1) reads .stop-after-cycle**: If wrapper scripts are being eliminated per #4966, this is irrelevant. If they survive into the transition period, the wrapper needs to be updated to call the harness API instead of checking the file, or the harness must continue writing the file as a backward-compat shim.

- **Harness auto-reboot on death reads .stop-after-cycle**: In `harness.py` update_health (lines 168-175), when an agent with intent=stopping dies, the harness cleans up `.stop-after-cycle`. Under the API model, there is no file to clean up — the intent field is simply reset or left as `stopping` (agent died as intended). This simplifies the code.

- **health_check.py and the .stop-after-cycle sentinel**: `health_check.py` does not currently read `.stop-after-cycle` — it reads `.health`, `.pid`, `.stop`, and `.restart`. No impact.

## Upgrade & Migration

- **New config values**: none required. The harness port is already configured (`Harness` → `Port` in config.md, default 7373). The API timeout for `cycle_post.py` could be configurable but a hardcoded 5s default is sufficient.

- **New files**: none. The `.harness-port` file already exists (harness.py line 38: `HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"`).

- **Template changes**: `cycle-runner.md` — remove or update the reference to `restart_needed` field (line 57). `self-restart.md` — update to describe API-based intent check instead of file-based sentinel. `agent-lifecycle.md` — update sentinel file list (remove `.stop-after-cycle`, add "harness intent API").

- **Upgrade steps**:
  1. Deploy updated harness with intent endpoint (backward-compatible: harness still writes `.stop-after-cycle` for one version)
  2. Deploy updated `cycle_post.py` with API-first, file-fallback logic
  3. Deploy updated `start_team.py` with API-first sentinel operations
  4. Run `compose.py deploy-all` to regenerate CLAUDE.md files
  5. After one version of stable API operation, remove file write from harness and file fallback from cycle_post

- **Graceful degradation**: If the user hasn't upgraded `cycle_post.py` but has the new harness, the harness still writes `.stop-after-cycle` (backward compat). If the user has the new `cycle_post.py` but the old harness (no intent endpoint), the API call fails and `cycle_post.py` falls back to the file check. Both directions degrade safely.

## Open Questions

- **Q1: Should the harness persist intent to disk for crash recovery?** — **Why**: Currently intent is memory-only in `HarnessState` (harness.py lines 96-104). If the harness crashes and restarts, it loses all intent state. Running agents would have their intent reset to `running` (default). A stop command issued just before a harness crash would be silently lost. This is the same class of problem as the current model (if harness crashes, it can't write `.stop-after-cycle` either), but it's more acute because the API model has no durable artifact. **Recommendation**: For this task (eliminating the last sentinel file), accept memory-only intent as equivalent to the current reliability. Persisting intent to `.squidsquad/.harness-state.json` can be a separate enhancement.

- **Q2: What endpoint exactly? `GET /agents/{role}/intent` or embed in existing `/agents/{role}`?** — **Why**: The existing `GET /agents/{role}` endpoint (harness.py lines 387-395) already returns `intent` in the agent's `to_dict()` output (line 87). So `cycle_post.py` could call `GET /agents/{role}` and read the `intent` field — no new endpoint needed. The endpoint already exists and is tested (test_harness.py line 251). **Recommendation**: Use the existing `GET /agents/{role}` endpoint. Add a dedicated `GET /agents/{role}/intent` only if latency or response size concerns arise (the full agent dict is ~6 fields — negligible).

- **Q3: Should context pressure exit also be reported to the harness?** — **Why**: Currently, when context pressure triggers exit 42, the wrapper respawns the agent. In the #4966 model where the harness owns all lifecycle, the harness needs to know about the context-pressure exit so it can respawn the agent. Exit code 42 is already the signal — the harness's process monitor detects the exit. But if the harness only sees "process exited" without knowing it was code 42 vs a crash, it can't distinguish between "needs respawn" and "crashed, apply backoff." **Recommendation**: `cycle_post.py` should POST to a harness endpoint (e.g., `POST /agents/{role}/context-pressure-exit`) to inform the harness, or the harness should read the exit code from the process return. This is already a concern in #4966, not new to this extension.

- **Q4: Should `cycle_post.py` cache the harness port or re-discover each cycle?** — **Why**: Port discovery (parent-directory walk + default port) takes milliseconds. Re-discovering each cycle is safer (handles port changes if harness restarts on a different port). Caching could cause a single missed cycle if the port changes. **Recommendation**: Re-discover each cycle. The cost is negligible.

## Recommendation

**Feasible with caveats.** The API-based intent check is architecturally cleaner than the file-based sentinel — it eliminates the last sentinel file, aligns with the human's preference for direct verification over indirect state files, and resolves a TOCTOU race condition. The two caveats are:

1. **Harness availability**: `cycle_post.py` must handle API connection failures gracefully. Safe default = "no intent to stop, continue running." This means a stop command issued during a harness outage may be missed — acceptable because a harness outage is a hard failure that requires human attention.

2. **Clone isolation + port discovery**: `cycle_post.py` in a clone needs to find the harness. Parent-directory walk to find `.squidsquad/.harness-port` plus default port 7373 fallback provides reliable discovery without cross-clone file synchronization.

The implementation surface is small: ~30 lines changed in `cycle_post.py` (rewrite `_do_stop_after_cycle_check`), ~10 lines removed from `harness.py` (stop writing `.stop-after-cycle` in stop/restart paths), and a new parent-directory port discovery helper. The existing `GET /agents/{role}` endpoint already exposes `intent` — no new endpoint required.

## Vault Candidates

- **Type**: decision — "Eliminate .stop-after-cycle sentinel file in favor of harness intent API" — **Why**: This is the final step in the sentinel-elimination journey (#3807 → #4966). The decision to use API-over-file for the last remaining sentinel is a significant architectural choice that future contributors need to understand: why API, what the failure modes are, and how clone isolation is handled.

- **Type**: pattern — "Parent-directory port discovery for clone-isolated agents" — **Why**: The specific algorithm for a script in a clone directory to find the harness port (walk up to primary repo → read `.harness-port` → fall back to default port 7373) is reusable for any agent-side script that needs to communicate with the harness.

- **Type**: pattern — "Safe-default-on-API-failure for lifecycle signals" — **Why**: When an agent's cycle_post cannot reach the harness API, the safe default is "continue running" (not "stop"). This pattern — choosing the safe default for each signal direction — applies to any agent↔harness communication where availability is not guaranteed.

- **Type**: learning — "API-based intent eliminates TOCTOU races inherent in file-based sentinels" — **Why**: The file-based model has an inherent window between "check if file exists" and "act on it." The API model returns instantaneous state at query time. This is a concrete architectural improvement worth documenting for future sentinel/signal design decisions.

- **Type**: learning — "Dual-write phase (API + file) enables safe migration from file-based to API-based signals" — **Why**: The upgrade path where harness writes both intent (API) and file (for one version), and cycle_post reads API-first with file-fallback, demonstrates a zero-downtime migration pattern for replacing file-based communication with API-based communication. Reusable for other sentinel migrations.