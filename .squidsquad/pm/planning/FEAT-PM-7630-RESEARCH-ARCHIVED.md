# FEAT-PM-7630-v2 Research — Event-Driven Agent Architecture (Re-Research with Locked Decisions)

## Summary

This re-research validates the CONTEXT.md locked decisions against the actual codebase at `references/scripts/`. The human has doubled down on all six locked decisions (kill cycles, Monitor tool wake, event closure API, scan-due idle timeout, terminal cleanup, persistent session) and added four new prerequisites from the GAP-REVIEW (event bus disk persistence, clone event bus discovery fix, per-role in-flight queues, harness thread safety). **All 9 architectural gaps and 8 race conditions identified in the GAP-REVIEW are confirmed against the actual code.** The Monitor tool remains unvalidated — Claude Code v2.1.86 is installed, v2.1.98+ is required, and FEAT-PM-5613 previously concluded "Monitor cannot completely replace /loop." The architecture is internally consistent IF the Monitor tool exists, but the entire wake model lock depends on infrastructure that has not been validated.

**Primary risks**: (1) The wake model lock blocks Phase 2 until Monitor tool is validated. (2) Killing cycles entirely means absorbing ~1800 lines of battle-tested Python (cycle_pre.py 1058 lines, cycle_post.py 746 lines) into harness.py — this is a rewrite, not a refactor. (3) The event closure API contract (`POST /events/{id}/complete`) is zero-code — the event lifecycle, payload schema, idempotency strategy, and crash recovery are all undefined in code. (4) Template migration spans 24 includes.yml files, 25+ instructions.md files, and 6+ sub-skills — all must change atomically in one deploy.

**Recommendation**: Feasible with caveats. Phases 1 (continuous monitors) and 3 (template stripping) are straightforward regardless of wake mechanism. Phase 2 is blocked on Monitor tool validation. If Monitor tool isn't viable, the entire wake model lock must be revisited.

## Vault Context

- **BRIEFING.md priorities**: #7630 is the active top priority — "next major architectural shift — all mechanical cycle steps move to harness." Supersedes #6056, #5775, #5613.
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 split mechanical/creative; #7630 completes the transfer. [[decision-clone-isolation-architecture]] — agents run in sibling clones, not children; event bus port discovery must account for this. [[decision-pid-primary-liveness]] — OS-level truth preferred; aligns with PID checks.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — directly applicable: all cycle orchestration prose becomes harness code. [[pattern-windows-utf8-subprocess]] — Windows subprocess encoding handling applied in existing scripts.
- **Human preferences**: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose." Context pressure threshold: 70%. "Systems should self-heal: detect stuck states → unstick immediately." Prefers direct/mechanical checks over indirect state files.
- **Related learnings**: [[learning-commit-code-state-exclusion]] — original motivation for #2057; same class of problem. [[learning-atomic-migration-strategy]] — all templates, scripts, harness changes in one deploy.

## Impact Analysis

### Files touched (verified, not hallucinated)

**Core — major changes:**
- `references/scripts/harness.py` (1415 lines) — major expansion: event closure API (new `POST /events/{id}/complete` with payload schema, idempotency), scan-due idle timer (new `last_event_completed[role]` tracking, 10-min timeout thread), terminal PID tracking (new `terminal_pid` field in AgentState and `.harness-state.json`), per-role in-flight event queues, event bus disk persistence (new storage backend), thread safety fixes for `_update_agent_from_event` + `update_health`
- `references/scripts/cycle_pre.py` (1058 lines) — absorbed into harness continuous monitors (git pull, context pressure, triage, branch enforcement, cycle-input.json generation all move to harness)
- `references/scripts/cycle_post.py` (746 lines) — absorbed into harness event closure callback (commit/push, status transitions, tracker comments, iteration logging, version bumps, event cursor advancement)
- `references/scripts/event_bus.py` (103 lines) — new event types for work-dispatch (`work-available`, `work-started`, `work-completed`), lifecycle (`stop-requested`, `agent-stopping`, `agent-stopped`), scan (`scan-due`, `scan-completed`), diagnostics (`event-timeout`, `event-reemitted`, `work-failed`)
- `references/scripts/event_catalog.py` (216 lines) — 10+ new event types added to EMITTED tier (see event types below)
- `references/scripts/event_bus_reader.py` (89 lines) — may be superseded by Monitor tool or harness-pushed events; `_discover_port` parent-dir walk fix needed for sibling clones as prerequisite

