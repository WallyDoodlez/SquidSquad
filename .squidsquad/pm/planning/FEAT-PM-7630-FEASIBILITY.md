Now I have a thorough understanding of the codebase. Let me compile the feasibility audit.

```markdown
# FEAT-PM-7630-FEASIBILITY-v2 Research — Event-Driven Agent Architecture

## Summary

This research assesses the gap between the current cycle-based SquidSquad architecture (harness.py, cycle_pre/post.py, in-memory event stream, /loop-driven agents) and the target 5-event L1 model described in the PRD and CONTEXT. The event bus infrastructure (#4709, #5622, #5868, #6126) is ~70% built: harness has POST/GET /events endpoints, cursor-based consumption, per-role filtering, and a bounded in-memory EventStream. What's missing is the event lifecycle management (ack processing, timeout/re-emit/escalation, disk persistence), the external activity detector, the Monitor-tool-based wake mechanism (event_poll.py), template migration away from cycle-runner/event-reactions, and terminal PID tracking for clean shutdown.

**Recommendation**: Feasible with caveats. The biggest risk is Monitor tool validation — the entire wake model depends on a Claude Code feature (v2.1.98+) that hasn't been validated in this codebase. The phased approach (loop stays alive until final phase) mitigates this: Phase 1.5 infrastructure can ship without touching agent behavior, Phase 2 event infrastructure can coexist with /loop, and Phase 3 templates switch agents over. Phase 4 removes /loop after validation.

**Primary risks**: (1) Monitor tool API unknown — sub-second wake latency assumption unvalidated on Windows. (2) Ack timeout tuning for long-running work — false-positive death declarations could kill productive agents. (3) Event bus is in-memory only — harness crash loses all events; disk persistence is Phase 1.5 P-1. (4) External activity detector must filter SquidSquad's own changes perfectly to prevent event loops.

## Vault Context

- **BRIEFING.md priorities**: #7630 EPIC is the active top priority — "all mechanical cycle steps move to harness." Supersedes #6056, #5775, #5613.
- **Related decisions**: [[decision-cycle-runner-architecture]] — cycle_pre/post split (#2057) was intermediate step; #7630 completes the transfer of all mechanical operations to harness. [[decision-pid-primary-liveness]] — OS-level PID checks as primary liveness; ack-based health monitoring extends this pattern to event-driven form. [[decision-self-healing-sentinel]] — two-tier self-healing (immediate unstick → root-cause bug) applies to ack timeout → retry → kill → reboot → escalate flow. [[decision-watchdog-supervisor]] — guidance on thread vs. separate process for monitors; external activity detector starts as harness thread, may graduate. [[decision-clone-isolation-architecture]] — agents in sibling clones; port discovery fix (P-2) must account for this.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — all cycle orchestration prose moves to harness code; this is the fundamental pattern driving #7630.
- **Human preferences**: Cyclic/mechanical work must be programmatic, not LLM prose. PID-first liveness. Context pressure threshold 70%. Prefers direct OS checks over state files. Primary platform: Windows 11.
- **Related learnings**: [[learning-atomic-migration-strategy]] — all templates, scripts, harness changes in one deploy. [[learning-commit-code-state-exclusion]] — original motivation for #2057 mechanical/creative split.

## Impact Analysis

- **Files touched**:
  - **harness.py** (`references/scripts/harness.py`, ~1429 lines): Add ack processing to existing POST /events (line 827); new EventLifecycleManager class (~180 lines); external activity detector (~120 lines); modify save_state/load_state for event_state persistence (lines 298, 328); extend AgentState slots for in_flight_events, last_wake_at, idle_since, terminal_pid (line 71); per-role event queue management; thread safety hardening.
  - **event_bus.py** (`references/scripts/event_bus.py`, 104 lines): Add `ack(event_id, role)` function (~20 lines) for POSTing ack events; add disk outbox fallback for harness-unreachable scenarios.
  - **event_bus_reader.py** (`references/scripts/event_bus_reader.py`, 90 lines): Simplify `_discover_port()` to remove parent-dir walk (Phase 1.5 P-2); otherwise no functional changes.
  - **event_catalog.py** (`references/scripts/event_catalog.py`, 218 lines): Replace RECOGNIZED tier (currently: verification-failed, verification-passed, agent-health, phase-change, request-merge) with 5 L1 types: assigned-to, stop-requested, shipped, version-bump, ack. Keep EMITTED tier unchanged (harness-internal observability).
  - **event_validator.py** (`references/scripts/event_validator.py`, 260 lines): Update `check_hallucinated_events` to validate against new 5-event RECOGNIZED tier. The validator's `check_missing_consumers` and `check_orphaned_emits` checks remain structurally unchanged.
  - **cycle_pre.py** (`references/scripts/cycle_pre.py`, ~1060 lines): Retained during development phases. Removed in Phase 4.
  - **cycle_post.py** (`references/scripts/cycle_post.py`, ~747 lines): Retained during development phases. Removed in Phase 4.
  - **event_poll.py** (`references/scripts/event_poll.py`): **NEW** — ~30-line HTTP poll script for Monitor tool. Queries `GET /events?since=<cursor>&role=<role>`, outputs JSON events to stdout. Reads `.harness-port` from local `.squidsquad/`.
  - **thin_launcher.py** (`references/scripts/thin_launcher.py`, 118 lines): Change boot prompt at line 86 from `"Boot. Begin your first Ralph Loop cycle now."` to event-driven orientation referencing Monitor tool and event_poll.py. Return terminal PID on Windows (subprocess.Popen on line 79 currently only tracks claude PID).
  - **boot_remote.py** (`references/scripts/boot_remote.py`, 653 lines): `_spawn_windows` (line 395), `_spawn_macos` (line 443), `_spawn_linux` (line 494) must return terminal PID alongside spawn success. `_find_boot_script` (line 346) already prefers thin launcher.
  - **config.py** (`references/scripts/config.py`, 575 lines): Add 5 FIELD_MAP entries (after line 95) for event-timeout-minutes, event-max-retries, event-poll-interval, event-queue-cap, scan-cooldown. `get_event_reactions` (line 213) will eventually be deprecated but retained for backward compat during phases.
  - **compose.py** (`references/scripts/compose.py`): Template changes auto-propagate; `derive_event_contract` must work with new 5 event types.
  - **config.md** (`.squidsquad/config.md`): Replace `## Event Reactions` section (lines 132-148) with new `## Event Driven` section. Old event reactions section references verification-failed, verification-passed, agent-health — all removed.
  - **Sub-skills**:
    - **NEW**: `references/sub-skills/common/event-driven-workflow.md` — replaces cycle-runner.md and event-reactions.md
    - **DELETED**: `references/sub-skills/common/event-reactions.md` (28 lines, old per-event-type table)
    - **DELETED**: `references/sub-skills/common/cycle-runner.md` (~200 lines, 3-phase mechanical/creative/post flow)
    - **DELETED (Phase 4)**: `common/context-pressure.md`, `common/interval-sync.md`, `common/self-restart.md`, `common/boot-remote-agents.md`
  - **includes.yml**: All 4 base roles (`references/roles/{dev,pm,qa,dm}/includes.yml`) plus 20 variant includes — replace cycle-runner + event-reactions with event-driven-workflow; remove context-pressure, interval-sync, self-restart, boot-remote-agents.
  - **Tests**: ~15 files touched across test_event_catalog, test_event_bus, test_event_bus_reader, test_event_validator, test_event_config, test_event_derivation, test_harness, test_cycle_pre, test_cycle_post, test_feat_6126, test_thin_launcher, test_start_team, test_compose, test_config, test_config_functions.

