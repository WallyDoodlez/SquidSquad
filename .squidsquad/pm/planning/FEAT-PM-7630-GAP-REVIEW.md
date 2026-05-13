Now I have all the information needed. Let me compose the comprehensive gap analysis.

---

# FEAT-PM-7630-GAP-REVIEW Research — Event-Driven Agent Architecture Gap Analysis

## Summary

This analysis reviewed the FEAT-PM-7630 RESEARCH.md and CONTEXT.md against the actual codebase at `references/scripts/`. The proposed architecture is feasible in principle — the event bus infrastructure exists (harness.py lines 344–389, event_bus.py, event_bus_reader.py, event_catalog.py), the mechanical/creative split from #2057 is battle-tested, and the human's preferences are clear. However, the CONTEXT.md locked decisions contain a fatal contradiction: they lock "persistent session + Monitor tool" as the wake mechanism, but the Monitor tool requires Claude Code v2.1.98+ which is not installed (current: v2.1.86), and prior PM research (FEAT-PM-5613-MONITOR-RESEARCH.md) concluded "Monitor cannot completely replace /loop." PHASE2-PREP correctly identifies this and recommends stateless spawn instead — but this contradicts the CONTEXT.md Out of Scope line that says "Stateless spawn model — decided against."

**Primary risks**: (1) The locked wake model depends on unavailable infrastructure. (2) Locked Decision #3 ("kill cycles entirely") conflicts with PHASE2-PREP's recommendation to preserve cycle-output.json. (3) The event bus has no disk persistence — a harness restart loses the "sole agent activation mechanism." (4) Six critical architectural gaps (event closure API, scan-due timer, terminal PID tracking, per-event logs, idempotent comments, clone context-pressure monitoring) have zero implementation. (5) Windows-specific file locking, process tracking, and signal limitations add material risk to the Monitor-tool-based wake model.

**Recommendation**: Needs rethinking of the wake mechanism lock before Phase 2 can begin. The stateless spawn model (PHASE2-PREP Option A) is the only currently implementable path. All other phases (1, 3, 4) are straightforward.

## Vault Context

- **BRIEFING.md priorities**: #7630 is the active top priority, supersedes #6056/#5775/#5613, labeled "next major architectural shift — all mechanical cycle steps move to harness"
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 split mechanical/creative; #7630 completes the transfer of cycle orchestration to harness. [[decision-clone-isolation-architecture]] — agents run in sibling clones, not children; this affects event bus port discovery (event_bus_reader.py lines 42–53 parent-dir walk may fail for sibling clones). [[decision-pid-primary-liveness]] — OS-level truth preferred; aligns with harness PID checks but conflicts with file-polling wake signals.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — directly applicable: cycle orchestration prose in templates must become harness code. [[pattern-windows-utf8-subprocess]] — Windows subprocess encoding handling is already established.
- **Human preferences**: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" and "agents should react to events, not run multi-step cycles." Context pressure threshold: 70%. "Prefers direct/mechanical checks over indirect state files." "Systems should self-heal: detect stuck states → unstick immediately." All drive #7630.
- **Related learnings**: [[learning-commit-code-state-exclusion]] — original motivation for #2057; same class of problem (LLMs cannot reliably execute mechanical sequences). [[learning-atomic-migration-strategy]] — any migration must be atomic: all templates, scripts, and harness changes in one deploy.

## Impact Analysis