**Agent lifecycle — moderate changes:**
- `references/scripts/boot_remote.py` (652 lines) — `_spawn_windows` (line 395), `_spawn_macos`, `_spawn_linux` must return terminal PID alongside agent PID; `boot_agent()` must store both
- `references/scripts/thin_launcher.py` (117 lines) — boot prompt changes from "Boot. Begin your first Ralph Loop cycle now." (line 86) to event-driven orientation; Monitor tool setup vs stateless spawn; return terminal PID
- `references/scripts/cycle.py` (300+ lines) — iteration log functions (`log-iteration`, `cleanup-iterations`) replaced by per-event log format; status-bar writing must switch from cycle-based to event-based state

**Config & state — moderate changes:**
- `references/scripts/config.py` (330+ lines) — new fields: `event-driven: yes/no`, `scan-idle-timeout: 10`, `wake-mechanism: monitor|spawn`; `FIELD_MAP` (lines 38-95) extended
- `references/scripts/harness.py` — `.harness-state.json` (line 285-313) extended: `terminal_pid`, `last_event_completed`, `in_flight_events`, `event_cursor` per role
- `references/scripts/tracker.py` (line 1069) — `comment()` function must accept `event_id` parameter for idempotent deduplication

**Templates — massive changes (all roles):**
- `references/sub-skills/common/cycle-runner.md` (93 lines) — **removed entirely** (replaced by event-driven workflow sub-skill)
- `references/sub-skills/common/context-pressure.md` (19 lines) — **removed** (absorbed by harness continuous monitor)
- `references/sub-skills/common/self-restart.md` (21 lines) — **removed** (absorbed by harness)
- `references/sub-skills/common/interval-sync.md` (13 lines) — **removed** (interval is harness config only)
- `references/sub-skills/common/event-reactions.md` (32 lines) — **rewritten** as event handler guidance (no more mechanical/creative split; agent just handles events)
- `references/sub-skills/common/agent-lifecycle.md` (46 lines) — **rewritten** for persistent session + Monitor tool wake
- `references/sub-skills/common/improvement-scan.md` (103 lines) — **trigger mechanism changed** (agent no longer self-triggers; harness emits `scan-due` event)
- `references/roles/dev/instructions.md` — ~60% content stripped (Ralph Loop steps, cycle markers, status bar cycle writes, `/loop` invocation at line 26-27 removed)
- `references/roles/pm/instructions.md` — ~60% content stripped (Ralph Loop steps, cycle markers, `/loop` invocation at line 15-16 removed)
- `references/roles/qa/instructions.md` — same
- `references/roles/dm/instructions.md` — same
- `references/roles/{dev,pm,qa,dm}/skill/instructions.md` — same (5 variant files each)
- `references/roles/{dev,pm,qa,dm}/{android,fullstack,ios,web}/{instructions.md}` — 16 domain variant files
- `references/roles/{dev,pm,qa,dm}/includes.yml` (4 base files) — remove 4-5 cycle-related includes each
- `references/roles/{dev,pm,qa,dm}/{skill,android,fullstack,ios,web}/includes.yml` (20 variant files) — same
- `references/roles/skill/includes.yml` — same (skill is a role variant)

**New files:**
- `references/sub-skills/common/event-driven-workflow.md` — new sub-skill: event handler descriptions ("when woken by event X, do Y, close event via API")
- Possibly `references/scripts/event_store.py` — disk-persistent event storage backend (dev discretion on format)
- Possibly `references/scripts/watcher_script.sh` — Monitor tool bridge script (polls GET /events for the agent)

