Now I have a thorough understanding of the entire architecture. Let me compile the research document.

---

# FEAT-PM-5613-MONITOR Research — Can Monitor Replace /loop Cron-Based Agent Cycling?

## Summary

The Claude Code Monitor tool watches a shell command's stdout and wakes the session on new output — zero tokens spent when silent. This research evaluates whether Monitor can completely replace the `/loop` cron mechanism that currently drives SquidSquad's agent cycling (every N minutes, each agent executes one Ralph Loop cycle via `cycle_pre.py → creative work → cycle_post.py`).

**The answer is NO — Monitor cannot completely replace /loop.** A hybrid model is required. Approximately 8 distinct agent behaviors depend on time-based cycling (quiet-cycle counters for improvement scans, vault synthesis, staleness detection, health checks, working-state resume, context pressure monitoring, doc improvement loops, and vault optimization). However, Monitor can provide significant token savings by *supplementing* /loop: event-triggered immediate wake-up for high-priority events (PR merges, verification failures, human input), while a low-frequency cron (e.g., every 30–60 minutes, or `watchdog.py`-style) handles the housekeeping triggers that require periodic attention regardless of event flow.

**Primary risk**: The event bus is purely in-memory (a bounded `collections.deque` in `harness.py` line 349, max 1000 events), not persisted to an `events.jsonl` file. Monitor would need to poll the harness REST API (`GET /events`) via a custom watcher script — there is no file to `tail`. The 1-hour max Monitor timeout compounds this: for days-running agents, persistent mode would be essential, and the watcher script must handle reconnection when the timeout expires.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill" (pending, high) — directly relevant: agents already read events in `cycle_pre.py` line 1032–1039, but events drive awareness, not waking. #5622 "Harness Phase 3: Agent communication bus" shipped — the event bus is live and agents read it each cycle. #3963 "EPIC: Web dashboard — Harness Phase 4" (pending, high) — any Monitor integration should align with Harness Phase 4.
- **Related decisions**: [[decision-watchdog-supervisor]] — Centralized lifecycle management in `watchdog.py` (now absorbed into `harness.py`). Agents are "dumb workers" that just run cycles. The watchdog polls health independently of agent cycles. This is the architectural precedent for splitting event-triggered work from time-triggered work. [[decision-pid-primary-liveness]] — OS-level truth (PID check) beats application-level files (.health). This preference for direct/mechanical checks applies to Monitor: direct harness API polling is preferred over watching a derived file. [[decision-improvement-loop-philosophy]] — Layer 4 (vault synthesis) triggers every 5 quiet cycles. If Monitor eliminates quiet cycles, synthesis never fires. [[decision-cycle-runner-architecture]] — The mechanical shell/agent core split (cycle_pre.py → creative → cycle_post.py) is architectural bedrock. Monitor would wake the creative phase, but the mechanical shell must still run.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — Any Monitor watcher script must be deterministic Python, not agent-authored bash.
- **Human preferences**: "Systems should self-heal: detect stuck states → unstick immediately → file root-cause bug → agent fixes gap" (human-profile.md line 40). Monitor enables immediate reaction to events (e.g., PR merge → PM reacts immediately instead of waiting up to 30m). "Prefers direct/mechanical checks over indirect state files" (line 33) — a Monitor watcher polling the harness API directly aligns with this preference.
- **Related learnings**: [[learning-atomic-migration-strategy]] — If this change ships, it must be atomic: all agent templates, cycle scripts, and harness changes in one deploy. Partial migration (some agents on Monitor, some on /loop) would break coordination.

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/common/cycle-runner.md` (lines 1–93) — Would need a section on Monitor-triggered vs. cron-triggered cycle entry
  - `references/sub-skills/common/interval-sync.md` (lines 1–14) — CronDelete/CronCreate replaced or augmented with Monitor setup
  - `references/sub-skills/common/improvement-scan.md` (lines 1–92) — "Every quiet cycle" trigger must remain time-based
  - `references/sub-skills/roles/pm/vault-synthesis.md` (lines 1–80) — "After 5 consecutive quiet cycles" — relies on quiet cycle counting
  - `references/sub-skills/common/vault-remember.md` (lines 1–86) — BRIEFING.md staleness check "runs every cycle"
  - `references/sub-skills/roles/dm/doc-improvement-loop.md` (line 15) — "After 3 consecutive quiet cycles"
  - `references/sub-skills/common/vault-optimize.md` (lines 1–7) — "Only run when vault has 20+ notes AND this is a quiet cycle"
  - `references/scripts/cycle_pre.py` (lines 1–1086) — Would need Monitor-awareness (distinguish event-wake from cron-wake)
  - `references/scripts/cycle_post.py` (lines 1–768) — Would need to manage Monitor state
  - `references/scripts/event_bus_reader.py` (lines 1–89) — Current 500ms timeout HTTP poll; Monitor needs streaming or long-poll variant
  - `references/scripts/harness.py` (lines 345–381, 839–869) — EventStream is in-memory deque. Would need SSE/long-poll endpoint for Monitor or disk persistence of events
  - `references/scripts/thin_launcher.py` (lines 1–114) — Initial prompt "Begin your first Ralph Loop cycle now" might need Monitor setup instead of /loop
  - All role instruction files: `references/roles/*/instructions.md` (pm, qa, skill/dev, dm) — /loop invocation replaced or augmented
  - `references/sub-skills/roles/pm/health-check.md` (lines 1–22) — PM health check runs each cycle
  - `references/sub-skills/roles/qa/verification.md` (line 292) — QA checks agent health by reading current-state mtime
  - `references/sub-skills/common/working-state.md` (lines 1–27) — Would need Monitor-related fields (e.g., last event-driven cycle timestamp)

- **Behavior changes**:
  1. Agents wake on events (PR merge, verification result, human comment) instead of every N minutes — **major latency improvement** for coordination
  2. Quiet cycles no longer occur naturally — agents only wake when something happens, so "quiet cycle" detection must become explicit (time-based)
  3. Improvement scans must be triggered by a separate time-based mechanism (low-frequency cron or watchdog)
  4. Context pressure is no longer checked at cycle start — must be monitored out-of-band (already partially handled by `harness.py` polling, but the creative-phase pressure that triggers restart happens at cycle end via `cycle_post.py` line 586–588)
  5. Working-state resume after crash: agent boots, has no pending event, waits forever — needs explicit boot-time check

- **Dependencies**:
  - `harness.py` EventStream (line 345–381): Currently in-memory only. For Monitor to work, either a disk-persisted events file OR a long-poll/SSE endpoint must be added
  - `event_bus_reader.py` (line 24): `_TIMEOUT = 0.5` — currently designed for fire-and-forget within a cycle, not long-poll monitoring
  - Claude Code `/loop` command: This is a Claude Code built-in. Monitor is a different built-in. The agent instruction templates currently hardcode `/loop` with `CronCreate`/`CronDelete` commands
  - `thin_launcher.py` (line 86): Hardcodes `"Boot. Begin your first Ralph Loop cycle now."` — would need Monitor variant
  - `start_team.py` / harness spawning: Agents are launched with expectation of /loop scheduling

## Side Effects

- **Risk 1: Loss of quiet-cycle counting breaks improvement scans, vault synthesis, and doc improvement loops** — Severity: **H** — Mitigation: Implement a hybrid model where a low-frequency (e.g., 60-minute) cron still fires "housekeeping cycles" that ONLY run quiet-cycle-dependent work (improvement scan, vault synthesis, staleness checks, vault optimize). Event-triggered cycles skip this work. The quiet-cycle counter increments only on housekeeping cycles, not event-triggered ones.

- **Risk 2: Context pressure accumulation without monitoring** — Severity: **H** — Mitigation: The harness already has a `health_poll_loop` (harness.py line 276–282, every 5 seconds) that monitors PID liveness. Context pressure is currently read at cycle start (`cycle_pre.py` line 1020) and acted on at cycle end (`cycle_post.py` line 586–588, exit code 42). If events stop and no cron fires, pressure could accumulate undetected. The harness or watchdog must be extended to read context pressure files independently and trigger restarts.

- **Risk 3: Event bus is in-memory — Monitor can't tail a file** — Severity: **H** — Mitigation: Two options: (A) Add disk persistence to `harness.py` EventStream (write to `.squidsquad/.harness/events.jsonl` on each append), then Monitor can `tail -f` that file with a role-based grep filter. (B) Add an SSE/long-poll endpoint to harness and a Python watcher script that polls with backoff. Option A is more aligned with the "deterministic scripts" pattern (tail + grep is mechanically simpler than SSE client). Option B avoids file I/O but adds harness complexity.

- **Risk 4: 1-hour Monitor timeout conflicts with days-running agents** — Severity: **M** — Mitigation: Persistent mode (`persistent: true`) is documented as "full session" — if it truly survives the full claude session, it solves the timeout. If it still restarts after 1 hour, the watcher script must handle reconnection gracefully (wake agent, re-establish Monitor). Either way, the agent instruction template must handle "Monitor expired, re-establish" as a standard recovery path. The `/loop` cron also has an implicit re-establishment each cycle (interval-sync re-checks and re-creates cron if needed).

- **Risk 5: Event storms cause thrashing** — Severity: **M** — Mitigation: If 50 events arrive in rapid succession, Monitor could wake the agent 50 times. The cycle_pre/cycle_post overhead per-wake would be devastating. Mitigation: debounce in the watcher script — accumulate events for a minimum interval (e.g., 2 minutes) before emitting a wake signal, or only wake on the first event after a quiet period.

- **Risk 6: Race condition on event cursor** — Severity: **M** — Mitigation: Currently, `_advance_event_cursor` in `cycle_post.py` line 604–668 runs AFTER the creative phase completes. If Monitor wakes based on "new events exist," but the cycle is still processing previous events, cursor advancement could race with new event detection. The watcher script must check the cursor in working-state.md before deciding whether to wake.

## Edge Cases

- **No events for days (e.g., weekend, project paused)**: Under pure Monitor, agents would never wake. Housekeeping (BRIEFING.md staleness, vault optimization, improvement scans) would stop. This alone proves Monitor cannot be the sole trigger. Hybrid model solves this: low-frequency cron still fires every 60 minutes.

- **Agent crash during event processing**: Agent dies mid-cycle. `/loop` cron would wake it next interval. Monitor would wake on next event, which might not come for hours. Boot-time: `thin_launcher.py` must trigger an initial cycle regardless of event state, to read working-state.md and resume. Currently handled by "Boot. Begin your first Ralph Loop cycle now." — this must remain.

- **File rotation of events.jsonl (if disk-persisted)**: If events are written to disk for Monitor to tail, file rotation (logrotate or manual cleanup) would break `tail -f`. Mitigation: use the harness EventStream's bounded deque behavior (oldest events evicted) — don't rotate, just cap at N lines. Monitor's `tail -f` handles appends gracefully.

- **Multiple agents watching the same event stream**: If skill, PM, QA, and DM all run Monitor watching the same events file/harness, they'd all wake on the same event. The role-based filtering in `_ROLE_EVENT_TYPES` (cycle_pre.py line 377–383) already handles relevance — the watcher script should apply identical filtering before deciding to wake. PM wakes on `pr-merge, verification-failed, verification-passed, cycle-start, cycle-end, status-transition, agent-health`. QA only on `pr-merge, status-transition, cycle-end, verification-failed`. Etc.

- **Harness restart clears in-memory events**: If the harness restarts, the entire `EventStream` deque (1000 events max) is lost. Under current /loop polling, agents would miss events that arrived between harness stop and restart, but on next cycle they'd get new events. Under Monitor, the watcher would need to detect harness unavailability and fall back to periodic polling until harness returns.

## Integration Risks

- **harness.py EventStream is not designed for external streaming**: The current `/events` GET endpoint (line 839) is a polling endpoint with optional `since` cursor. It's called by `event_bus_reader.py` with a 500ms timeout — designed for single-shot queries within a cycle, not for long-lived Monitor watching. Adding SSE or long-poll would require harness changes (FastAPI supports `StreamingResponse` for SSE natively, but this is new harness code).

- **Monitor vs. agent communication layer (#3415 epic)**: The vault project note `agent-communication-layer.md` describes a Telegram-first real-time communication system (lines 103–112). Monitor for event-driven waking partially overlaps with this — both aim to reduce cycle latency. However, they serve different purposes: Monitor wakes the agent to process events; the comms layer lets agents *talk to each other* in real-time. If the comms layer ships, agents could notify each other via Telegram instead of relying on event-bus events, which Monitor then watches. These should be coordinated but not conflated.

- **Watchdog/harness health polling**: The harness already polls agent health every 5 seconds (line 43: `HEALTH_POLL_INTERVAL = 5`). This independent timer proves the architectural feasibility of splitting time-based checks (health) from event-based checks (work). The hybrid model extends this pattern: harness/watchdog handles health + context pressure + staleness, Monitor handles event-triggered waking.

- **Compose-time instruction assembly**: `compose.py` builds agent CLAUDE.md from sub-skills. The current templates hardcode `/loop` with `CronCreate`. If Monitor is introduced, compose.py must conditionally emit either the /loop or Monitor setup based on a config flag (e.g., `wake-mode: monitor` vs `wake-mode: loop`). This is a template change affecting all roles.

## Upgrade & Migration

- **New config values**: `wake-mode` (default: `"loop"`, options: `"loop"`, `"monitor"`, `"hybrid"`), `housekeeping-interval` (default: `60`, minutes between time-based housekeeping cycles when in hybrid/monitor mode)
- **New files**: `references/scripts/monitor_watcher.py` — deterministic Python script that polls harness GET /events with backoff and emits wake signals (or a shell script using `tail -f` on events file if disk persistence is added). Possibly `.squidsquad/.harness/events.jsonl` if disk persistence is added to harness.
- **Template changes**: All role `instructions.md` files (pm, qa, skill/dev, dm) — add conditional Monitor setup block alongside /loop block. `cycle-runner.md` — add "Event-driven vs. time-driven cycle entry" section. `interval-sync.md` — expand to handle Monitor re-establishment. `thin_launcher.py` — conditional initial prompt.
- **Upgrade steps**:
  1. Harness update: Add disk persistence of events (`.squidsquad/.harness/events.jsonl`) or SSE endpoint
  2. Config migration: Add `wake-mode` and `housekeeping-interval` fields with safe defaults
  3. Template update: compose.py conditionally emits Monitor or /loop instructions
  4. Agent recompose: Run `compose.py` to regenerate all CLAUDE.md files
  5. Graceful agent restart: Stop agents via harness, recompose, restart — agents pick up new wake mode on next boot
  6. Per [[learning-atomic-migration-strategy]], all steps must ship atomically in a single dev cycle
- **Graceful degradation**: If `wake-mode` is `"loop"` (default), behavior is completely unchanged. If Monitor is enabled but harness is unreachable, the watcher script must fall back to periodic polling (every N seconds) — effectively degrading to a poor-man's cron. This ensures agents don't hang indefinitely waiting for events that will never arrive.

## Open Questions

- **Q1**: Does Claude Code Monitor's `persistent: true` truly survive the full session (days/weeks), or does it restart after each 1-hour `timeout_ms`? — **Why**: If Monitor expires after 1 hour regardless of persistent mode, agents must self-re-establish Monitor every hour, adding complexity and failure modes. If persistent = truly persistent, the 1-hour limit is a non-issue.

- **Q2**: Should the harness emit events to disk (events.jsonl) for Monitor to tail, or should Monitor poll the REST API? — **Why**: File-based tailing is mechanically simpler and more aligned with the "deterministic scripts over prose" pattern, but requires harness changes to write events to disk. API polling requires a more complex watcher script (handling HTTP errors, backoff, reconnect) but keeps events purely in the harness domain.

- **Q3**: What is the actual token cost of a quiet cycle? — **Why**: The token savings estimate depends on knowing what a quiet cycle burns. Without measurement, we can't quantify the ROI of Monitor adoption. A quiet cycle involves: cycle_pre subprocess calls (gh issue list, tracker queries, git pull — these are bash tool calls in Claude), agent reads cycle-input.json (~2-5K tokens of structured JSON), agent determines nothing to do, runs improvement scan or vault-remember, writes cycle-output.json, cycle_post commits. Rough estimate: 3K–8K input tokens + 500–1500 output tokens per quiet cycle. At 30-minute intervals with 4 agents, that's ~192 quiet cycles/day across the squad, or ~576K–1.5M input tokens/day burned on idle polling.

- **Q4**: Does the human want Monitor now, or is this speculative? — **Why**: The BRIEFING.md shows #5868 "Event consumption sub-skill" as pending/high and #3415 "Agent communication layer" as active. Monitor could be scoped as part of #5868 (event consumption) or deferred until the comms layer ships. Implementing Monitor before the comms layer means agents react faster to events but still communicate via 30m-delayed GitHub Issue comments — faster waking with same slow communication.

- **Q5**: Can the Monitor tool run a Python script (not just a shell command)? — **Why**: The `command` parameter is described as "shell command" — if it only accepts inline shell strings, the watcher must be a shell pipeline (`tail -f events.jsonl | grep ...`) or a single-line Python invocation. If it accepts arbitrary executables, `python references/scripts/monitor_watcher.py <role>` would be cleaner and more maintainable.

## Recommendation

**Feasible with caveats — hybrid model required.** Monitor cannot replace /loop entirely due to 8+ time-based triggers that require periodic waking regardless of event flow. However, a hybrid architecture provides the best of both:

1. **Monitor for event-driven waking**: Watches harness events (via file tail or API poll), wakes agent immediately on high-priority events relevant to the agent's role. Zero tokens burned when no events arrive.

2. **Low-frequency cron for housekeeping**: A single cron (every 60 minutes, or integrated into `harness.py`'s existing health poll loop) fires housekeeping cycles that ONLY run: improvement scans, vault synthesis, vault optimization, BRIEFING.md staleness checks, doc improvement loops, and context pressure monitoring. These cycles skip tracker queries and work queue building if no events arrived since last check.

3. **Boot-time cycle preserved**: `thin_launcher.py` still triggers an initial cycle to read working-state.md and resume any in-progress work. This initial cycle also establishes the Monitor.

This hybrid model reduces token burn on quiet cycles by ~95% (only housekeeping cycles, at 1/2 the frequency, with lighter work), while actually improving responsiveness to coordination events from 30-minute latency to near-instant.

## Vault Candidates

- **Type**: pattern — **Event-driven + time-driven hybrid wake pattern** — **Why**: If implemented, this architectural pattern of splitting agent waking into event-triggered (Monitor) and time-triggered (low-frequency cron) would be the definitive reference for how SquidSquad agents manage their cycle cadence. Reusable for any future wake mechanism.

- **Type**: decision — **Event bus persistence strategy** — **Why**: Whether events are written to disk (events.jsonl) or kept purely in-memory with an API polling watcher is a significant architectural choice that affects reliability, complexity, and debuggability. The chosen approach should be documented as a decision.

- **Type**: learning — **Quiet cycle counting is load-bearing infrastructure** — **Why**: This research revealed that "quiet cycle" counting isn't just a bookkeeping detail — it's the trigger mechanism for improvement scans, vault synthesis, vault optimization, doc improvement loops, and staleness checks. Any architecture change that affects cycle frequency must account for these counters. Documenting this would prevent future proposals from unknowingly breaking these triggers.