- **Files touched**: 30+ files confirmed via codebase analysis:
  - `references/scripts/harness.py` (1415 lines) — major expansion: event closure API (missing `POST /events/{id}/complete`), scan-due timer, terminal PID tracking, per-role event in-flight queues, context-pressure monitoring for clones
  - `references/scripts/cycle_pre.py` (1058 lines) — becomes harness-internal
  - `references/scripts/cycle_post.py` (746 lines) — becomes harness-internal or absorbed into closure callback
  - `references/scripts/event_bus.py` (103 lines) — new event types for wake/stop/scan-due
  - `references/scripts/event_bus_reader.py` (89 lines) — may be superseded by harness-pushed events or Monitor tool watcher
  - `references/scripts/event_catalog.py` (216 lines) — 8+ new event types needed
  - `references/scripts/boot_remote.py` (652 lines) — must return terminal PID for cleanup
  - `references/scripts/thin_launcher.py` (117 lines) — boot prompt changes, Monitor tool setup vs. stateless spawn
  - `references/scripts/config.py` (330+ lines) — new config fields
  - `references/sub-skills/common/cycle-runner.md` (93 lines) — removed
  - `references/sub-skills/common/context-pressure.md` (19 lines) — absorbed by harness
  - `references/sub-skills/common/event-reactions.md` (32 lines) — rewritten as metadata
  - `references/sub-skills/common/self-restart.md` (21 lines) — absorbed
  - `references/sub-skills/common/agent-lifecycle.md` (46 lines) — rewritten
  - `references/sub-skills/common/improvement-scan.md` (103 lines) — trigger mechanism changes
  - `references/roles/{dev,pm,qa,dm}/instructions.md` — ~60% content stripped
  - `references/roles/{dev,pm,qa,dm}/includes.yml` (24 files) — 4-5 sub-skills removed each
  - `references/sub-skills/common/interval-sync.md` — removed
  - `references/statusline.sh` (471 lines) — context-pressure writing continues, but agent reading is removed

- **Behavior changes**: 8 major behavior shifts as documented in RESEARCH.md lines 51–58. Additional: event cursor advancement moves from cycle_post.py to harness; status bar transitions become harness-driven.

- **Dependencies**: FastAPI + uvicorn (in harness.py), boot_remote.py, health_check.py, event_bus.py, event_bus_reader.py, git_ops.py, tracker.py, config.py, Claude Code CLI. New dependency: Claude Code v2.1.98+ (if Monitor tool path chosen).

## Side Effects (Gaps & Risks)

### 1. Architectural Gaps

**GAP-1: Event closure API does not exist** — Severity: **H** — CONTEXT.md Locked Decision #4 requires `POST /events/{event_id}/complete` with structured result payload. harness.py currently has only `POST /events` (line 814, receive_event) and `GET /events` (line 844). No endpoint for event completion exists. No event lifecycle state (open/closed) is tracked in EventStream (line 348). This is the fundamental contract between agent creative work and harness post-processing — without it, nothing in Phase 2 works.

**GAP-2: Monitor tool is not available** — Severity: **H** — CONTEXT.md Locked Decision #1 commits to "Persistent session + Monitor tool (Claude Code v2.1.98+)." Current install is v2.1.86. FEAT-PM-5613-MONITOR-RESEARCH.md already determined "Monitor cannot completely replace /loop." No Monitor tool invocation exists anywhere in the codebase. The entire wake model Locked Decision depends on infrastructure that doesn't exist in the installed version.

**GAP-3: scan-due idle timeout timer does not exist** — Severity: **H** — CONTEXT.md Locked Decision #5 requires harness to emit `scan-due` after 10 minutes with no completed events, with an issue gate (skip if role has open bugs). Harness has no `last_event_completed[role]` timestamp tracking. No idle timeout monitor exists. The issue gate requires querying GitHub Issues from harness — currently done by cycle_pre.py (lines 913-922) which will be removed. The quiet-cycle counter currently lives in cycle_pre.py working-state processing (lines 1037).

**GAP-4: Terminal PID not tracked** — Severity: **M** — CONTEXT.md Locked Decision #6 requires harness to close terminal windows on clean stop. thin_launcher.py writes only Claude PID (line 96). boot_remote.py `_spawn_windows` (line 395) spawns via `wt.exe` or `cmd /c start` — neither returns the terminal window PID. `.harness-state.json` stores `claude_pid` (line 304) but has no `terminal_pid` field. On Windows, `wt.exe new-tab` creates a new tab whose PID is not easily correlated to the spawned process.

**GAP-5: Per-event log format undefined** — Severity: **M** — CONTEXT.md says "Per-event log entries replace per-cycle iteration logs." Current iteration logs use `cycle.py log-iteration` (cycle_post.py lines 228-246) writing `iter-{N}.md`. No per-event log design exists. Historical audit trail must span both formats. Dev discretion on format (CONTEXT.md line 51) but no design constraints provided.

