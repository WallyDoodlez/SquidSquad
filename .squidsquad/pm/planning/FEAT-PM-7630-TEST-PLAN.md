# FEAT-PM-7630 Test Plan — Event-Driven Agent Architecture

> This plan supersedes the earlier draft. 50 test cases across 11 categories, 9 smoke checks, 9 regression risks, 12 comprehension questions.

## Test Cases

---

### Category 1: Happy Path — 5 Event Types

---

### TC-1: assigned-to — happy path delivery to target agent
- **Precondition**: Harness running. Agent (skill) is alive, idle, Monitor tool watching `event_poll.py` output. GitHub Issue #123 exists.
- **Steps**:
  1. POST to harness: `{"event_type": "assigned-to", "role": "skill", "payload": {"role": "skill", "issue_or_pr": 123}}`
  2. Observe `event_poll.py` stdout from skill agent's Monitor subscription.
  3. Observe skill agent reads Issue #123 from GitHub.
  4. Wait for skill agent to complete work and POST `ack` event.
- **Expected**: Monitor tool wakes agent. Agent reads the forge (not just the payload). Agent completes work and emits `ack {event_id}`. Harness marks event `acked` in `.squidsquad/.event-state.json`. No second event dispatched to skill before ack received.
- **Verification**: `GET /events/{event_id}` → `status: acked`. `.squidsquad/.event-state.json` shows `acked_at` timestamp. `GET /events/in-flight/skill` → empty list.

---

### TC-2: stop-requested — graceful agent shutdown
- **Precondition**: Harness running. Skill agent alive, idle. No events in flight.
- **Steps**:
  1. POST stop: `{"event_type": "stop-requested", "role": "skill", "payload": {"source": "human", "target": "skill"}}`
  2. Observe agent behavior.
  3. Wait for ack.
- **Expected**: Agent receives event, checkpoints `working-state.md`, stops Monitor tool, emits `ack {event_id}`. Harness processes ack on `stop-requested` as shutdown confirmation. Agent process exits. Harness does NOT reboot the agent (intent = stopping).
- **Verification**: `GET /agents/skill` → `status: stopped`, `intent: stopping`. `.squidsquad/skill/working-state.md` updated with checkpoint. Harness does not reboot within 30 seconds.

---

### TC-3: stop-requested — agent finishes current event atomically before stopping
- **Precondition**: Skill agent actively processing an `assigned-to` event for Issue #123.
- **Steps**:
  1. While agent is mid-work, POST `stop-requested` for skill.
  2. Observe whether agent interrupts work or completes it.
- **Expected**: Agent completes the current `assigned-to` event fully before processing `stop-requested`. Event atomicity is preserved — no partial outputs. After completing the first event and emitting its ack, agent then processes `stop-requested` and acks it.
- **Verification**: Issue #123 has complete, non-partial output. Both events in `.event-state.json` show `acked`. Agent exits after both acks.

---

### TC-4: shipped — broadcast to all agents
- **Precondition**: Harness running. All agents (pm, skill, qa) alive and idle.
- **Steps**:
  1. Harness emits `shipped {issue_or_pr: 456}` (simulating DM delivery announcement).
  2. Observe all agents receive and respond.
- **Expected**: Event dispatched to all agents. Each agent independently updates their status line and emits `ack {event_id}`. Harness does NOT wait for all agents to ack before marking complete — each ack is processed independently. `acked_by` list in `.event-state.json` grows as each agent acks.
- **Verification**: `GET /events/{event_id}` → `acked_by` includes all three roles. Each role's ack has distinct `acked_at` timestamp. Harness never blocks waiting for all acks simultaneously.

---

### TC-5: version-bump — broadcast to all agents
- **Precondition**: Harness running. All agents alive and idle.
- **Steps**:
  1. Harness emits `version-bump {version: "1.5.0"}`.
  2. Observe all agents.
- **Expected**: Each agent reads the payload, updates their status line, emits `ack`. Same independent-ack behavior as TC-4.
- **Verification**: `GET /events/{event_id}` → `acked_by` includes all roles. Status lines show updated version reference in agent terminals.

---

### TC-6: ack — replaces POST /events/{id}/complete, universal closure
- **Precondition**: Agent has received an `assigned-to` event with `event_id: evt-abc`.
- **Steps**:
  1. Agent runs: `python references/scripts/event_bus.py ack evt-abc skill`
  2. Observe harness handling.
- **Expected**: POST to harness `/events` with `event_type: ack, payload: {event_id: evt-abc}`. Harness looks up `evt-abc`, marks it `acked` by `skill`. No separate `stopped` event emitted. The `ack` is the sole closure mechanism. `POST /events/{id}/complete` endpoint does not exist (endpoint was removed).
- **Verification**: `GET /events/evt-abc` → `status: acked`. No `stopped` event appears in event stream. HTTP 404 on `POST /events/evt-abc/complete` confirms endpoint removal.

---

### Category 2: Ack Timeout and Retry Flow (Health Monitoring)

---