**Not touched (confirmed out of scope):**
- `references/scripts/model_router.py` — unaffected
- `references/scripts/comms_adapter.py` — unaffected
- `references/scripts/forge_adapter.py` — unaffected
- `references/scripts/soul_adaptation.py` — unaffected
- `references/scripts/vault_*.py` — vault protocol unchanged, trigger mechanism changes only
- `references/scripts/squidsquad_cli.py` — unaffected
- `references/scripts/state_bus.py` — unaffected
- `references/scripts/git_ops.py` — indirect: git operations called from harness instead of cycle_post

### Behavior changes

1. **Agent activation**: Currently: `/loop [INTERVAL]m` in Claude Code re-invokes every N minutes → cycle_pre → creative work → cycle_post. After: Monitor tool watches event bus → harness emits work event → agent wakes, reads event context, does creative work, calls `POST /events/{id}/complete`.

2. **Mechanical operations ownership**: Currently split: cycle_pre.py handles git pull, context pressure, triage, branch enforcement; cycle_post.py handles commit/push, transitions, comments, iteration logs. After: harness owns ALL mechanical operations. Agent never runs git pull, commit, push, status transitions, or tracker comments directly.

3. **Cycle concept elimination**: Cycle numbers, cycle counters, iteration logs (`iter-{N}.md`), cycle-input.json, cycle-output.json, quiet-cycle counters, quiet-cycle detection — all gone. Replaced by event ID as the tracking unit and per-event log entries.

4. **Stop mechanism**: Currently: harness sets intent=stopping → cycle_post checks API at cycle end → exits with code 42. After: harness emits `stop-requested` event on event bus → Monitor tool detects it → agent checkpoints and exits cleanly. Unified channel (event bus) for both wake and stop.

5. **Improvement scanning**: Currently: agent prose decides when to scan (every quiet cycle, checking `Improvement Scanning` config). After: harness tracks `last_event_completed[role]` → emits `scan-due` after 10-min idle → PM is woken deterministically. Issue gate: harness checks for open issues before emitting.

6. **Terminal cleanup**: Currently: harness exit leaves terminal windows open (agents survive, line 1349: "Agents run in independent terminal windows — they survive harness exit"). After: on clean stop (`intent=stopping`), harness closes the terminal window via platform-specific mechanism (Windows: `taskkill /PID`, Unix: `kill`).

7. **Context pressure management**: Currently: agent reads context-pressure file each cycle (context-pressure.md, line 7-18), decides to checkpoint and continue. After: harness monitors context-pressure files from clones and triggers restart independently via intent=restarting.

8. **Git operations**: Currently: cycle_pre.py pulls, cycle_post.py commits and pushes. After: harness pulls before delivering work context, commits and pushes after processing event closure callback. Agent never runs git operations.

9. **Status bar**: Currently: `current-state` file shows cycle phases (pulling, triaging, implementing, committing, idle) written by agent each step. After: status bar driven by event state (idle/working), with event timestamps replacing cycle timers (statusline.sh lines 88-119).

### Dependencies

- **FastAPI + uvicorn** — already required by harness.py (line 52-61)
- **Claude Code v2.1.98+** — **critical new dependency** for Monitor tool; current install is v2.1.86; must be validated before Phase 2
- **Monitor tool API** — undocumented, unvalidated; the GAP-REVIEW lists 6 validation checklist items (CONTEXT.md lines 76-81)
- **New optional dependency**: disk-persistent storage backend for event bus (SQLite stdlib or filesystem only)
- **No new Python packages required** beyond what's already installed

## Side Effects

### Gaps Confirmed Against Codebase

- **GAP-1: Event closure API — zero code — Severity: H**: `POST /events/{id}/complete` does not exist. harness.py has only `POST /events` (line 814, receive_event) and `GET /events` (line 844). EventStream (line 348-384) has no concept of event lifecycle state (open/closed/dispatched). Mitigation: design and implement the endpoint, payload schema, atomicity contract, and idempotency strategy before any agent-facing changes.

- **GAP-2: Monitor tool unavailable — Severity: H**: Claude Code v2.1.86 installed; v2.1.98+ required. FEAT-PM-5613 concluded "Monitor cannot completely replace /loop." No Monitor tool invocation exists anywhere in codebase. Mitigation: human must upgrade Claude Code and validate Monitor tool API before prototyping Phase 2. If Monitor tool is insufficient, fall back to stateless spawn (PHASE2-PREP Option A).