**GAP-6: Event bus has no disk persistence** — Severity: **H** — CONTEXT.md declares "Event bus becomes the sole agent activation mechanism." EventStream is an in-memory `collections.deque` with 1000-event cap (harness.py line 352). On harness restart, all events are lost. Crash recovery can't re-emit events because there's no record of what was emitted. CONTEXT.md delegates storage format to dev discretion (line 47), but no persistence means the "sole activation mechanism" can't survive a restart.

**GAP-7: Idempotent tracker comments by event_id not implemented** — Severity: **M** — CONTEXT.md Side Effect Mitigation requires "comments need dedup by event_id." tracker.py comment command (called by cycle_post.py line 213) has no event_id parameter. No deduplication mechanism exists. If an event is re-emitted after crash recovery, duplicate tracker comments will be posted.

**GAP-8: Clone context-pressure monitoring** — Severity: **M** — CONTEXT.md requires harness to "monitor context pressure files and trigger restarts independently." harness.py `GET /agents/{role}/health` (line 676) reads context-pressure from the primary repo's `.squidsquad/<role>/context-pressure`. For clone agents, statusline.sh writes to the clone (line 72), but harness doesn't reliably know clone paths at check time. AgentState.clone_path (line 72) is set during health polling but may be stale.

**GAP-9: Per-role event in-flight queue** — Severity: **M** — CONTEXT.md requires "Harness must not emit a second event to the same role while the first is unclosed (queue events per role)." No per-role event queue or in-flight tracking exists in harness.py. EventStream has no concept of "dispatched but unclosed."

### 2. Race Conditions

**RACE-1: Startup race — agents boot before harness ready** — harness.py lines 475–491 auto-starts all agents, deferred-init thread runs at line 492. Agents launch immediately via boot_remote.py while the event bus may not be accepting connections yet. In event-driven mode, agents that boot before monitors start will find no events and sit idle — potentially forever if no events are ever emitted. The Monitor tool subscription (if used) would fail if the /events endpoint isn't ready.

**RACE-2: Compose-completed → reboot race** — harness.py lines 1147–1156 emit `compose-completed` then call `_reboot_affected_agents` (line 1179) which sets `intent=restarting`. CONTEXT.md says "compose-completed event should wake affected agents rather than rebooting them." If an agent wakes on `compose-completed` before the reboot executes, it reads stale CLAUDE.md (old templates). If the reboot happens first, the agent session is killed before it can process the event. Ordering must be: reboot → then emit compose-completed for awareness only.

**RACE-3: Event bus re-entrant state mutation** — `_update_agent_from_event` (harness.py line 737) is called from `receive_event` (line 836) in the uvicorn thread. `update_health` (line 155) runs in the health-poller thread. Both access `AgentState` fields. `HarnessState._lock` protects the dictionary, but `_update_agent_from_event` calls `state.get_agent(role)` which returns a reference to the AgentState object — field mutations to this object happen outside the lock. If the health poller reads `agent.current_cycle` while an event handler writes it, the value is undefined.

**RACE-4: Event ID collision across emission sources** — event_bus.py `_generate_id` (line 61) uses SHA256 hash with 8-char truncation. harness.py `_emit_event` (line 1017) uses `os.urandom(4).hex()` (8 hex chars from 4 random bytes). Two different ID schemes with different collision properties. 4 bytes of randomness = birthday collision at ~65K events (within operational range for days-running systems). An ID collision would corrupt event cursor advancement in cycle_post.py `_advance_event_cursor` (line 588).

**RACE-5: Event cursor advancement crash window** — cycle_post.py `_advance_event_cursor` (line 588) advances the cursor AFTER the creative phase and AFTER commit/push/transitions. If harness crashes between agent writing cycle-output.json and cursor advancement on restart, events are replayed. In the event-driven model, this maps to: agent POSTs `/events/{id}/complete`, harness processes closure (commits, transitions), crashes before persisting "event closed" state → on restart, harness sees event as still unclosed and re-emits it, causing duplicate work.

**RACE-6: Clone isolation breaks event bus discovery** — event_bus_reader.py `_discover_port` (line 27) walks parent directories looking for `.squidsquad/.harness-port`. Per [[decision-clone-isolation-architecture]], agent clones are siblings of the primary repo (e.g., `../SquidSquad-skill/`), not children. The walk goes UP from clone → parent → grandparent. If clones aren't nested under primary, the walk never finds the harness port file, and all event queries silently return `[]` (line 89). This already affects event consumption (silently degraded) but becomes critical when events are the sole activation mechanism.