### TC-7: ack timeout — event re-emitted on first timeout
- **Precondition**: `event-timeout-minutes: 1` (set low for testing). Skill agent alive but unresponsive (simulate by blocking ack script).
- **Steps**:
  1. Dispatch `assigned-to` to skill.
  2. Prevent agent from emitting ack.
  3. Wait for timeout + 30 seconds.
- **Expected**: After 1 minute, harness detects no ack. Re-emits the event to skill (`retry_count: 1`). `GET /events/{id}` shows `retry_count: 1`, `status: in-flight`.
- **Verification**: `.squidsquad/.event-state.json` shows `retry_count: 1`. Event appears again in `GET /events?role=skill&since=<cursor>`. Event `status` is still `in-flight`, not `acked` or `timed-out`.

---

### TC-8: ack timeout — max retries reached → agent declared dead → kill PID → reboot → re-emit
- **Precondition**: `event-timeout-minutes: 1`, `event-max-retries: 3`. Agent persistently fails to ack.
- **Steps**:
  1. Dispatch event to skill.
  2. Block ack indefinitely.
  3. Wait for 3 retry cycles.
- **Expected**: After 3 retries, harness declares skill agent dead. Harness kills PID via OS (verified via OS check). Harness reboots skill agent via thin_launcher. Event is re-emitted to the rebooted agent. If reboots also fail repeatedly, harness escalates to PM.
- **Verification**: `GET /agents/skill` shows `status: rebooting` then `running`. Original PID no longer alive (OS check). New PID present in `GET /agents/skill`. Event re-emitted in event stream. `.event-state.json` shows `retry_count: 3` then a new dispatch record.

---

### TC-9: ack timeout — PID alive and active → retry without killing
- **Precondition**: Agent is processing a legitimately long task (> `event-timeout-minutes`) but PID is alive and CPU-active with context pressure below threshold.
- **Steps**:
  1. Dispatch event requiring work that takes longer than the timeout.
  2. Wait past timeout.
  3. Observe harness behavior.
- **Expected**: Harness checks PID via OS before declaring dead. PID alive + context pressure below threshold + wake was delivered → harness retries (re-emits) but does NOT kill the agent. Agent eventually acks and event closes normally.
- **Verification**: Agent PID survives past timeout. Event shows `retry_count >= 1` but agent is not killed. Agent eventually acks.

---

### TC-10: ack loss recovery — disk outbox fallback
- **Precondition**: Agent sends ack but harness is temporarily unreachable (simulated network blip).
- **Steps**:
  1. Agent processes event, calls `event_bus.py ack`.
  2. Harness endpoint is down for 30 seconds.
  3. Harness comes back up.
- **Expected**: `event_bus.py` detects unreachable harness, appends ack to `.squidsquad/.event-outbox.json`. On harness reconnect, outbox is drained and ack is delivered. Duplicate acks (if event retried in the meantime) are handled idempotently — duplicate acks are safe.
- **Verification**: `.squidsquad/.event-outbox.json` contains pending ack while harness is down. After harness recovers, `GET /events/{id}` → `status: acked`. No double-processing side effects from the duplicate ack.

---

### Category 3: External Activity Detector (Including Own-Change Filtering)

---

### TC-11: external activity detector — new GitHub issue triggers assigned-to for PM
- **Precondition**: External activity detector running. GitHub repo configured. PM agent alive.
- **Steps**:
  1. Create a new GitHub Issue without the `squidsquad` label (simulating human-filed issue).
  2. Wait for `event-poll-interval` seconds (default 30s).
- **Expected**: Detector polls GitHub, detects new issue without `squidsquad` label. Harness emits `assigned-to {role: "pm", issue_or_pr: <number>}`. PM agent receives event, reads the issue from GitHub, triages it.
- **Verification**: `GET /events?role=pm&event_type=assigned-to` shows event with new issue number. PM comments on the issue within one poll interval. `GET /monitors` → `github_detector: {status: running, last_activity: <recent>}`.

---

### TC-12: external activity detector — filters SquidSquad agent commits (own changes)
- **Precondition**: Detector running. SquidSquad agents committing with standard role prefix.
- **Steps**:
  1. Skill agent commits: `skill: cycle 42 — implement feature`.
  2. Wait for detector poll cycle.
- **Expected**: No `assigned-to` event emitted. Detector filters out commits with agent prefix pattern (`skill:`, `pm:`, `qa:`, `dm:`).
- **Verification**: No new `assigned-to` events in `GET /events?role=pm` after the agent commit. `GET /monitors` shows `last_check` advanced but `last_activity` unchanged.

---

### TC-13: external activity detector — filters SquidSquad-labeled issues and PRs
- **Precondition**: Detector running.
- **Steps**:
  1. PM agent opens a GitHub Issue with the `squidsquad` label.
  2. SquidSquad agent opens a PR with `squidsquad` label.
  3. Wait for detector poll cycle.