- **GAP-3: scan-due idle timeout — zero code — Severity: H**: No `last_event_completed[role]` timestamp tracking in harness. No idle timeout monitor thread exists. Issue gate (skip scan if role has open bugs) requires querying GitHub Issues from harness — currently done by cycle_pre.py (lines 913-921) which will be removed. Mitigation: add timestamp tracking to AgentState (or `.harness-state.json`), implement idle-check thread in harness, port issue gate query logic.

- **GAP-4: Terminal PID not tracked — zero code — Severity: M**: thin_launcher.py writes only Claude PID (line 96). boot_remote.py `_spawn_windows` (line 395-440) spawns via `wt.exe` or `cmd /c start` — neither returns terminal window PID. AgentState has `claude_pid` (line 73) but no `terminal_pid`. `.harness-state.json` stores `claude_pid` (line 303) but no `terminal_pid`. On Windows, `wt.exe new-tab` creates a tab whose PID is not trivially correlated to the spawned process. Mitigation: modify `_spawn_windows`/`_spawn_macos`/`_spawn_linux` to capture and return terminal PID; add `terminal_pid` to AgentState and state file; implement platform-specific close logic.

- **GAP-5: Per-event log format — undefined — Severity: M**: Current iteration logs use `cycle.py log-iteration` (cycle_post.py lines 228-246) writing `iter-{N}.md`. No per-event log design exists. Historical audit trail spans both formats. Mitigation: define per-event log schema (event_id, event_type, timestamp, role, summary, outcomes) and implement migration path for existing iter-N.md files.

- **GAP-6: Event bus disk persistence — zero code — Severity: H**: EventStream is `collections.deque` with 1000-event cap (harness.py line 352). On harness restart, all events lost. The "sole agent activation mechanism" cannot survive a restart. Mitigation: implement disk-persistent event store (CONTEXT.md dev discretion: file-per-event, append-only log, or SQLite). Must include crash recovery: on harness restart, replay unclosed events.

- **GAP-7: Idempotent tracker comments — zero code — Severity: M**: tracker.py `comment()` (line 1069) has no `event_id` parameter. No dedup mechanism. If event re-emitted after crash, duplicate comments posted. Mitigation: add `event_id` parameter to `comment()`, implement dedup by event_id (skip if comment with same event_id exists on the issue).

- **GAP-8: Clone context-pressure monitoring — confirmed broken — Severity: M**: harness.py `GET /agents/{role}/health` (line 676-710) reads context-pressure from `SQUIDSQUAD_DIR / role / "context-pressure"` (line 704) — this is the PRIMARY repo's path (REPO_ROOT/.squidsquad/role/context-pressure). For clone agents, statusline.sh writes to the clone's path. Harness reads the wrong file for clone agents. Mitigation: use `agent.clone_path` to resolve context-pressure path for clone agents.

- **GAP-9: Per-role in-flight event queue — zero code — Severity: M**: No tracking of "dispatched but unclosed" events. EventStream has no concept of dispatch state. No per-role queue exists. Mitigation: add `in_flight: dict[role, event_id]` to HarnessState; gate event emission on no in-flight event for that role.

### Race Conditions Confirmed

- **RACE-1: Startup race — SERVER NOT READY**: harness.py lifespan (line 406-500): port file written (line 437-441), deferred_init thread launched (line 492) which auto-starts agents, but server doesn't accept connections until `yield` (line 495). Agents boot before server is ready. cycle_pre has 30-min interval so impact is low today, but event-driven agents would try to POST closure immediately and fail. Mitigation: ensure server is accepting before spawning agents, or add retry logic to closure POST.

- **RACE-2: Compose-completed → reboot race — confirmed**: harness.py `_do_merge` (line 1095-1172): emits `compose-completed` (line 1147-1151), then calls `_reboot_affected_agents` (line 1156) which sets intent=restarting. If an agent wakes on compose-completed before reboot executes, it reads stale templates. Mitigation: reboot first, then emit compose-completed as informational only.