**RACE-7: Shutdown event loss** — harness.py shutdown (line 926) sets `intent=stopping`, waits for agents to idle, then kills. If an agent emits an event during shutdown grace period (e.g., cycle-end via event_bus.py), the event is stored but no agent exists to process it. On next startup, stale events (e.g., `pr-merged` for a PR already merged) could trigger duplicate work.

**RACE-8: File-based wake trigger TOCTOU (if Monitor uses file watching)** — If Monitor tool watches a file for wake signals and harness writes a trigger file, there's a TOCTOU race on Windows where the write and the watch notification are not atomic. The statusline.sh already uses `.tmp` → `mv` atomic writes for context-pressure (line 72), but Monitor tool file watching behavior on Windows is completely unverified.

### 3. Failure Modes

**Harness crash during event processing:**
- `.harness-state.json` (line 285–313, save_state) persists PID, intent, boot_time, clone_path, claude_pid. Does NOT store: in-flight event IDs, event dispatch state, unclosed event queue, last_event_completed timestamps.
- On restart, harness has no record of which events were sent to which agents. Agents may be mid-work but harness doesn't know.
- If using stateless spawn: agent exits, harness processes output, harness crashes before persisting → work result lost.
- If using persistent session: agent processes event, harness crashes before agent POSTs closure → agent's closure POST fails → agent can't close event → event eventually times out (if timeout mechanism exists, which it doesn't yet).

**Agent crash during event:**
- CONTEXT.md says "unclosed events = diagnostic signal." But no timeout mechanism, no stuck-event detection, no diagnostic reporting exists.
- Health polling (harness.py line 265, 5-second interval) detects dead agent via PID check. But can't distinguish "crashed mid-event" from "working on a long task."
- If agent crashes after POSTing `/events/{id}/complete` but before harness finishes processing, the event is in a partially-processed state (some transitions done, some not).

**Monitor tool disconnection (1-hour max timeout):**
- FEAT-PM-5613-MONITOR-RESEARCH.md line 13: "The 1-hour max Monitor timeout compounds this." The Monitor tool subscription expires. During reconnection gap, events emitted to that role are missed.
- The event bus (in-memory deque) has no mechanism to buffer events per-role during disconnection.
- Agent must implement reconnection logic → mechanical residue in templates, defeating the purpose.

**Git operation failure during closure callback:**
- CONTEXT.md says harness owns git commit/push after closure. If `git push` fails in the closure callback, the event is processed but code isn't pushed.
- cycle_post.py currently has complex error handling for this (line 325-343: "Nothing to commit" detection, branch verification). This logic must be replicated in harness.
- No atomicity guarantee: event closed ≠ code committed+pushed.

**Stop signal delivery failure:**
- Locked Decision #2: harness emits `intent:stop-requested` on event bus, Monitor tool detects it. If Monitor has disconnected (timeout), agent never sees stop signal.
- No fallback mechanism. Sentinel file pattern (PHASE2-PREP Q-STOP Option A) is more reliable but contradicts the "event bus only" channel design.

**Event bus overflow (1000-event cap):**
- EventStream maxlen=1000 (harness.py line 352). At high event rates (e.g., multiple agents doing rapid work), old events are silently evicted.
- If an agent's event cursor references an evicted event, `get_since` returns oldest available events (line 380), causing re-delivery.
- With per-event tracking replacing per-cycle tracking, event volume increases significantly.

### 4. Windows-Specific Risks

**File locking on context-pressure reads:**
- statusline.sh writes context-pressure to `.squidsquad/<role>/context-pressure` using atomic `.tmp` → `mv` (line 72). On Windows, `mv` of an open file can fail with permission errors if another process has the file open.
- Harness reading context-pressure from clone (for health endpoint line 704-708) while statusline writes it → potential `PermissionError` on `Path.read_text()`. Python's file reading on Windows uses sharing modes that may conflict with bash's redirect.

**PID reuse window:**
- boot_remote.py `_is_process_alive` (line 163) uses `tasklist /FI "PID eq {pid}"` on Windows. Windows PID reuse is faster than Unix (PIDs wrap around more quickly in a 32-bit space).
- If an agent dies and its PID is reused by an unrelated Windows process within the 5-second health poll interval, harness thinks agent is alive.
- `.claude-pid` file adds a second factor but is only read on health check, not continuously verified against the actual process name.

**Terminal window tracking on Windows:**
- `wt.exe new-tab` (boot_remote.py line 401) spawns a tab in Windows Terminal. The spawned process (python thin_launcher.py) is a child of wt.exe, but wt.exe's PID is not returned or recorded.
- `cmd /c start` (line 425) creates a new console window via `conhost.exe`. The relationship between the spawned python process and the console window is not tracked.
- `taskkill /PID` kills a process but cannot specifically close a terminal window without killing the agent inside it.
- CONTEXT.md Locked Decision #6 (close terminal on clean stop) is significantly harder on Windows than Unix.

**Signal handling limitations:**
- Windows does not support SIGTERM. harness.py Ctrl+C escalation (line 1294–1355) uses SIGINT only.
- There is no cross-platform way to send a "graceful stop" signal to a Claude Code process. The stop mechanism MUST be file-based or API-based — which aligns with current design but means no emergency interrupt capability.
- If Claude Code hangs (infinite loop in creative work), there's no way to interrupt it short of `taskkill /F`.

**Path separator mismatches in clone isolation:**
- boot_remote.py resolves `.local-config` relative paths against `REPO_ROOT` (line 79). On Windows, `Path` objects may contain backslashes. `.local-config` may contain forward slashes.
- Path comparison (`Path("C:\\Users\\...") == Path("C:/Users/...")`) works in Python but string-based comparisons (e.g., in statusline.sh line 322) may not.

**Subprocess flags are Windows-only:**
- `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (boot_remote.py line 414) are Windows-specific `creationflags`. These flags mean the child process has no console attachment and runs in a new process group.
- Harness cannot signal detached processes — they don't receive console control events.
- If thin_launcher.py is spawned detached, it won't receive Ctrl+C even if the human presses it in the terminal.

### 5. Monitor Tool Assumptions

**Assumption 1: Monitor tool exists in v2.1.98+** — The installed version is v2.1.86. FEAT-PM-5613-MONITOR-RESEARCH.md was unable to verify the Monitor tool's API, capabilities, or even existence. The entire wake model lock depends on a version upgrade that hasn't happened and an API that hasn't been validated. If Monitor tool works differently than assumed — for example, it watches files not HTTP endpoints, or has a 5-minute minimum polling interval instead of sub-second, or doesn't support custom watcher scripts — the wake model fails completely.

**Assumption 2: Monitor can watch the event bus** — The event bus is an HTTP endpoint (`GET /events`), not a file. Monitor tool watches "shell command stdout" (per 5613-RESEARCH). To bridge this, a watcher script must poll `GET /events` and output new events to stdout. This is polling wrapped in Monitor — not truly event-driven. The 500ms HTTP timeout in event_bus_reader.py (line 24) is designed for fire-and-forget within a cycle, not continuous streaming. A long-lived watcher script must handle: connection errors, harness restart (port change), event filtering per role, and never blocking the Monitor tool's timeout window.

**Assumption 3: Sub-second wake latency** — CONTEXT.md claims "agent wakes immediately (sub-second)." With a watcher script polling HTTP endpoints, actual latency is: poll interval (unknown) + HTTP round-trip (50-200ms) + JSON parsing + Monitor tool notification + agent context loading. Realistic latency is 500ms-2s, not sub-second. This is still acceptable but the claim should be calibrated.

**Assumption 4: Single Monitor per session** — Monitor tool capabilities are unknown. Can one session run multiple Monitor subscriptions (one for work events, one for stop-requested)? Can Monitor subscription be changed mid-session? If only one Monitor is allowed, the agent must multiplex work and stop detection into a single watcher script.

**Assumption 5: Monitor survives session lifetime** — 5613-RESEARCH says "1-hour max Monitor timeout." For days-running persistent sessions, Monitor must reconnect every hour. The agent template must include reconnection mechanics — which is exactly the kind of mechanical prose #7630 aims to eliminate. Stateless spawn avoids this entirely.

### 6. Migration Risks

**MR-1: Cross-role coordination breaks with partial migration** — CONTEXT.md says "Both models cannot run simultaneously for the same role." If PM migrates to event-driven but skill stays on cycles: PM emits `verification-failed` event → skill won't see it until next cycle_pre.py (up to 30-minute delay). The `event-driven` config flag is per-instance, but the gating must prevent mixed-mode teams. Currently, there's no cross-role event-driven detection — a role doesn't know if other roles are on events or cycles.

**MR-2: cycle-output.json contract uncertainty** — Locked Decision #3 says "No /loop, no cycle_pre.py, no cycle_post.py, no cycle-input.json, no cycle-output.json." PHASE2-PREP Q2 recommends Option A: "Agent still writes cycle-output.json; harness reads it post-exit." These are fundamentally contradictory. The role-specific extras in cycle-output.json (code_commit, pr_actions, vault_writes, version_bump, etc. — cycle-runner.md lines 73-92) represent years of accumulated business logic. Removing cycle-output.json means redesigning all of these. Keeping it violates Locked Decision #3.

**MR-3: /loop removal renders agents inert on failure** — All instruction files currently contain `/loop [INTERVAL]m` (dev/instructions.md line 27, pm/instructions.md line 16). Removing /loop means agents have ZERO re-invocation mechanism. If the event-driven wake mechanism has any bug — missed event, Monitor timeout, harness crash — agents sit idle forever. Current `/loop` provides a reliable fallback that guarantees eventual progress. The event-driven model has no equivalent safety net.

**MR-4: Template migration scope is massive and fragile** — 24 `includes.yml` manifests must change. 4 `instructions.md` files stripped of ~60% content. 6 sub-skills removed or rewritten. 1 new sub-skill (`event-driven-workflow.md`). compose.py must handle the new includes without breaking existing agents. All changes must be atomic ([[learning-atomic-migration-strategy]]). No partial deployment possible.

**MR-5: Iteration log format break** — Per-cycle iteration logs (`iter-{N}.md` in `.squidsquad/<role>/iterations/`) are the system's audit trail. Per-event logs create a format schism. Historical queries, status bar cycle counting (statusline.sh line 93), and cycle number computation (cycle_pre.py `_get_cycle_number` line 318) all reference iteration logs. The status bar's cycle timer (statusline.sh lines 88-119) is based on `current-state` file mtime — with no cycles, what drives the status bar display?

**MR-6: Config flag gating must be bulletproof** — `event-driven: yes/no` gates the entire new behavior. If this flag is misconfigured (yes but Monitor tool not available, or yes but no harness running), agents must fail safely into the old model. The config.py `get_field` function (line 71-72) returns empty string on missing field, which would be falsy — but explicit boolean parsing (`== "yes"`) is needed, not truthiness.

### 7. Missing Event Types

The event_catalog.py currently defines 12 EMITTED types and 5 RECOGNIZED types. The event-driven model requires at minimum these additional types, none of which exist:

**Work dispatch events (not in catalog):**
- `work-available` — harness detected work for an agent (emits before `agent-wake`)
- `work-started` — agent acknowledged and began processing an event
- `work-completed` — agent finished processing and called closure API
- `agent-idle` — agent has no pending work and is waiting

**Lifecycle events (not in catalog):**
- `stop-requested` — harness requests agent to stop (Locked Decision #2) — must be in event_catalog.py EMITTED tier
- `agent-stopping` — agent acknowledges stop request and is checkpointing
- `agent-stopped` — agent exited cleanly

**Scan events (not in catalog):**
- `scan-due` — harness triggers improvement scan (Locked Decision #5)
- `scan-completed` — agent completed scan and reported findings

**Error/diagnostic events (not in catalog):**
- `event-timeout` — harness detected an unclosed event beyond timeout
- `event-reemitted` — harness re-emitted an event after crash recovery
- `work-failed` — agent failed to process an event (error, not verification failure)

**Events for agent activities not covered:**
- **Subagent spawn**: dev instructions.md line 17 says "spawning subagents via the Agent tool." Subagent work is agent-initiated within a single event. No event type for subagent-start/subagent-complete. If subagent work fails, there's no event trail.
- **Human interaction**: PM checks for human input each cycle. In event-driven model, human input must become an event. No `human-input-received` event type. How does human communication enter the event bus?
- **Vault operations**: Out of Scope says "harness emits vault-reflect event instead of agent checking a counter." No `vault-reflect` event type in the catalog.
- **Pipeline stall detection**: human-profile.md says "Systems should self-heal: detect stuck states → unstick immediately." No `pipeline-stalled` or `agent-stuck` event for harness-initiated diagnostics.

### 8. Contradictions

**CONTRADICTION-1: Kill cycles vs. Keep cycle-output.json (FATAL)**
- CONTEXT.md Locked Decision #3: "No /loop, no cycle_pre.py, no cycle_post.py, no cycle-input.json, no cycle-output.json, no cycle counters, no iteration logs in the current format. The cycle concept is replaced entirely."
- PHASE2-PREP Q2 PM Recommendation: "Option A. Agent still writes cycle-output.json; harness reads it post-exit. The output contract is unchanged... Preserving it costs nothing and avoids a high-risk rewrite."
- **These are directly contradictory.** The locked decision says eliminate cycle-output.json entirely. The recommended implementation preserves it. One must yield. If cycle-output.json is eliminated, the role-specific extras (code_commit, pr_actions, vault_writes, version_bump, etc. — cycle-runner.md lines 73-92) need complete redesign with no specified replacement. If it's preserved, Locked Decision #3 is violated in its most specific clause.

**CONTRADICTION-2: Monitor tool lock vs. Unavailable infrastructure (FATAL)**
- CONTEXT.md Locked Decision #1: "Persistent session + Monitor tool (Claude Code v2.1.98+)."
- PHASE2-PREP Q-MONITOR PM Recommendation: "Option A. Design for stateless spawn; treat Monitor tool as future enhancement."
- FEAT-PM-5613-MONITOR-RESEARCH.md conclusion: "Monitor cannot completely replace /loop. A hybrid model is required."
- CONTEXT.md Out of Scope: "Stateless spawn model — decided against."
- **Three-way contradiction.** The locked decision mandates a mechanism that (a) requires an unavailable version, (b) was previously determined insufficient by PM research, and (c) is contradicted by the PHASE2-PREP recommendation. Meanwhile, the alternative (stateless spawn) is explicitly ruled out in Out of Scope.

**CONTRADICTION-3: Event bus as sole mechanism vs. No persistence**
- CONTEXT.md: "Event bus becomes the sole agent activation mechanism."
- EventStream implementation (harness.py line 348): in-memory deque, max 1000 events, no disk persistence, lost on harness restart.
- The "sole activation mechanism" can't survive the most basic failure mode (harness restart).

**CONTRADICTION-4: Pure event-driven vs. Time-based scan triggering**
- CONTEXT.md Locked Decision #3: "Kill cycles entirely — pure event-driven."
- CONTEXT.md Locked Decision #5: "scan-due event on 10-minute idle timeout."
- Idle timeout = time-based polling, not event-driven. The scan-due trigger is a timer, which is a form of polling. A truly pure event-driven system wouldn't have time-based triggers — it would react to external state changes only. This is a minor philosophical contradiction but means the harness must have at least one polling loop (the idle timer), making the system hybrid, not "pure" event-driven.

**CONTRADICTION-5: All mechanical operations in harness vs. git operations complexity**
- CONTEXT.md: "Harness owns git pull... and git commit/push... Agent never runs git operations directly."
- cycle_post.py `_do_commit_push` (lines 297-412) contains 115 lines of role-specific git logic: branch workflow split commits (skill, lines 316-391), QA working-branch checkout (lines 392-402), state-branch commits (lines 410-412), auto-close sanitization (lines 254-266), disposable file detection (lines 275-294), PR creation with branch gymnastics (lines 347-374). The DM version bump (lines 415-464) is another 50 lines of git tag/commit/push logic.
- Absorbing all of this into harness means harness must understand role-specific git workflows. This creates tight coupling between harness and role behavior — exactly the kind of coupling the cycle runner architecture (#2057) was designed to reduce.

## Open Questions

- **Q1**: Which contradiction yields first — kill cycles (no cycle-output.json) or preserve cycle-output.json? — **Why**: The entire output contract design (event closure API schema, agent template writing, harness post-processing) depends on this. If cycle-output.json is killed, every role-specific extra needs a new home. If preserved, Locked Decision #3 must be revised.

- **Q2**: What is the actual Monitor tool API? — **Why**: The locked wake model depends entirely on this. Before Phase 2 begins, a human must upgrade Claude Code to v2.1.98+ and validate: (a) Monitor tool exists, (b) it can watch custom shell command output, (c) it supports reconnection after timeout, (d) multiple Monitors per session are possible. Without this validation, the entire Locked Decision #1 is speculative.

- **Q3**: How does the harness discover events for clone agents across sibling directories? — **Why**: event_bus_reader.py's parent-dir walk (`_discover_port` line 42-53) assumes clones are nested under primary. Per clone-isolation architecture, they're siblings. If event bus discovery fails for clones, agents silently receive no events — the sole activation mechanism is broken.

- **Q4**: What is the atomicity contract for event closure? — **Why**: If harness processes `POST /events/{id}/complete` and crashes mid-processing (after some git operations but before others), the event is partially processed. The re-emission strategy (CONTEXT.md dev discretion, line 51) depends on how much idempotency the closure callback provides.

- **Q5**: What drives the status bar display when cycles are eliminated? — **Why**: The status bar timer (statusline.sh lines 88-119) is based on `current-state` mtime. Without cycles, there's no concept of "time since last cycle." The status bar must either be redesigned or driven by event timestamps instead.

## Recommendation

**Needs rethinking.** The locked decisions contain two fatal contradictions (Monitor tool vs. unavailable infrastructure; kill cycles vs. preserve cycle-output.json) that block Phase 2 implementation. Before any code is written:

1. **Resolve the wake mechanism**: Either upgrade to Claude Code v2.1.98+ and validate Monitor tool API, OR revise Locked Decision #1 to stateless spawn (PHASE2-PREP Option A). The stateless spawn model is the only currently implementable path and doesn't require external version dependencies.

2. **Resolve the output contract**: Either revise Locked Decision #3 to preserve cycle-output.json (PHASE2-PREP Option A), OR design a replacement for all role-specific extras currently in cycle-output.json. This must be settled before template migration begins.

3. **Add event bus persistence**: The "sole activation mechanism" must survive harness restart. This is a Phase 2 prerequisite, not a future enhancement.

Phases 1 (continuous monitors), 3 (template stripping), and 4 (creative-only templates) are well-defined and implementable regardless of the wake mechanism chosen.

## Vault Candidates

- **Type**: learning — FEAT-PM-5613 already determined Monitor tool cannot replace /loop; #7630's locked decision ignored this finding — **Why**: Documents the risk of making architecture decisions contingent on unvalidated external tool capabilities. The Monitor tool research was done, concluded "no," but the lock happened anyway.
- **Type**: decision — Stateless spawn vs. persistent session trade-off for agent architecture — **Why**: The two models have fundamentally different reliability, latency, and complexity characteristics. This decision shapes the entire agent lifecycle design. Worth vaulting once settled.
- **Type**: pattern — Atomic template migration: all 24 manifests, 4 instructions, 6 sub-skills change in one deploy — **Why**: Already established as [[learning-atomic-migration-strategy]] but worth reinforcing with the specific scale of this migration (30+ files, cross-cutting).
- **Type**: learning — Event bus port discovery via parent-dir walk fails for sibling clones — **Why**: event_bus_reader.py's `_discover_port` assumes parent-child relationship. Clone isolation uses siblings. This is a latent bug that becomes critical when events are the sole activation mechanism. Worth documenting as a known architectural constraint.
- **Type**: decision — cycle-output.json is the stable interface between agent creative work and mechanical post-processing — **Why**: PHASE2-PREP Q2 correctly identifies this as "one of the most stable interfaces in the system." Preserving it across architectural shifts prevents cascading template redesigns. The role-specific extras (code_commit, pr_actions, version_bump, vault_writes) encode years of business logic that shouldn't be casually discarded.