- **Expected**: Neither the issue nor the PR triggers an `assigned-to` event. Detector ignores all items bearing the `squidsquad` label.
- **Verification**: No new events in stream after agent-created activity. Confirmed via `GET /events?since=<before-activity>&event_type=assigned-to`.

---

### TC-14: external activity detector — cursor-based polling prevents duplicate events on restart
- **Precondition**: Detector has already processed Issue #500. Harness restarts.
- **Steps**:
  1. Record cursor (last-seen GitHub `updatedAt`) before restart.
  2. Restart harness.
  3. Wait for first poll cycle.
- **Expected**: Detector resumes from saved cursor. Issue #500 is NOT re-emitted. Only activity after the cursor triggers new events.
- **Verification**: No duplicate `assigned-to` events for previously processed issues. Cursor stored in `.squidsquad/.event-state.json` under detector state key.

---

### TC-15: external activity detector — GitHub API rate limiting handled gracefully
- **Precondition**: Detector configured. Rate limit exhausted or simulated 429 response.
- **Steps**:
  1. Simulate 429/403 response from GitHub API.
  2. Observe detector behavior.
- **Expected**: Detector backs off gracefully. Does not crash harness. Logs warning. Resumes polling after backoff window. No duplicate events on resume.
- **Verification**: Harness still running. `GET /monitors` shows `status: rate-limited` or equivalent. Events resume after backoff.

---

### Category 4: Monitor Tool Wake Mechanism (event_poll.py + Monitor)

---

### TC-16: event_poll.py — outputs events to stdout when harness has pending events
- **Precondition**: Harness running. No pending events for role `skill`.
- **Steps**:
  1. Run: `python references/scripts/event_poll.py skill`
  2. In a second terminal, dispatch an `assigned-to` event to skill.
  3. Wait for next poll interval.
- **Expected**: `event_poll.py` outputs nothing when no events exist. When event arrives, script outputs JSON event payload to stdout within one poll interval. Script reads `.harness-port` from local `.squidsquad/` directory for discovery.
- **Verification**: stdout shows JSON: `{"event_id": "...", "event_type": "assigned-to", "payload": {...}}`. No errors when harness is reachable.

---

### TC-17: Monitor tool — detects event_poll.py stdout and wakes agent
- **Precondition**: Agent session running with `Monitor: python references/scripts/event_poll.py skill`.
- **Steps**:
  1. Dispatch event to skill.
  2. Observe agent terminal.
- **Expected**: Monitor tool detects `event_poll.py` stdout within sub-second to a few seconds. Agent wakes and reads the event payload. Agent does not need to poll manually — Monitor tool handles passive detection.
- **Verification**: Agent begins responding to event without manual invocation. Latency from event dispatch to agent awareness is measurable and sub-minute.

---

### TC-18: event_poll.py — cursor tracking prevents duplicate event delivery
- **Precondition**: Agent has already processed event `evt-abc`. Cursor saved.
- **Steps**:
  1. Poll again with saved cursor: `python references/scripts/event_poll.py skill`.
  2. No new events since `evt-abc`.
- **Expected**: Script passes `since=<cursor>` to `GET /events`. Returns empty. Does not re-output already-seen events.
- **Verification**: stdout is empty. Script exits with 0. No duplicate events trigger agent wake.

---

### TC-19: event_poll.py — harness unreachable handled without spurious stdout
- **Precondition**: Harness not running. `.harness-port` exists from previous run.
- **Steps**:
  1. Run `python references/scripts/event_poll.py skill` with harness stopped.
- **Expected**: Script handles connection failure gracefully. Does not crash. Returns empty stdout or a non-JSON error to stderr (not stdout). No Python traceback on stdout that Monitor tool could misinterpret as an event.
- **Verification**: stdout is empty or clean (no traceback). Script exits with non-zero code. Monitor tool not spuriously triggered.

---

### Category 5: Event Atomicity

---

### TC-20: second event queued while first is in-flight — no simultaneous dispatch
- **Precondition**: Agent processing an `assigned-to` event (long work in progress). Second `assigned-to` event dispatched for same role.
- **Steps**:
  1. Dispatch first event to skill. Confirm agent is actively working.
  2. While agent works, dispatch a second `assigned-to` event to skill.
  3. Observe harness and agent behavior.
- **Expected**: Harness queues the second event (per-role in-flight queue). Agent is NOT interrupted mid-work. Agent finishes first event, acks it, THEN Monitor tool delivers the second event.
- **Verification**: `GET /events/in-flight/skill` shows second event as `pending` while first is `in-flight`. Second event transitions to `in-flight` only after first is `acked`.

---

### TC-21: Monitor tool queues notifications behind current work naturally
- **Precondition**: Agent woken by Monitor tool for event A. While processing event A, event B arrives and `event_poll.py` outputs it to stdout.
- **Steps**:
  1. Agent starts processing event A.
  2. Dispatch event B while A is in progress.
  3. Observe agent behavior.
- **Expected**: Monitor tool queues the event B notification. Agent does not interrupt event A processing. After acking event A, agent processes the queued Monitor notification for event B.
- **Verification**: Logs show event A completed before event B processing begins. No interleaved partial work output.