- **RACE-3: Thread safety — confirmed**: `_update_agent_from_event` (line 737-757) called from `receive_event` (uvicorn thread, line 836) mutates AgentState fields (current_cycle, last_cycle_start, etc.) outside `HarnessState._lock`. `update_health` (line 155-262) reads AgentState fields under the lock but the object reference is returned and fields mutated outside. Mitigation: either move field mutations inside lock, or make AgentState fields atomic/thread-safe.

- **RACE-4: Event ID collision — confirmed**: event_bus.py `_generate_id` (line 58-61) uses SHA256 hash → 8-char hex. harness.py `_emit_event` (line 1010-1026) uses `os.urandom(4).hex()` (line 1017) → 8 random hex chars. Two different schemes with different collision properties. 4 bytes of randomness = ~65K events before birthday collision (within operational range). Mitigation: unify on one scheme; use SHA256 with more entropy (full hash or 12-char truncation).

- **RACE-5: Event cursor crash window — confirmed**: cycle_post.py `_advance_event_cursor` (line 588-630) advances cursor AFTER creative phase and AFTER commit/push. If harness crashes between agent POSTing closure and persisting "event closed," event replays on restart → duplicate work. Mitigation: persist "closed" before executing side effects (at-most-once), or make all side effects idempotent (at-least-once). CONTEXT.md dev discretion line 51.

- **RACE-6: Clone isolation event bus discovery — partially mitigated**: event_bus_reader.py `_discover_port` (line 27-55) has two paths: direct (SQUID_DIR/.harness-port, line 34-39) and parent walk (line 42-53). Harness distributes port files to clones in deferred_init (line 453-463), so direct path works IF harness has distributed. Parent walk fails for sibling clones. Risk: if harness crashes before distributing port files, or new clone added after harness start, agent silently receives `[]` from event queries (line 72-73 returns `[]`). Mitigation: ensure port distribution is reliable (retry on failure); consider using well-known port or environment variable as fallback.

- **RACE-7: Shutdown event loss — confirmed**: harness shutdown (line 926-1003) sets intent=stopping, waits for agents, then kills. Events emitted during grace period are stored but no agent exists to process them. On restart, stale events could trigger duplicate work. Mitigation: mark all in-flight events as "abandoned" on shutdown; filter abandoned events on restart.

- **RACE-8: File-based wake TOCTOU — speculative**: If Monitor tool watches files (not confirmed), and harness writes trigger files, Windows file locking may cause TOCTOU. Mitigation: use atomic writes (.tmp → mv) as statusline.sh already does (line 72); validate Monitor tool's Windows file watching behavior.

### Failure Modes

- **Harness crash during event processing**: `.harness-state.json` (line 293-306) stores PID, intent, boot_time, clone_path, claude_pid — but NOT in-flight event IDs, dispatch state, or `last_event_completed` timestamps. On restart, harness has no record of dispatched-but-unclosed events. Agent may be mid-work but harness doesn't know. Mitigation: extend state file to include event dispatch state; on restart, query agents for active event status.

- **Agent crash mid-event**: Health polling (5s, line 44) detects dead agent via PID check. Cannot distinguish "crashed mid-event" from "working on long task." No timeout mechanism exists. CONTEXT.md specifies: short tasks (scan, comment) = 5 min, long tasks (implementation) = 60 min. Mitigation: implement event-type-specific timeouts in harness; on timeout, diagnose (check PID, context pressure), decide (respawn, re-emit, alert).

- **Monitor tool disconnection**: 5613-RESEARCH says "1-hour max Monitor timeout." During reconnection gap, events emitted to role are missed. In-memory deque has no per-role buffering. Mitigation: with disk-persistent event bus, events survive reconnection gaps; agent reconnects and queries `GET /events?since=<last_processed>`.

- **Git operation failure during closure**: If `git push` fails in closure callback, event processed but code not pushed. cycle_post.py has complex error handling for this (lines 325-343: "Nothing to commit" detection, branch verification). Mitigation: replicate error handling in harness closure callback; event closure = committed+pushed, not just processed.