- **Behavior changes**:
  1. Agents no longer self-loop via `/loop` — harness delivers events, agents wake via Monitor tool + event_poll.py
  2. Agents sit idle (persistent Claude session alive) until harness delivers events
  3. Harness owns all "should I work?" decisions — external activity detection, event dispatch
  4. Ack-based closure: agent emits `ack {event_id}` via POST /events after any event
  5. Ack-based health monitoring replaces PID polling — no ack within timeout → retry → kill → reboot
  6. cycle_pre.py and cycle_post.py absorbed into harness (event-driven mode)
  7. No config gate (event-driven is the only mode) — per Locked Decision 3
  8. Scan: agent self-initiates per 15-min cooldown when idle — no scan-due event

- **Dependencies**:
  - Claude Code v2.1.98+ with Monitor tool (unvalidated — Locked Decision prerequisite)
  - Existing FastAPI + uvicorn (already in harness.py)
  - Existing event bus infrastructure (#4709, #5622, #5868, #6126)
  - GitHub API access for external activity detector (requires gh CLI or PAT)
  - Harness lifecycle management (#4966) — already shipped

## Side Effects

- **Risk 1**: Monitor tool is sole wake mechanism — if it has limitations (1-hour timeout, single subscription, Windows quirks), entire architecture degrades — Severity: H — Mitigation: Validate Monitor tool API checklist (CONTEXT.md lines 128-136) before Phase 2 prototyping. The phased plan keeps /loop alive as fallback until Phase 4.
- **Risk 2**: Ack timeout false-positive — agent working on long task (e.g., large PR review), doesn't ack within timeout, harness kills productive agent — Severity: H — Mitigation: Generous default timeout (10 min, configurable). Agent can send interim heartbeat ack. Harness checks PID via OS before killing (TC-9).
- **Risk 3**: Agent terminal idle for long periods — human observes blank terminal, thinks agent is dead — Severity: M — Mitigation: Status line shows "idle — waiting for events" with timestamp. Harness console shows agent states. Monitor tool continues watching.
- **Risk 4**: Harness crash while events in-flight — in-memory EventStream (harness.py line 361, collections.deque) loses all events — Severity: H — Mitigation: Phase 1.5 P-1 adds disk persistence (.event-state.json). Atomic writes on every state change.
- **Risk 5**: External activity detector reacts to SquidSquad's own GitHub changes → event loop (Locked Decision 9) — Severity: H — Mitigation: Filter by squidsquad label and agent commit prefix pattern (`skill:`, `pm:`, `qa:`, `dm:`). Test with TC-12, TC-13.

## Edge Cases

- **No events for long periods**: Agent sits idle — Monitor tool watching event_poll.py stdout, status line shows "idle." No cycle logs written. Correct behavior. Harness does NOT emit periodic heartbeats (not in 5-event model).
- **Event storm (many events simultaneously)**: Per-role in-flight queue capped at 50 (configurable). Events 51+ dropped with counter increment. Agent processes one event at a time (atomic). Monitor tool naturally queues notifications.
- **Agent crashes mid-work**: Harness detects via ack timeout (no PID polling needed). After max retries: kills PID, reboots agent via thin_launcher, re-emits event to rebooted agent. Rebooted agent reads working-state.md for checkpoint resume.
- **Ack timeout**: Event re-emitted with retry_count++. After max retries (default 3), harness declares agent dead, kills PID, reboots, re-emits. If reboots also fail, escalates to PM (self-healing tier 2, per [[decision-self-healing-sentinel]]).
- **Clone isolation**: Agent clones may not share filesystem with harness. event_poll.py reads `.harness-port` from local `.squidsquad/` directory (distributed by harness at boot, harness.py line 465-477). No parent-dir walk needed. Ack also uses HTTP API.
- **Multi-agent broadcast**: announced events (shipped, version-bump) dispatched to all agents. Each agent acks independently — harness does NOT wait for all acks. No multi-consumer tracking (Locked Decision 12).
- **Duplicate ack**: Idempotent — harness processes first ack, ignores duplicates (Locked Decision 13).

## Integration Risks

- **Compose/deploy integration**: Changing sub-skills and includes.yml (24 files) requires compose.py deploy-all. Event contract derivation (#5868, `derive_event_contract` in compose.py) validates against event_catalog — must work with new 5 event types. Old `## Event Reactions` config section is parsed by `get_event_reactions()` (config.py line 213) and fed to event_validator.py — these checks become no-ops if section is empty/absent.
- **Harness merge (#6126)**: Harness already owns PR merge (POST /merge, line 1081). Merge emits pr-merged and compose-completed events (harness-internal only). After event-driven migration, merged code that changes references/ must still trigger compose + agent reboot. The `_reboot_affected_agents` function (line 1192) uses intent-based restart — must emit stop-requested + restart in event-driven model instead.
- **Tracker authority**: tracker.py emits status-transition and tracker-comment events (EMITTED tier). These remain harness-internal observability only — not delivered to agents. External activity detector replaces agent-initiated tracker polling in cycle_pre.py.
- **Config.md versioning**: New `## Event Driven` section must be added. Pre-upgrade configs (without this section) must default gracefully — all 5 fields use sensible defaults (TC-39). Old `## Event Reactions` section is silently ignored in event-driven mode.
- **Windows ProactorEventLoop**: harness.py runs FastAPI on uvicorn with asyncio. Adding EventLifecycleManager threads and external activity detector thread may surface Windows-specific asyncio pipe exceptions (known project risk). Already worked around for health poller; new threads need same treatment.

## Upgrade & Migration

- **New config values**: 5 fields in new `## Event Driven` section:
  - `event-timeout-minutes`: 10 (default)
  - `event-max-retries`: 3 (default)
  - `event-poll-interval`: 30 (default)
  - `event-queue-cap`: 50 (default)
  - `scan-cooldown`: 15 (default)
- **New files**:
  - `references/scripts/event_poll.py` — HTTP poll script for Monitor tool
  - `references/sub-skills/common/event-driven-workflow.md` — replaces cycle-runner.md and event-reactions.md
  - `.squidsquad/.event-state.json` — disk-persisted event state (created at harness startup)
- **Template changes**:
  - **Removed sub-skills**: `common/cycle-runner`, `common/event-reactions`, `common/context-pressure`, `common/interval-sync`, `common/self-restart`, `common/boot-remote-agents`
  - **Added sub-skills**: `common/event-driven-workflow`
  - **Role instructions.md** (4 base roles): Remove all Ralph Loop references, /loop invocation, cycle numbering. Replace with Monitor tool + event_poll.py guidance.
  - **Role SOUL.md** (4 base roles): Remove "You follow the Ralph Loop" — replace with "You react to events dispatched by the harness."
  - **Agent-instructions.md**: Regenerated via compose.py deploy-all
  - **config.md**: Old `## Event Reactions` section removed; new `## Event Driven` section added
- **Upgrade steps**:
  1. Stop all agents (`start_team.py --stop --all` or Ctrl+C harness)
  2. Pull latest code containing #7630 changes
  3. Run `python references/scripts/compose.py deploy-all` — regenerates all CLAUDE.md + SOUL.md
  4. Clean stale sentinel files from clone directories
  5. Start harness — auto-spawns agents in event-driven idle mode
- **Graceful degradation**: Pre-upgrade config.md (no `## Event Driven` section) loads all 5 fields with defaults. Old `## Event Reactions` section is silently ignored. Harness starts without error. All new config fields accessible via `config.py get <field>`.

## Open Questions

- **Q1**: Has the human upgraded Claude Code to v2.1.98+ and validated the Monitor tool API? — **Why**: The entire wake model depends on this. If Monitor tool doesn't support custom command stdout watching, has hard timeout limits, or doesn't work on Windows, the architecture must pivot to stateless spawn (PHASE2-PREP Option A). Validate before Phase 2.
- **Q2**: How does the external activity detector authenticate to GitHub? — **Why**: The detector polls GitHub API. If `gh` CLI is already authenticated (standard SquidSquad setup), reuse that. If not, a PAT must be configured. The detector needs rate-limit handling (TC-15).
- **Q3**: What happens to existing `.harness-state.json` fields (`current_cycle`, `last_cycle_start`, etc.) after migration? — **Why**: These are cycle-specific AgentState slots (harness.py lines 95-99). They become vestigial in event-driven mode. Keep for backward compat during phases, remove in Phase 4 cleanup.
- **Q4**: Should `cycle.py` (287 lines, timestamp/status-bar/iteration-log utilities) be renamed or kept? — **Why**: PRD says "no changes — still used for timestamps, status-bar, iteration-log." But "cycle" naming is legacy. Dev discretion (CONTEXT.md line 109) allows rename. Small PR later.

## Recommendation

**Feasible with caveats**. The infrastructure is 70% built. The remaining 30% is substantial but well-understood: event lifecycle management, external activity detection, template migration, and Monitor tool integration. The phased rollout strategy (loop stays alive until Phase 4) provides safe incremental delivery with each phase independently testable. The biggest unknown — Monitor tool validation — must be resolved before Phase 2 implementation begins.

---

## High-Level Phased Dev Plan

### Phase 1: Prerequisites (L — ~3 dev sessions)
**Goal**: Infrastructure hardening. Zero agent behavior change. /loop continues working normally.

| # | Change | Current State | What Changes | Reuse vs Rewrite | Complexity | Risk |
|---|--------|--------------|-------------|-----------------|------------|------|
| P-1 | **Event bus disk persistence** | `EventStream` (harness.py:361) is in-memory `collections.deque` (max 1000). Crash = all events lost. | Add `.squidsquad/.event-state.json`. New `EventLifecycleManager` class with `persist()`/`load()`. Modify `save_state()` (line 298) and `load_state()` (line 328) to include event_state. | New class (~180 lines). Existing `save_state`/`load_state` extended, not rewritten. | L | M — corrupt state file on crash if not atomic |
| P-2 | **Clone event bus discovery fix** | `_discover_port()` in event_bus.py:28 and event_bus_reader.py:27 walks parent dirs. Clone isolation uses sibling dirs — walk fails. | Simplify both `_discover_port()` to check direct `.squidsquad/.harness-port` only. Harness already distributes port file to clones (harness.py:465-477). Remove parent-dir walk (lines 41-53 in both files). | Reuse 90% — remove ~12 lines from each file, keep direct-path logic. | S | L — clone agents silently received zero events before |
| P-3 | **Per-role in-flight event queue** | All events go into single `EventStream` deque. No per-agent tracking. `AgentState.__slots__` (harness.py:71) lacks in_flight_events, last_wake_at, idle_since. | Add `in_flight_events: list[str]`, `last_wake_at`, `idle_since` to AgentState slots. Add `EventLifecycleManager._role_queues` dict. Cap at event-queue-cap (50). | Extend existing AgentState (3 new slots). New queue dict in EventLifecycleManager. | M | L — slot additions are backward compat |
| P-4 | **Harness thread safety** | `HarnessState._lock` (line 125) protects agents dict. `EventStream._lock` (line 366) protects deque. `save_state()` snapshots under `_lock`. `update_health()` (line 155) mutates AgentState outside lock for some fields. | Audit all lock paths. Ensure `update_health()` mutations are under lock. Review `_update_agent_from_event` (line 750) for lock coverage. Add `EventLifecycleManager` lock for dispatch/ack. | Extend existing locking — no rewrite. | M | M — race conditions are subtle |
| P-5 | **Terminal PID tracking** | `_spawn_windows` (boot_remote.py:395) spawns via `subprocess.Popen` but doesn't return terminal PID. `_spawn_macos` (line 443) and `_spawn_linux` (line 494) same gap. Harness can't close terminal windows on clean stop (Locked Decision 6). | `_spawn_windows` returns `(success, message, terminal_pid)`. On Windows via wt.exe, the terminal PID is the wt.exe process PID from Popen. Store in AgentState as `terminal_pid`. | Modify return signature of 3 spawn functions. Reuse 95% of existing spawn code. | M | M — Windows terminal PID tracking via wt.exe is indirect |
| P-6 | **Add terminal_pid to AgentState + persistence** | `AgentState.__slots__` (line 71) lacks `terminal_pid`. `save_state` (line 298) doesn't persist it. | Add `terminal_pid` slot. Include in `to_dict()` (line 101) and `save_state()` agent snapshot. Load in `load_state()`. | Extend existing — 4 lines added. | S | L |

**Phase 1 test coverage**: TC-31 through TC-37, TC-39, TC-45, TC-48, TC-49, TC-50 from TEST-PLAN. Plus smoke checks S1-S9.

**Phase 1 keeps /loop alive**: No template changes. No agent behavior change. Harness infrastructure only.

---

### Phase 2: Event Infrastructure + Ack (L — ~3 dev sessions)
**Goal**: Event lifecycle management, ack processing, event_poll.py, external activity detector. Agents still use /loop but event infrastructure is live and testable via curl/scripts.

| # | Change | Current State | What Changes | Reuse vs Rewrite | Complexity | Risk |
|---|--------|--------------|-------------|-----------------|------------|------|
| 2-1 | **Add 5 L1 event types to event_catalog.py** | RECOGNIZED tier (line 91-117) has 5 old types: verification-failed, verification-passed, agent-health, phase-change, request-merge. | Replace entire RECOGNIZED dict with 5 new types: assigned-to, stop-requested, shipped, version-bump, ack. Each with description, planned_source, and payload_fields. EMITTED tier unchanged. | Rewrite RECOGNIZED dict (~25 lines). Keep API functions unchanged. | S | L — tests reference old RECOGNIZED names |
| 2-2 | **Ack processing in POST /events** | `receive_event` (harness.py:827) stores event, updates AgentState, logs. No special handling for any event_type. | Add branch: if event_type == "ack", extract event_id from payload, look up in event_state, mark as acked by role. If ack references stop-requested, treat as shutdown confirmation. | Extend existing handler (~30 lines). Reuse 95%. | M | M — must not break existing non-ack event flow |
| 2-3 | **EventLifecycleManager class** | No event lifecycle management exists. Events are fire-and-forget into deque. | New class (~180 lines): `dispatch(event, target_role)`, `process_ack(event_id, role)`, `timeout_scan()` (background thread), `escalate(event_id)` (kill PID, reboot, re-emit), `persist()`/`load()`. | New class. Uses existing `boot_remote.boot_agent()` for reboot. Uses existing PID check for liveness verification. | L | H — escalate path must verify PID before killing |
| 2-4 | **External activity detector** | No external monitoring exists. Agents self-poll via cycle_pre.py. | New GitHub poller (~120 lines): daemon thread polls GitHub API every event-poll-interval seconds. Filters SquidSquad-labeled issues/PRs and agent-prefix commits. Emits assigned-to for PM via EventLifecycleManager. Uses cursor-based polling (store last-seen updatedAt). | New code. Reuses `_emit_event` (harness.py:1023) for event creation. Reuses existing `gh` CLI or GitHub API. | L | H — must filter SquidSquad's own changes perfectly |
| 2-5 | **event_poll.py — HTTP poll script** | No poll script exists. | New ~30-line script: reads `.harness-port`, queries `GET /events?since=<cursor>&role=<role>`, outputs JSON events to stdout. Saves cursor in `.squidsquad/<role>/.event-cursor`. Handles harness unreachable (empty stdout, non-zero exit). Errors to stderr only. | New file. Reuses `_discover_port()` pattern from event_bus.py (post-P-2 fix). | S | L — stdout must be clean JSON only |
| 2-6 | **event_bus.py ack() function** | `emit()` exists (line 64). No ack function. | Add `ack(event_id, role)` — POSTs `{event_type: "ack", role, payload: {event_id}}` to /events. Fire-and-forget like emit(). Add disk outbox fallback (.event-outbox.json) for harness unreachable. | Add ~20 lines. Reuse existing `_discover_port()`, POST pattern, error handling. | S | L |
| 2-7 | **New endpoints** | No dedicated event lifecycle endpoints exist. | Add: GET /events/{id} (single event state), POST /events/replay (crash recovery), GET /monitors (detector status), GET /events/in-flight/{role} (agent queue). | New endpoints (~60 lines). Use existing FastAPI patterns. | S | L |
| 2-8 | **thin_launcher.py boot prompt + terminal PID** | Line 86: `"Boot. Begin your first Ralph Loop cycle now."` No terminal PID returned. | Change prompt to event-driven: `"Boot. Run event_poll.py with Monitor tool to watch for events."` Return terminal PID to harness (on Windows, `proc.pid` from `subprocess.Popen` is the claude PID, not terminal PID — terminal PID needs different approach). | Modify 1 line of prompt. Terminal PID requires OS-specific handling. | M | M — terminal PID capture on Windows is complex |
| 2-9 | **boot_remote.py terminal PID return** | `_spawn_windows/macos/linux` return `(success, message)`. | Return `(success, message, terminal_pid)` where terminal_pid is the PID of the terminal process (wt.exe on Windows, Terminal.app on macOS, tmux session on Linux). | Modify 3 functions' return signatures. | M | M — PID tracking across process boundaries |

**Phase 2 test coverage**: TC-1 through TC-21, TC-26, TC-27, TC-38, TC-40, TC-42, TC-43, TC-46, TC-47. Smoke checks S1-S9.

**Phase 2 keeps /loop alive**: Agents continue using /loop + cycle_pre/post. Event infrastructure is live and testable via direct POST/GET. event_poll.py can be run manually. Monitor tool doesn't gate this phase.

---

### Phase 3: Template Migration (M — ~2 dev sessions)
**Goal**: Compose produces event-driven templates. Agents switch to event-driven workflow. /loop still exists but agents are told not to use it.

| # | Change | Current State | What Changes | Reuse vs Rewrite | Complexity | Risk |
|---|--------|--------------|-------------|-----------------|------------|------|
| 3-1 | **event-driven-workflow.md** | No such sub-skill exists. | Create new sub-skill covering: Monitor tool + event_poll.py wake, 5 event types with payloads, processing flow (read forge, act, ack), atomicity rule, scan cooldown, what agents do NOT do (no /loop, no cycle_pre/post, no git pull/push). | New file (~100 lines). Follows existing sub-skill format with `<!-- sub-skill: -->` markers. | M | L |
| 3-2 | **Update all includes.yml** | All 24 includes.yml files reference cycle-runner, event-reactions, context-pressure, self-restart, etc. (e.g., dev/includes.yml lines 4-6, 21). | Replace cycle-runner + event-reactions with event-driven-workflow. Remove context-pressure, interval-sync, self-restart, boot-remote-agents from all 24 files. | Edit 24 files (~4 lines changed each). Keep all role-specific sub-skills intact. | M | M — missing one variant causes compose failure |
| 3-3 | **Update role instructions.md + SOUL.md** | All 4 base roles reference Ralph Loop, /loop invocation, cycle mechanics. | Replace cycle prose with event-driven workflow references. Update SOUL.md "You follow the Ralph Loop" → "You react to events." | Edit 8 files (~10-20 lines each). Keep role-specific behavior intact. | M | L |
| 3-4 | **config.md: Event Reactions → Event Driven** | Current config.md lines 132-148 have `## Event Reactions` section with old event types. | Replace with `## Event Driven` section (5 fields with defaults). Remove old Event Reactions section entirely. | Rewrite ~15 lines. | S | L — config.py `get_event_reactions` becomes no-op |
| 3-5 | **Config.py FIELD_MAP additions** | FIELD_MAP (config.py:40-95) lacks 5 Event Driven fields. | Add 5 entries: event-timeout-minutes, event-max-retries, event-poll-interval, event-queue-cap, scan-cooldown. All map to "Event Driven" section. | Add 5 lines to existing dict. | S | L |
| 3-6 | **Compose deployment** | `derive_event_contract` (compose.py) validates against event_catalog. Must work with new 5 L1 types. | Verify derive_event_contract works with new RECOGNIZED tier. If LLM derivation references old event types, update prompts. Test via compose deploy-all. | Reuse 95% — validation logic unchanged. | S | M — LLM derivation may need prompt updates |

**Phase 3 test coverage**: TC-22 through TC-25, TC-28, TC-29, TC-30, TC-37, TC-38, TC-40, TC-41, TC-44. Comprehension questions CQ-1 through CQ-12.

**Phase 3 keeps /loop alive**: Template instructs agents to use Monitor tool, but /loop is still available if something goes wrong. Dual-mode operation for one version to confirm stability.

---

### Phase 4: Cleanup (S — ~1 dev session)
**Goal**: Remove /loop, cycle-runner, legacy sub-skills. Pure event-driven mode only.

| # | Change | Current State | What Changes | Reuse vs Rewrite | Complexity | Risk |
|---|--------|--------------|-------------|-----------------|------------|------|
| 4-1 | **Remove /loop, cycle-runner, context-pressure, interval-sync, self-restart** | Sub-skill .md files exist but are no longer included in manifests. | Delete 5 .md files. Remove from sub-skill registry. | Pure deletion. | S | L — verify no lingering references |
| 4-2 | **Remove cycle_pre.py, cycle_post.py references** | Files retained but unused. | Delete or move to `references/scripts/legacy/`. Remove any remaining import references. | Pure deletion. | S | L — other scripts may import them |
| 4-3 | **Remove cycle-related AgentState slots** | `current_cycle`, `current_phase`, `last_cycle_start`, `last_cycle_end`, `last_cycle_type` in AgentState (harness.py:95-99). | Remove 5 slots. Update `to_dict()`, `save_state()`, `load_state()`, `_update_agent_from_event`. | Remove ~20 lines across 4 locations. | S | M — state file backward compat |
| 4-4 | **Remove event-reactions.md** | File exists at `references/sub-skills/common/event-reactions.md`. Already excluded from manifests. | Delete file. | Pure deletion. | S | L |
| 4-5 | **Verify no `/loop` or "Ralph Loop" in any composed template** | After Phase 3, templates don't reference /loop. | Grep all composed CLAUDE.md/SOUL.md for `/loop` and "Ralph Loop." Fix any stragglers. | Verification only. | S | L |
| 4-6 | **Update manifest.md sub-skill registry** | Registry lists removed sub-skills. | Remove cycle-runner, event-reactions, context-pressure, interval-sync, self-restart, boot-remote-agents. Add event-driven-workflow. | Edit 1 file. | S | L |

**Phase 4 test coverage**: TC-37, TC-38 (full upgrade sequence). Regression TC-42, TC-43. Comprehension questions CQ-1 through CQ-12 re-run against final templates.

---

### Phase-to-Test-Case Mapping

| Phase | Test Cases |
|-------|-----------|
| Phase 1 | TC-31, TC-32, TC-33, TC-34, TC-35 (disk persistence), TC-36 (prerequisites active), TC-39 (pre-upgrade config), TC-45 (terminal PID), TC-48 (thread safety), TC-49 (per-role queue), TC-50 (clone isolation) |
| Phase 2 | TC-1 through TC-6 (5 event types happy path), TC-7 through TC-10 (ack timeout/retry), TC-11 through TC-15 (external activity detector), TC-16 through TC-19 (event_poll.py + Monitor), TC-20 through TC-22 (atomicity), TC-26 (event storm), TC-27 (crash mid-event), TC-38 (upgrade sequence), TC-40 (catalog), TC-42, TC-43 (regression), TC-46 (ack function), TC-47 (validator) |
| Phase 3 | TC-22 through TC-25 (scan cooldown), TC-28 (long idle), TC-29, TC-30 (broadcast ack independence), TC-37 (compose output), TC-40 (catalog verify), TC-41 (config fields), TC-44 (boot prompt) |
| Phase 4 | TC-37, TC-38 (full upgrade), TC-42, TC-43 (regression) |

---

## Vault Candidates

- **Type**: pattern — **Ack-based health monitoring replaces PID polling** — **Why**: Event acknowledgment timeout as the sole health signal (no ack → retry → kill → reboot) is a novel architectural pattern that integrates health monitoring into the event protocol itself. Extends [[decision-pid-primary-liveness]] into event-driven form. Reusable for any event-driven agent system.
- **Type**: decision — **5-event L1 model — monitors translate external signals to assigned-to, never emit own event types** — **Why**: The architectural choice to funnel all external signals (GitHub issues, PRs, commits) through `assigned-to` for PM triage rather than dedicated event types keeps the agent-facing model at exactly 5 types. PM is the single triage point. Fundamental constraint worth capturing.
- **Type**: learning — **Phased architectural migration with dual-mode operation** — **Why**: Strategy of shipping backward-compatible infrastructure changes (Phase 1-2) before template changes (Phase 3), observing for one version, then cleaning up in Phase 4. The loop stays alive until the final phase. Reusable pattern for future architectural overhauls.
- **Type**: learning — **Clone isolation + port file distribution** — **Why**: The parent-dir walk for `.harness-port` discovery was fragile across clone isolation boundaries. The fix — harness distributes port file to all clone `.squidsquad/` directories at boot — is a pattern worth capturing for any future cross-clone communication.
- **Type**: pattern — **Three-tier event failure escalation** — **Why**: ack timeout → re-emit (retry) → max-retries → declare dead + kill PID + reboot → re-emit to rebooted agent → escalate to PM if reboots fail. Embodies [[decision-self-healing-sentinel]] two-tier philosophy in event processing domain. Escalation from retry to kill/reboot is a reusable pattern.
```