---

### TC-22: stop-requested does not interrupt a running event mid-work
- **Precondition**: Agent processing `assigned-to` for Issue #789. `stop-requested` arrives.
- **Steps**:
  1. Agent working on Issue #789.
  2. `stop-requested` broadcast arrives mid-work.
  3. Observe ordering.
- **Expected**: Agent completes Issue #789 work first. Then processes `stop-requested` (checkpoint, ack, exit). Both acks emitted in correct order.
- **Verification**: `.event-state.json` shows `assigned-to` acked before `stop-requested` acked. Issue #789 has complete, non-partial output.

---

### Category 6: Scan Cooldown (15 Minutes Between Scans)

---

### TC-23: scan cooldown — 15-minute gap enforced between scans
- **Precondition**: `scan-cooldown: 15` (default). Agent just completed an improvement scan.
- **Steps**:
  1. Agent completes scan. Scan timestamp recorded.
  2. System goes idle. Wait 14 minutes.
  3. Observe: no scan at 14 minutes.
  4. Wait 1 more minute (15 total). Observe.
- **Expected**: No scan triggered at 14 minutes. Scan triggered at 15-minute mark. First scan after boot happens immediately on idle (no initial cooldown — scan immediately on idle is the specified default).
- **Verification**: Scan log or event shows scan at 15-minute boundary, not before. First-ever scan happens immediately on going idle.

---

### TC-24: scan cooldown — issue gate blocks scan even when cooldown elapsed
- **Precondition**: `scan-cooldown: 15`. Open issues assigned to pm. 15 minutes elapsed.
- **Steps**:
  1. Confirm open issue exists for pm role.
  2. Wait 15 minutes with no events.
  3. Observe whether scan fires.
- **Expected**: Scan does NOT fire while open issues exist for the role. Issues take priority over scans.
- **Verification**: No scan event in event stream. `GET /events?role=pm&event_type=scan-due` → empty. Open issue persists unblocked.

---

### TC-25: scan cooldown — L4 override via config.md
- **Precondition**: `config.md → Event Driven → Scan Cooldown Minutes: 5`.
- **Steps**:
  1. Agent completes scan.
  2. Wait 5 minutes idle.
  3. Observe next scan trigger.
- **Expected**: Scan fires after 5 minutes, not 15.
- **Verification**: `python references/scripts/config.py get scan-cooldown` returns `5`. Scan event at ~5-minute mark.

---

### Category 7: Edge Cases

---

### TC-26: event storm — queue cap enforced at 50, drop counter incremented
- **Precondition**: `event-queue-cap: 50` (default). Agent idle.
- **Steps**:
  1. Dispatch 60 events to skill in rapid succession.
  2. Observe queue behavior.
- **Expected**: First 50 events queued. Events 51-60 dropped. Drop counter incremented (observable in harness metrics). No crash. No silent loss — counter tracks dropped events. Agent processes all 50 queued events in order.
- **Verification**: `GET /events/in-flight/skill` shows max 50 entries. Harness log or counter shows 10 dropped. Agent eventually acks all 50 queued events.

---

### TC-27: agent crash mid-event — harness detects via ack timeout, reboots, re-emits
- **Precondition**: `event-timeout-minutes: 2`, `event-max-retries: 3`. Event dispatched to skill.
- **Steps**:
  1. Kill skill agent PID mid-processing (simulate crash).
  2. Wait for timeout.
- **Expected**: Harness detects no ack within timeout. PID is dead → diagnosis: crashed → respawn. Harness reboots skill. Event re-emitted to rebooted agent. Rebooted agent reads `working-state.md` and picks up from checkpoint.
- **Verification**: New PID for skill in `GET /agents/skill`. Event re-appears in event stream with `retry_count: 1`. Event eventually acked by rebooted agent.

---

### TC-28: no events for long period — agent sits idle, visual indicator shown
- **Precondition**: Agent running in event-driven mode. No events for 2 hours.
- **Steps**:
  1. Let system idle for extended period with no GitHub activity.
  2. Observe agent terminal and harness console.
- **Expected**: Agent prints idle indicator. Harness console shows all agents as `idle` with timestamps. No cycle logs written. Monitor tool continues watching. Agent process alive throughout. No false-positive death declarations from harness.
- **Verification**: `GET /agents/skill` → `status: idle`, `idle_since: <timestamp>`. `GET /agents/skill/health` → `alive: true`. No error events in event stream.

---

### TC-29: multi-agent broadcast — shipped ack is independent per agent, no blocking
- **Precondition**: 3 agents alive (pm, skill, qa). `shipped` event broadcast.
- **Steps**:
  1. Emit `shipped {issue_or_pr: 789}`.
  2. One agent (qa) is slow to ack (simulate 30-second delay).
  3. Other agents (pm, skill) ack immediately.