- **Stop signal delivery failure**: If Monitor tool disconnected (timeout), agent never sees `stop-requested` event. No fallback mechanism. Mitigation: sentinel file fallback (`.stop-requested`) as secondary channel; harness writes sentinel + emits event.

- **Event bus overflow**: 1000-event max (harness.py line 352). At high event rates, old events silently evicted. If agent's cursor references evicted event, `get_since` returns oldest available (line 380) causing re-delivery. Mitigation: disk persistence removes memory cap; implement cursor validation to detect eviction.

### Windows-Specific Risks

- **File locking on context-pressure reads**: statusline.sh writes via `.tmp` → `mv` (atomic). Python `Path.read_text()` on Windows uses sharing modes that may conflict with bash redirects. Mitigation: retry reads with backoff; use `share_mode` flags in Python file opens.

- **PID reuse window**: Windows PID reuse faster than Unix. 5-second health poll interval may miss a death-and-reuse cycle. `.claude-pid` file adds second factor but is only read at health check time, not continuously verified. Mitigation: store process start time alongside PID for disambiguation; verify process name matches expected.

- **Terminal window tracking on Windows**: `wt.exe new-tab` (line 401) spawns a tab; the spawned process (python thin_launcher.py) is a child of wt.exe, but wt.exe's PID is not returned. `cmd /c start` (line 425) creates console via conhost.exe — relationship not tracked. `taskkill /PID` kills process but cannot specifically close terminal window without killing agent. Mitigation: on Windows, use `wt.exe --window` to target specific terminal; or accept that terminal cleanup on Windows may be best-effort only.

- **Signal handling**: Windows no SIGTERM. harness Ctrl+C escalation (line 1294-1355) uses SIGINT only. No cross-platform way to send graceful stop signal to Claude Code process. If Claude Code hangs, no interrupt short of `taskkill /F`. Mitigation: file-based stop signal (event bus stop-requested) is already the design; ensure agent templates include periodic stop-event checks.