- **Expected**: pm and skill acks processed immediately. Harness does NOT wait for qa to ack before processing pm/skill acks. qa acks 30 seconds later and it is processed. No harness timeout or re-emit due to slow qa ack. Each ack is independent.
- **Verification**: `GET /events/{id}` shows `acked_by: [pm, skill]` after 5 seconds. `acked_by: [pm, skill, qa]` after 35 seconds. No harness timeout triggered for pm/skill while qa is slow.

---

### TC-30: multi-agent broadcast — version-bump ack is independent per agent
- **Precondition**: Same as TC-29 but with `version-bump` event.
- **Steps**: Same pattern as TC-29 with `version-bump {version: "2.0.0"}`.
- **Expected**: Same independent-ack behavior. Each agent's status line updated independently.
- **Verification**: Same as TC-29.

---

### Category 8: Disk Persistence and Crash Recovery

---

### TC-31: disk persistence — in-flight events survive harness crash and restart
- **Precondition**: Event dispatched to skill (status: `in-flight`). Harness crashes (kill -9 harness PID).
- **Steps**:
  1. Dispatch event. Confirm `in-flight` in `.squidsquad/.event-state.json`.
  2. Kill harness process.
  3. Restart harness.
- **Expected**: Harness reads `.event-state.json` on boot. Finds event in `in-flight` state. Replays it to the skill agent. Event is NOT lost.
- **Verification**: After restart, `GET /events/{id}` still exists with same ID. `POST /events/replay` (or auto-replay on boot) re-emits the event. Skill agent receives event and acks it.

---

### TC-32: disk persistence — event-state.json written atomically on every state change
- **Precondition**: Harness running, event-driven mode.
- **Steps**:
  1. Dispatch event. Check `.squidsquad/.event-state.json`.
  2. Agent acks. Check file again.
- **Expected**: File updated on dispatch (`status: in-flight`) and on ack receipt (`status: acked`, `acked_at` populated). Each update is atomic (tmp + rename pattern). File is valid JSON after each write.
- **Verification**: File stat timestamps advance on each state change. `python -m json.tool .squidsquad/.event-state.json` → valid JSON after each write.

---

### TC-33: crash recovery — POST /events/replay replays in-flight events
- **Precondition**: Two events in `.event-state.json` with `status: in-flight` from a previous harness run.
- **Steps**:
  1. Start fresh harness with the pre-populated `.event-state.json`.
  2. Call `POST /events/replay`.
- **Expected**: Response: `{replayed: 2, failed: 0}`. Both events re-queued for delivery. Skill agent (if alive) receives both events.
- **Verification**: `GET /events?role=skill` shows both events available for poll. Both eventually acked.

---

### TC-34: crash recovery — two-phase received→closed survives mid-closure crash
- **Precondition**: Agent POSTs ack. Harness persists state but crashes before executing git operations.
- **Steps**:
  1. Simulate harness crash after persisting ack state but before executing git commit/push side effects.
  2. Restart harness.
  3. Harness scans for events in intermediate state.
- **Expected**: Harness replays side effects (git commit/push) from persisted state. Ack is idempotent — emitting ack for the same event_id multiple times is safe; harness processes the first and ignores duplicates. Event transitions to fully closed after replay.
- **Verification**: Tracker comment not duplicated. Git commit not duplicated. Event state transitions to `closed`.

---

### TC-35: harness state — agents.*.in_flight_events persisted and restored on restart
- **Precondition**: Skill agent has `in_flight_events: ["evt-abc"]`. Harness restarts.
- **Steps**:
  1. Confirm `in_flight_events` in `.harness-state.json`.
  2. Kill and restart harness.
  3. Read restored state.
- **Expected**: `GET /agents/skill` after restart shows `in_flight_events: ["evt-abc"]` restored. Harness knows the event is in-flight and resumes monitoring for ack.
- **Verification**: `.harness-state.json` contains `in_flight_events` under skill. After restart, `GET /events/in-flight/skill` returns `evt-abc`.

---

### Category 9: Upgrade Path

---

### TC-36: Phase 1.5 prerequisites active on install
- **Precondition**: Fresh install of #7630 changes.
- **Steps**:
  1. Start harness.
  2. Verify P-1 through P-4 behavior.
- **Expected**: P-1 (disk persistence), P-2 (clone discovery fix), P-3 (per-role queue), P-4 (thread safety) all active. Infrastructure improvements are unconditional.
- **Verification**: `.squidsquad/.event-state.json` created on harness start. `event_bus.py._discover_port()` works from clone directories. `GET /agents/skill` shows `in_flight_events` field exists. No race conditions under concurrent load.

---

### TC-37: compose.py deploy-all produces correct event-driven templates
- **Precondition**: Fresh install of #7630.
- **Steps**:
  1. `python references/scripts/compose.py deploy-all`. Inspect `.squidsquad/skill/CLAUDE.md`.
- **Expected**: CLAUDE.md contains `event-driven-workflow` sub-skill. Monitor tool boot prompt references `event_poll.py`. No `/loop` invocation.
- **Verification**: `grep event-driven-workflow .squidsquad/skill/CLAUDE.md` → match. `grep /loop .squidsquad/skill/CLAUDE.md` → no match.

---

### TC-38: upgrade sequence — stop-recompose-restart completes cleanly
- **Precondition**: Agents running. Upgrading to #7630.
- **Steps**:
  1. `python references/scripts/start_team.py --stop --all`
  2. Apply #7630 changes.
  3. `python references/scripts/compose.py deploy-all`
  4. Clean stale sentinel files from clone directories.
  5. Start harness.
- **Expected**: All steps complete without error. No lingering `/loop` sessions. Agents boot in event-driven mode.
- **Verification**: `GET /agents` → all agents `status: idle` (not cycling). Agent terminals show Monitor tool boot.

---

### TC-39: pre-upgrade config.md (no Event Driven section) handled gracefully
- **Precondition**: `config.md` from before #7630 (no `## Event Driven` section).
- **Steps**:
  1. Run post-#7630 harness with pre-#7630 config.md.
- **Expected**: Harness starts without error. All new config fields default gracefully (`event-timeout-minutes: 10`, etc.). No crash or missing key error.
- **Verification**: Harness exit code 0. `python references/scripts/config.py get event-timeout-minutes` → default value. All 5 new fields return defaults.

---

### TC-40: event_catalog.py — 5 L1 event types present in RECOGNIZED tier
- **Precondition**: Post-#7630 `event_catalog.py`.
- **Steps**:
  1. Import `RECOGNIZED` from `event_catalog`.
  2. Check for all 5 event types.
- **Expected**: `assigned-to`, `stop-requested`, `shipped`, `version-bump`, `ack` all present in `RECOGNIZED` with descriptions and sources.
- **Verification**: `python -c "from event_catalog import RECOGNIZED; print(list(RECOGNIZED.keys()))"` → includes all 5. No `KeyError` on any of the 5.

---

### TC-41: config.py reads all 5 Event Driven fields correctly
- **Precondition**: `config.md` has the `## Event Driven` section with all 5 fields populated.
- **Steps**:
  1. Run `python references/scripts/config.py get <field>` for each of the 5 fields: `event-timeout-minutes`, `event-max-retries`, `event-poll-interval`, `event-queue-cap`, `scan-cooldown`.
- **Expected**: Each command exits 0 and returns the configured value.
- **Verification**: All 5 commands succeed. No `KeyError` or `None` returned for any field.

---

### Category 10: Regression Tests for Existing Functionality

---

### TC-42: existing POST /events endpoint still works for non-ack events
- **Precondition**: Post-#7630 harness running. Existing agent scripts emitting events.
- **Steps**:
  1. POST a `cycle-start` event: `{"event_type": "cycle-start", "role": "skill"}`.
- **Expected**: Harness accepts the event. Returns `{status: "ok"}`. Existing event emission from `event_bus.py emit()` is unchanged.
- **Verification**: HTTP 200. Event appears in `GET /events`. No regression in existing event bus usage.

---

### TC-43: existing GET /events filtering still works correctly
- **Precondition**: Multiple events for multiple roles in harness.
- **Steps**:
  1. `GET /events?role=skill` — should return only skill events.
  2. `GET /events?event_type=assigned-to` — should return only that type.
  3. `GET /events?since=<cursor>` — should return only events after cursor.
- **Expected**: All existing filter params work as before. No regression.
- **Verification**: Response counts match expected filtered results. No cross-role contamination.

---

### TC-44: thin_launcher.py boot prompt uses event-driven mode
- **Precondition**: Post-#7630 `thin_launcher.py`.
- **Steps**:
  1. Inspect boot prompt generated by `thin_launcher.py`.
- **Expected**: Boot prompt contains `event_poll.py` and Monitor tool reference. No `/loop` invocation.
- **Verification**: Read `thin_launcher.py` prompt generation logic. Confirm Monitor tool + `event_poll.py` references present.

---

### TC-45: boot_remote.py returns terminal PID alongside agent PID
- **Precondition**: Post-#7630 `boot_remote.py`.
- **Steps**:
  1. Boot a skill agent via `boot_remote.py`.
  2. Inspect returned data.
- **Expected**: `_spawn_windows` (and Unix variants) return both `agent_pid` and `terminal_pid`. Harness stores `terminal_pid` in `.harness-state.json`.
- **Verification**: `.harness-state.json` contains `terminal_pid` field for the skill agent. Both PIDs are valid OS process IDs and are distinct from each other.

---

### TC-46: event_bus.py ack() function — fire-and-forget POST to /events
- **Precondition**: Harness running.
- **Steps**:
  1. Call `python references/scripts/event_bus.py ack evt-abc skill`.
  2. Check harness received it.
- **Expected**: `ack()` POSTs `{event_type: "ack", role: "skill", payload: {event_id: "evt-abc"}}` to harness `/events`. Returns without waiting for harness to process side effects.
- **Verification**: `GET /events?event_type=ack&role=skill` shows the ack event. HTTP round-trip completes quickly.

---