- **Detached process flags**: `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (line 414) means child has no console attachment. Harness cannot signal detached processes. Mitigation: this is by design (agents survive harness exit); stop mechanism must be cooperative (agent checks for stop event).

## Edge Cases

- **Zero events for role on first boot**: Agent boots, Monitor tool watches event bus, no events exist. Agent sits idle — correct behavior, but must not appear stalled. Mitigation: harness emits `agent-ready` event on first boot confirmation; agent acknowledges with initial health check.

- **Event arrives while agent is closing previous event**: Agent mid-POST to `/events/{id}/complete` when new event arrives. Mitigation: agent processes one event at a time; harness queues events per role (GAP-9 prerequisite); agent queries for next event after closure completes.

- **Agent issues tracker commands during creative work**: Under event-driven model, agent should NOT run tracker transitions or comments directly — those go through closure API. But agent may still have bash access. Mitigation: prohibitions sub-skill updated to forbid direct tracker/git operations; harness closure API is the only path.

- **Human sends message mid-event**: Currently: PM checks human input each cycle. After: human input becomes an event (`human-input-received`). Mitigation: harness must detect human messages (GitHub issue comment, discussion post) and emit events. This is a new event source not covered by current event catalog.

- **Subagent spawn during event processing**: dev instructions.md line 17: "spawning subagents via the Agent tool." Subagent work is agent-initiated within a single event. No subagent-start/subagent-complete event type exists. Mitigation: subagent work is internal to the agent's event processing; no event type needed unless subagent failure should be visible to harness.

- **Config flag `event-driven: no` while old cycle code removed**: Once cycle_pre/cycle_post are removed from templates and agents, the old model cannot run. Mitigation: config flag gates behavior, but old code must remain in codebase (not in templates) until migration is complete and validated.

- **Mixed-mode team**: If PM on event-driven, dev on cycles: PM emits `verification-failed` event — dev won't see it until next cycle_pre (up to 30-min delay). Mitigation: cross-role event-driven detection; warn on mixed-mode; gating must be per-team, not per-role.

## Integration Risks

- **Tracker protocol**: cycle_post.py currently handles all status transitions and tracker comments. Absorbing into harness means harness must understand role-specific transition rules. The cycle-runner.md role-specific extras (lines 73-92: code_commit, pr_actions, vault_writes, version_bump, human_input_processed, issues_filed, etc.) represent years of accumulated business logic that must be preserved in the closure API payload schema.

- **Compose integration**: Currently: compose emits `compose-completed` → harness reboots affected agents. Under event-driven: compose emits event → agents with changed templates get `templates-updated` event → agent checkpoints and exits → harness respawns with new templates. The reboot-then-event ordering (RACE-2) must be fixed.

- **PR merge flow**: harness.py `/merge` (line 1068-1176) already handles PR merging asynchronously. This is close to the event-driven model already. The merge result (`pr-merged` event) would be consumed by agents via event bus rather than via cycle_pre's `recent_events`.

- **Vault operations**: Out of scope per CONTEXT.md, but trigger mechanism changes. Currently: agent checks vault counters each cycle. After: harness emits `vault-reflect` event when vault state changes. No `vault-reflect` event type exists in event_catalog.py.

- **Git branch enforcement**: cycle_pre.py `_enforce_branch` (line 980) ensures correct branch before pull. This must move to harness and run before delivering work context. Branch workflow (feature branches, PR lifecycle) must remain functional.

- **Status bar**: statusline.sh (line 88-119) uses `current-state` file mtime for cycle timer. With no cycles, this must be redesigned to use event timestamps. The status bar's cycle-based display (iteration number, quiet cycle count) needs new event-based equivalents.

- **Health check legacy fallback**: health_check.py is deprecated (#4966) but still used as fallback in harness.update_health() (lines 201-214). Under event-driven, health_check.py should be fully removed — harness uses direct PID checks only.

## Upgrade & Migration

- **New config values**:
  - `event-driven: no` (default `no`; must be explicitly set to `yes` to activate)
  - `scan-idle-timeout: 10` (minutes, default `10`)
  - `wake-mechanism: monitor` (default `monitor`; future: `spawn` fallback)
  - These must be added to `config.py` FIELD_MAP (line 38-95)

- **New files**:
  - `references/sub-skills/common/event-driven-workflow.md` — new sub-skill
  - Possibly `references/scripts/event_store.py` — disk-persistent event storage
  - Possibly `references/scripts/watcher.sh` — Monitor tool bridge script
  - New `.squidsquad/.harness-state.json` fields (automatic, no manual creation)

- **Template changes**: 24 includes.yml files remove `common/cycle-runner`, `common/context-pressure`, `common/self-restart`, `common/interval-sync` includes. 4 base instructions.md files strip ~60% content (Ralph Loop steps, cycle markers, `/loop` invocation, status bar cycle writes). 4 new variant instructions.md files same treatment. 1 new sub-skill added (`event-driven-workflow.md`). All changes must be atomic — one compose deploy-all.

- **Upgrade steps**:
  1. Human upgrades Claude Code to v2.1.98+ and validates Monitor tool API
  2. Set `event-driven: yes` in config.md
  3. Set `wake-mechanism: monitor` and `scan-idle-timeout: 10`
  4. Run `python references/scripts/compose.py deploy-all` to regenerate all CLAUDE.md files
  5. Restart harness (`python references/scripts/harness.py`)
  6. Harness detects `event-driven: yes` and switches to event-driven mode (continuous monitors, event bus activation)
  7. Agents boot with new templates (no `/loop`, event-driven workflow)
  8. Monitor tool watches event bus; agents process events as they arrive

- **Graceful degradation**: When `event-driven: no` (default), existing cycle model runs unchanged. Both models cannot run simultaneously for the same role. Cross-role detection needed: if one role is event-driven and another is cycle-based, warn on harness startup. Rollback: set `event-driven: no`, `compose.py deploy-all`, restart harness.

- **N/A for pre-public** — no existing users to migrate. The feature is gated behind a config flag.

## Open Questions

- **Q1: Does Monitor tool exist and work as assumed?** — **Why**: The entire wake model lock (Persistent session + Monitor tool) depends on this. Before Phase 2 code is written, human must: (a) upgrade Claude Code to v2.1.98+, (b) verify Monitor tool can watch custom shell command stdout, (c) verify multiple subscriptions per session, (d) verify Windows behavior, (e) measure actual wake latency. If Monitor tool is insufficient, the wake model must be revised to stateless spawn (PHASE2-PREP Option A).

- **Q2: What is the event closure API payload schema?** — **Why**: The output contract replaces cycle-output.json. Must include all role-specific extras currently in cycle-runner.md lines 73-92 (code_commit, pr_actions, vault_writes, version_bump, human_input_processed, issues_filed, etc.). If the schema doesn't capture these, role-specific business logic is lost. If it over-captures, the "agent describes outcomes in natural language" goal is undermined.

- **Q3: At-most-once vs at-least-once for event closure?** — **Why**: If harness persists "closed" before executing side effects (git commit, tracker comment, status transition), a crash after persist but before execution loses work permanently (at-most-once). If harness executes side effects first, then persists "closed," a crash causes duplicate work (at-least-once). The idempotency strategy (CONTEXT.md line 51, dev discretion) depends on which atomicity model is chosen.

- **Q4: How does the status bar work without cycles?** — **Why**: statusline.sh lines 88-119 use `current-state` file mtime for cycle timer and `iter-N.md` files for cycle count. Without cycles, the status bar must display event-based state: idle time, last event type, event count. This requires statusline.sh changes not in scope of CONTEXT.md.

## Recommendation

**Feasible with caveats.** Phases 1 (continuous monitors), 3 (template stripping), and 4 (creative-only templates) are well-defined and implementable regardless of wake mechanism. Phase 2 (event-driven wake + closure) is blocked on two unresolved dependencies:

1. **Monitor tool validation** — Upgrade Claude Code to v2.1.98+ and validate the Monitor tool API before writing any Phase 2 code. If Monitor tool fails validation, fall back to stateless spawn (PHASE2-PREP Option A), which requires revising Locked Decision #1.
2. **Event closure API design** — The payload schema must preserve all role-specific extras from cycle-runner.md lines 73-92. The atomicity contract (at-most-once vs at-least-once) must be settled before implementation.

The four new prerequisites from the GAP-REVIEW (event bus disk persistence, clone event bus discovery fix, per-role in-flight queues, harness thread safety) are valid and should be implemented as Phase 1.5 — infrastructure work that benefits both old and new models and can proceed in parallel with Monitor tool validation.

## Vault Candidates

- **Type**: learning — FEAT-PM-5613 already determined Monitor tool cannot replace /loop; #7630's locked decision ignored this finding — **Why**: Documents the risk of locking architecture decisions on unvalidated external dependencies. The Monitor tool research was done, concluded "no," but the lock happened anyway. Important for future decision-making discipline.
- **Type**: pattern — Atomic template migration at scale: 24 includes.yml + 4 instructions.md + 6 sub-skills + compose.py in one deploy — **Why**: Already established as [[learning-atomic-migration-strategy]] but worth reinforcing with this specific scale (30+ files, all roles, cross-cutting). The compose.py `deploy-all` command enables this but the coordination complexity is material.
- **Type**: decision — Event closure API as the new stable interface between agent creative work and harness mechanical post-processing — **Why**: Replaces cycle-output.json (one of the most stable interfaces since #2057). The design choices here (payload schema, atomicity contract, idempotency strategy) will shape all future agent-template development. Worth vaulting once settled.
- **Type**: learning — cycle-output.json role-specific extras encode years of business logic that must survive architectural transitions — **Why**: code_commit, pr_actions, vault_writes, version_bump, human_input_processed, issues_filed, etc. (cycle-runner.md lines 73-92) are not incidental — they are the system's delivery contract. Any replacement must preserve them with fidelity. This learning applies to future architectural shifts.
- **Type**: learning — Event bus port discovery via parent-dir walk fails for sibling clones but harness port distribution mitigates this — **Why**: event_bus_reader.py `_discover_port` has two paths: direct (works if harness distributed) and parent walk (fails for siblings). This is a latent architectural constraint worth documenting. The harness distribution is a workaround, not a fix — any new event bus consumers must be aware of this limitation.