### TC-47: event_validator.py — validates all 5 new L1 event types correctly
- **Precondition**: Post-#7630 `event_validator.py` and `event_catalog.py`.
- **Steps**:
  1. Validate each of the 5 event types with correct payloads.
  2. Validate each with missing required payload fields.
- **Expected**: Valid events pass. Invalid events (missing `issue_or_pr` in `assigned-to`, missing `event_id` in `ack`, etc.) return validation errors.
- **Verification**: `python -c "from event_validator import validate; validate('assigned-to', {'role': 'skill', 'issue_or_pr': 123})"` → no error. Missing field → validation error raised.

---

### TC-48: thread safety — concurrent event dispatch and ack do not corrupt state
- **Precondition**: Harness running. Multiple agents.
- **Steps**:
  1. Dispatch 5 events concurrently (different roles).
  2. All agents ack concurrently.
  3. Inspect `.event-state.json` for consistency.
- **Expected**: No race conditions. All events tracked correctly. No lost acks. `.event-state.json` valid JSON after concurrent writes. No `RuntimeError` about dictionary size change.
- **Verification**: `python -m json.tool .squidsquad/.event-state.json` → valid JSON. All 5 events show `status: acked`. Harness logs show no lock exceptions.

---

### TC-49: per-role event queue — each role's queue is independent
- **Precondition**: Three roles (pm, skill, qa). Events dispatched to all simultaneously.
- **Steps**:
  1. Dispatch 10 events to pm, 5 to skill, 2 to qa simultaneously.
- **Expected**: Each role has its own independent queue. pm queue has 10, skill has 5, qa has 2. Skill processing does not block pm queue. No cross-role contamination.
- **Verification**: `GET /events/in-flight/pm` → up to 10 entries. `GET /events/in-flight/skill` → up to 5 entries. Queues drain independently.

---

### Category 11: Clone Isolation

---

### TC-50: clone isolation — event_bus.py and event_poll.py discover harness from clone directory
- **Precondition**: Agent running in sibling clone directory (e.g., `SquidSquad-skill/`). Harness distributes `.harness-port` to clone's `.squidsquad/` at boot.
- **Steps**:
  1. From clone directory, run `python references/scripts/event_bus.py emit cycle-start skill`.
  2. From clone directory, run `python references/scripts/event_poll.py skill`.
- **Expected**: Both scripts find `.harness-port` in the clone's local `.squidsquad/` directory. No parent-directory walk needed. Both succeed.
- **Verification**: Both scripts emit/receive without error from clone path. No `FileNotFoundError` for `.harness-port`. Event appears in harness event stream.

---

## Smoke Tests

These must pass within 5 minutes of deploying #7630 changes before investing in full TC runs:

- [ ] `python references/scripts/event_poll.py --help` or running with no harness exits cleanly (no Python traceback on stdout)
- [ ] `python -c "from event_catalog import RECOGNIZED; assert 'assigned-to' in RECOGNIZED"` passes
- [ ] `python -c "from event_catalog import RECOGNIZED; assert 'ack' in RECOGNIZED"` passes
- [ ] `python -c "from event_catalog import RECOGNIZED; assert 'stop-requested' in RECOGNIZED"` passes
- [ ] `GET /events` returns 200 with `{events: [], total: 0}` on fresh harness
- [ ] `GET /events/in-flight/skill` returns 200 with empty list on fresh harness
- [ ] `GET /monitors` returns 200 with detector running
- [ ] `.squidsquad/.event-state.json` created on harness start (may be `{}` initially)
- [ ] Existing `POST /events` still returns `{status: "ok"}` for a non-ack event (regression check)

---

## Regression Risks

- **POST /events/{id}/complete referenced in old agent templates**: If any residual CLAUDE.md contains the old endpoint, agents will 404 on closure attempts. Verify no old endpoint references after compose with `grep -r "events.*complete" .squidsquad/*/CLAUDE.md`.
- **event_bus.py emit() regresses after ack() addition**: The new `ack()` function shares infrastructure with `emit()`. A refactor could break emit for existing callers. Run existing event bus tests after adding `ack()`.
- **`.harness-state.json` schema change breaks existing harness reads**: New fields (`in_flight_events`, `last_wake_at`, `idle_since`, `event_state`) must not break `load_state()` on configs with the old schema. Validate graceful migration — old fields preserved, new fields added with defaults.
- **event_catalog.py RECOGNIZED additions break derivation (#5868)**: Event contract derivation depends on the catalog. Adding 5 new types must not confuse the derivation logic for existing harness-internal types.
- **Thread contention under load**: `EventLifecycleManager` lock must not deadlock with existing `HarnessState._lock` and `EventStream._lock`. Multi-lock acquisition paths must maintain consistent lock ordering.
- **Monitor tool stdout parsing spuriously triggered**: If `event_poll.py` emits any non-event output (debug logs, empty lines, error tracebacks) to stdout, Monitor tool may misinterpret it as an event trigger. The script's stdout must be clean event JSON only — errors go to stderr.
- **Ack processing in POST /events swallows non-ack events**: Adding ack logic to the existing `receive_event` handler must branch cleanly. Existing non-ack events must still be processed as before. Verify with TC-42.
- **Windows ProactorEventLoop conflicts with new threads**: Per known project risk, asyncio pipe exceptions are cosmetic now but adding `EventLifecycleManager` threads and the external activity detector thread may surface new Windows-specific failures when the harness web UI (issue #3963) is added.
- **Pre-upgrade config.md missing new fields causes KeyError**: Any access to the 5 new Event Driven config fields must default gracefully on pre-upgrade configs. Verify with TC-39.

---

## Comprehension Questions

These questions are answered by a fresh agent reading only the modified files. They validate that the instructions are self-contained and unambiguous. QA spawns a fresh subagent, provides only the listed files, and scores answers against expected derivations. No prior context or conversation memory permitted.

### CQ-1: What is the agent's wake mechanism in event-driven mode?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: Agent uses the Monitor tool watching `event_poll.py` stdout. `event_poll.py` queries `GET /events?since=<cursor>&role=<role>` from the harness. When new events arrive, the script outputs them to stdout and Monitor tool wakes the agent within the same persistent session. No `/loop`, no manual polling, no kill/respawn.

### CQ-2: How does an agent close (complete) an event?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: Agent runs `python references/scripts/event_bus.py ack <event_id> <role>`. This POSTs an `ack` event to the harness `/events` endpoint with the `event_id` being acknowledged. No separate endpoint exists for event closure. Ack is the universal closure mechanism.

### CQ-3: What does an agent do when it receives a stop-requested event?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: Finish current event atomically (do not interrupt mid-handling). Checkpoint working state to `.squidsquad/<role>/working-state.md`. Stop the Monitor tool. Emit `ack` for the `stop-requested` event. Agent process exits. Does NOT reboot. Does NOT continue cycling.

### CQ-4: What is the source of truth for an assigned-to event's work context?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: The forge (GitHub Issues/PRs). The `assigned-to` payload only contains `{role, issue_or_pr}`. All context — comments, status, history, findings — lives in the GitHub Issue or PR. Agent reads the forge when it receives the event, not the event payload. Events are routing signals, not context carriers.

### CQ-5: What are the 5 event types and their payloads?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: `assigned-to {role, issue_or_pr}`, `stop-requested {source, target}`, `shipped {issue_or_pr}`, `version-bump {version}`, `ack {event_id}`. All L1 universal. No L2/L3 event-reaction sub-skills needed because roles already know how to handle issues from their existing role instructions.

### CQ-6: Can an agent be interrupted mid-event to handle a higher-priority event?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: No. Events are atomic — an agent completes the entire unit of work before picking up the next event. Monitor tool notifications naturally queue behind the current event. No interruption, even for stop-requested (which waits for the current event to finish).

### CQ-7: What happens if the agent does not ack an event within the timeout?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: Harness re-emits the event (retry_count increments). After `event-max-retries` retries (default 3), harness declares the agent dead, kills the PID, reboots the agent, and re-emits the event to the rebooted agent. If reboots also fail, harness escalates to PM.

### CQ-8: What scan cooldown applies between improvement scans?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: 15 minutes (default, L1). Overridable via `config.md → Event Driven → Scan Cooldown Minutes`. First scan after going idle happens immediately (no initial cooldown). Subsequent scans are separated by the cooldown. Issue gate: scan does not fire if open issues exist for the role.

### CQ-9: How does the external activity detector decide what is "not SquidSquad's own work"?
- **Files**: Harness documentation or composed agent instructions referencing the detector
- **Expected**: Filters by `squidsquad` label (issues/PRs) and agent commit prefix pattern (`skill:`, `pm:`, `qa:`, `dm:`). Activity matching either filter is ignored. Activity without these markers triggers `assigned-to` for PM. This prevents event loops from SquidSquad's own GitHub activity.

### CQ-10: What are the 5 configurable Event Driven fields in config.md?
- **Files**: `references/scripts/config.py`, `config.md`
- **Expected**: `event-timeout-minutes`, `event-max-retries`, `event-poll-interval`, `event-queue-cap`, `scan-cooldown`. These are the only 5 valid fields in the `## Event Driven` section. There is no `event-driven` toggle and no `event-sensitivity` field.

### CQ-11: What does the ack of a stop-requested event signal to the harness?
- **Files**: `references/sub-skills/common/event-driven-workflow.md`
- **Expected**: Harness treats the `ack` of a `stop-requested` as shutdown confirmation. Agent stopped as requested. Harness does NOT reboot the agent (intent = stopping). No separate `stopped` event is needed — `ack` is the universal closure mechanism that also serves as stop confirmation.

### CQ-12: How does an agent in a clone directory discover the harness port?
- **Files**: `references/scripts/event_bus.py`, `references/scripts/event_bus_reader.py`
- **Expected**: Agent reads `.harness-port` from the clone's local `.squidsquad/` directory. Harness distributes this file to each clone at boot (deferred init). No parent-directory walk needed. The direct path always works for clone agents.
