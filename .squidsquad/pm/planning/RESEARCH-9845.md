# RESEARCH-9845 — noop Event Type for Harness/Event-Mode Stress Testing

**Issue**: #9845
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

There is no side-effect-free event type that operators can emit on demand to probe
harness event delivery end-to-end. Intermittent 5-second harness stalls observed
in cycles 1535–1539 are currently undiagnosable because there is no way to isolate
whether the delay is in emit→storage, storage→poll, poll→agent, or agent→ack. A
`noop` event type would provide a measurable, zero-side-effect signal for all four
of these: burst-stress testing, per-agent latency probing, and E2E validation after
the event-mode flip.

---

## 2. Current State

### 2.1 Event Catalog — where to register noop

`references/scripts/event_catalog.py` defines a three-tier model:

- **EMITTED** (lines 26–87): mechanically emitted by scripts. Ground truth.
- **RECOGNIZED** (lines 91–143): planned/expected; referenced by filters; not yet
  emitted. Validated by `is_valid()` at ingestion.
- **unknown**: rejected at ingestion (harness logs and drops).

`noop` does not exist in either tier today. If emitted without registration, the
harness would log it as unknown (no current hard-reject — `is_valid()` is called
by `event_validator.py` but `POST /events` in harness.py does NOT call
`event_catalog.is_valid()` at the ingestion boundary; it only rejects unknown
roles, not unknown event types). **Key finding**: the catalog is advisory, not
enforced at the HTTP boundary. An unknown event type is stored and delivered just
fine today. The catalog governs documentation and filter configuration — not
storage gatekeeping.

### 2.2 Event Emission Path (emit→storage)

`event_bus.emit()` (`references/scripts/event_bus.py` lines 85–125):

1. Discovers harness port via `.squidsquad/.harness-port`.
2. Builds JSON envelope with `id`, `event_type`, `role`, `timestamp`, `payload`.
3. POSTs to `http://127.0.0.1:{port}/events` with a **500ms timeout**.
4. Silent no-op on any failure — fire-and-forget.

Harness `POST /events` (`harness.py` lines 1470–1565):

1. Validates `event_type` and `role` fields are present.
2. Rejects unknown roles (204 No Content — not a 4xx).
3. **Stamps `received_at` with `time.time()`** (line 1509) — this is the
   harness-side wall-clock timestamp at ingestion. The emit-side `timestamp` field
   uses `datetime.now().isoformat()` (second resolution). `received_at` is
   float-precision epoch: this is the field a latency tool must read.
4. Stores via `event_lifecycle.append(body)`.
5. Handles special event types (`bootup-complete`, `ack`) — all others are stored
   and returned without side effects.

### 2.3 Ack Mechanism Reality Post #9813 — CRITICAL FINDING

The issue body assumes agents can "ack" a noop event. The actual ack path is
substantially changed:

**Pre-#9741**: `GET /events/for/{role}` called `event_lifecycle.dispatch()` which
populated `_in_flight` per role. An agent completing an event would POST
`/events/{event_id}/complete` or emit an `ack` event type, which called
`event_lifecycle.ack()` to remove from in-flight.

**Post-#9741** (harness.py lines 1675–1681):
> "#9741: dispatch() call stripped — endpoint is a pure filtered-read with no
> lifecycle side effects. The agent-side ack stub (event_bus.ack) was also removed
> in #9813 since it had no live producer after this."

**Current state**:
- `GET /events/for/{role}` is a pure read. No dispatch. Nothing goes in-flight.
- `event_bus.ack()` was deleted in #9813. There is no `ack()` function in
  `event_bus.py` today.
- `POST /events/{event_id}/complete` still exists (harness.py lines 1691–1746)
  and calls `event_lifecycle.ack()`. But it returns HTTP 410 ("gone — not
  in-flight") for any event that was never dispatched — which is now every event,
  since `dispatch()` is dormant (lines 628–644: the function exists but is marked
  "not yet wired into POST /events — Phase 4 plumbing. Currently dormant").
- The **de-facto ack signal** is the cursor advance in `event_poll.py`: when
  `event_poll.py` writes the event ID to `working-state.md`, that is how the
  agent signals "I received this event." There is no HTTP call back to the harness.

**Implication for #9845**: "agent acks an event" must be redefined. Latency from
emit to cursor-advance is what is measurable. The cursor advance happens in
`event_poll.py` (`_write_cursor_atomic`, lines 96–131) immediately before the
event is printed to stdout — the agent hasn't even processed it yet. What is
measurable is emit→cursor-advance-in-working-state.md, not emit→agent-processing-
complete.

### 2.4 Poll Path (storage→agent)

`event_poll.py --wait` runs in Monitor, long-polling `GET /events/for/{role}` with
a configurable HTTP timeout (default 5s via `--wait 5`). The 5-second stalls
observed in cycles 1535–1539 match exactly the `--wait 5` poll timeout: if the
harness returns an empty response, `event_poll.py` sleeps `http_timeout` seconds
(line 360: `time.sleep(http_timeout)`) before the next poll. A 5s stall is
consistent with an empty-batch cycle during which no new events arrived.

### 2.5 Role Filtering — noop delivery

`GET /events/for/{role}` filters events two ways (harness.py lines 1660–1666):

1. `payload.target_role == role` — direct targeting.
2. `event_type` in the role's `reacts-to` list from `config.md` `## Event
   Reactions`.

For noop to be delivered to all agents (for stress-test purposes), it must either
(a) be added to all roles' `reacts-to` lists in `config.md`, or (b) be emitted
with `target_role: <role>` per probe. The CLI must handle this.

### 2.6 Agent Contract Location

The "ack and do nothing" instruction lives in agent CLAUDE.md files, which are
composed from role templates + sub-skills via `compose.py`. The compose pipeline
is the only source per memory rule `feedback_l1_l4_only`. The correct fragment for
event-mode reaction rules is `references/sub-skills/common-events/l1-base.md`.

The relevant section is **Case E — Special events** (l1-base.md lines 80–84):
> - **Unknown event type** — log a warning to stderr. Do not block.

Today, `noop` would be treated as an unknown event type by agents — they would log
a warning and do nothing. That is actually close to the desired behavior. The
difference: the issue wants agents to explicitly "ack" (cursor advance still
happens automatically). The current unknown-event path already satisfies "do
nothing"; the gap is documentation/clarity, not behavior.

### 2.7 CLI Surface — harness_admin.py Does NOT Exist

The issue body proposes `python references/scripts/harness_admin.py ping`.
**harness_admin.py does not exist** in `references/scripts/`. No admin CLI exists.

Existing CLI surface:
- `squidsquad_cli.py` — agent lifecycle only (start/stop/restart/status/shutdown).
  No event-sending capability.
- `tracker.py` — GitHub Issues operations. No harness event operations.
- `diagnostics.py` — diagnostics, no event injection.
- `event_bus.py` — Python API, no CLI.

The ping/latency tool must be either (a) a new `squidsquad_cli.py ping` subcommand,
(b) a new standalone `references/scripts/harness_ping.py`, or (c) a new
`harness_admin.py`.

### 2.8 Latency Measurement Mechanism

To measure emit→cursor-advance latency, the tool needs to:

1. Emit a noop event with a known ID (or record `time.time()` at emit).
2. Record the `received_at` timestamp from `.squidsquad/.event-state.json` (the
   persistence file written by `event_lifecycle._persist()`, lines 665–686, which
   stores `events` list including `received_at`). Or poll `GET /events?event_type=noop`
   on the harness.
3. Watch `working-state.md` for cursor advance to the emitted event ID.
4. Compute delta: `cursor_advance_time - received_at`.

The `received_at` field is already in every stored event. The harness stores the
last 200 events to disk (line 672: `self._stream.get_recent(200)`). Reading
`.squidsquad/.event-state.json` is possible but fragile (concurrent writes by
harness). Polling `GET /events?event_type=noop&since=...` from the CLI is the
clean path.

The agent-side cursor advance timestamp is NOT directly observable without watching
`working-state.md` with polling. A simpler proxy: when the noop event exits the
poll loop (appears in Monitor stdout), that is the "agent received" timestamp. But
the CLI runs outside the agent — it cannot observe Monitor stdout.

**Practical measurement path**: CLI records `t0 = time.time()` before emit. CLI
then polls `GET /events?event_type=noop&since=<id>` waiting for the event to
appear (it should immediately, since harness stores on receipt). Delta to
`received_at` measures emit→harness-storage latency. For emit→agent-cursor-advance
latency, the CLI must watch `working-state.md` for cursor change — workable but
requires file polling. Alternatively, define a "response event": the agent emits a
`noop-ack` event (new catalog entry) immediately on seeing the noop, and the CLI
watches for it via `GET /events?event_type=noop-ack`. This is cleaner.

### 2.9 cycle_post.py — noop Accident Risk

`cycle_post.py` reads `cycle-output.json` and executes `status_transitions`,
`tracker_comments`, and commit/push. It does NOT react to event types — it only
processes `cycle-output.json`. A noop event arriving at an agent causes a Monitor
line to appear; the agent wakes, reads the event, and since the event carries no
tracker payload, there is nothing to transition or comment. **Risk is in the agent's
LLM interpretation**, not in mechanical scripts.

If an event-mode agent receives `noop` and is currently idle (Case B), it would:
1. Read the event.
2. Forge-read the referenced item — there is no referenced item in a noop payload.
3. `work_queue()` scan — picks up whatever is in the queue regardless.

So a noop mid-idle-cycle would incidentally trigger a `work_queue()` scan. If the
queue is empty, no harm. If a task is in the queue, the agent picks it up — this is
the normal idle-wake behavior, not a noop-specific risk. The "do nothing" contract
must be explicit in the agent instructions: receiving `noop` must NOT trigger
`work_queue()`. This is the core instruction change required.

---

## 3. Options

### Option A — New `noop` Event Type + New Harness Ping CLI + l1-base Fragment Patch

**Scope**:
1. Add `noop` to `event_catalog.py` RECOGNIZED tier with `planned_source: "operator/CLI"`.
2. Add a `noop-ack` event type to RECOGNIZED tier (agent emits in response, enabling
   RTT measurement).
3. Update `config.md` `## Event Reactions` to add `noop` to all roles' `reacts-to` lists.
4. Patch `l1-base.md` Case E: promote `noop` from "unknown event" to an explicitly
   handled special event — "read, emit `noop-ack` via `event_bus.emit()`, do nothing
   else."
5. Create `references/scripts/harness_ping.py` (or add `ping` to `squidsquad_cli.py`)
   with: `ping [--role R] [--count N] [--interval S]` that emits N noop events,
   waits for matching `noop-ack` events, and prints a per-event latency table.
6. CQ spec required: agent given only modified l1-base.md must correctly answer
   "what does an event-mode agent do when it receives a noop event?" — answer must
   include "emits noop-ack, does nothing else, does not run work_queue."

**Pros**:
- Full RTT measurement (emit→noop-ack).
- No ambiguity in agent behavior (explicit Case E entry).
- Catalog is authoritative — `event_catalog.py describe noop` gives operators context.
- The `noop-ack` event type gives the CLI a clean polling target.

**Cons**:
- Agent instruction change requires CQ spec + comprehension test (per
  `feedback_comprehension_tests_required`).
- `noop-ack` adds a second catalog entry and a compose cycle.
- In event mode, agent emitting `noop-ack` means one more HTTP call per probe —
  usually negligible but adds to the measurement.
- Requires compose pipeline run (`compose.py deploy-all`) to update all 4
  roles' CLAUDE.md files.

**Risk**: LOW. Noop is strictly additive; the only behavioral change is in the
"special events" handling which is the safest fragment to modify.

---

### Option B — No New Event Type; Use `target_role` to Probe Out-of-Band

Instead of a new event type, emit a probe event with a well-known payload field
(`"probe": true`) using an existing event type (e.g., a synthetic `cycle-start`).
Agents already handle `cycle-start` but it would need special-case handling in
the agent's cycle logic.

Alternatively, probe entirely out-of-band via a new harness endpoint (`GET
/events/probe/{role}`) that the harness processes internally without agent
involvement — measures harness→poll latency but not agent cursor latency.

**Pros**:
- No catalog change.
- No agent instruction change.
- Out-of-band endpoint is the simplest implementation.

**Cons**:
- Does not test the actual agent delivery path. An out-of-band harness endpoint
  measures harness internals, not agent behavior — not useful for diagnosing the
  5s stall (which is in the poll loop / Monitor path, not harness internals).
- Reusing an existing event type for probe purposes creates semantic ambiguity and
  risks triggering unintended agent reactions (e.g., a fake `cycle-start` could
  confuse agent state tracking if agents react to it).
- Does not satisfy the "E2E health canary" use case — a harness endpoint probe
  never traverses the agent event-poll path.

**Risk**: MEDIUM for semantic contamination; LOW if strictly out-of-band endpoint.

---

### Option C — noop Event Type Without noop-ack; Use working-state.md Polling for Latency

Same as Option A but skip the `noop-ack` agent response. The CLI measures
emit→agent-cursor-advance by watching `working-state.md` for the cursor to
advance to the noop event ID.

**Pros**:
- Fewer moving parts than A: no `noop-ack` catalog entry, no agent HTTP call.
- Cursor advance in `working-state.md` is the canonical "agent received" signal.
- Works in both polling mode and event mode (cursor advance is always performed
  by `event_poll.py`).

**Cons**:
- CLI file-watching is platform-specific and requires polling (no `inotify` on
  Windows without extra dependencies).
- Watching `working-state.md` from outside the agent process has a race window:
  `event_poll.py` advances cursor BEFORE emitting to stdout (before the agent
  processes the event at all). The "latency" measured is emit→poll-receipt, not
  emit→agent-processing.
- If multiple events arrive near-simultaneously, the cursor may advance past the
  noop ID before the CLI's watcher polls — measurement is lost.
- Requires knowing which agent clone's `working-state.md` to watch (clone
  isolation path from `.local-config`/`boot_remote`).

**Risk**: LOW for correctness; MEDIUM for implementation complexity (cross-platform
file watching).

---

## 4. Recommended Option

**Option A** — new `noop` event type + new `harness_ping.py` CLI + l1-base.md
Case E patch + `noop-ack` response type.

Reasons:
- The RTT measurement (emit→noop-ack) is the only path that exercises the complete
  agent delivery pipeline: operator emit → harness storage → `event_poll.py` poll
  → Monitor wake → agent processing → `event_bus.emit(noop-ack)` → harness storage
  → CLI polls for noop-ack. The 5s stalls are in this path; only a full RTT probe
  diagnoses them.
- Option B does not test the agent path. Option C has cross-platform file-watching
  issues and measures the wrong latency point.
- The agent instruction change is minimal (one Case E bullet) and the change is
  strictly in the "special events" block which has low blast radius.
- The `noop-ack` event type is also useful as a general-purpose "agent is alive
  and processing events" canary independent of task state.

**Deviation from issue body**: The issue body proposes `harness_admin.py`. That
file does not exist. The recommended home is either:
(a) a new standalone `references/scripts/harness_ping.py` (clean separation, easy
to find, matches the pattern of `event_poll.py`, `event_bus.py`), or
(b) a new `ping` subcommand in `squidsquad_cli.py` (keeps all operator-facing CLI
in one file). Preference for (a) because `squidsquad_cli.py` is lifecycle-only
by current contract and mixing in event probing would broaden its scope.

---

## 5. Open Questions for PM/Human

1. **Latency definition**: what does "emit→ack latency" mean for this project? The
   options are:
   - emit `time.time()` → `received_at` in harness (measures network/asyncio delay):
     always <500ms or event_bus.emit() silent-fails.
   - `received_at` → `noop-ack.received_at` (measures full agent RTT from harness
     perspective): this is the most useful for diagnosing the 5s stalls.
   - `received_at` → working-state.md cursor advance (measures poll receipt,
     before agent processing): see Option C notes.
   
   **Recommendation**: use `noop` `received_at` → `noop-ack` `received_at` as
   the canonical latency metric. Both values are in `.event-state.json` / harness
   event stream. CLI just reads `GET /events?event_type=noop-ack&since=<id>` and
   computes delta.

2. **Polling-mode agents**: noop is only meaningful in event-mode (agents in
   polling mode are not driven by the event stream). Should polling-mode agents
   silently ignore noop (cursor advance still happens in `event_poll.py` if they
   run it), or should the CLI refuse to target a polling-mode role? **Impact**: if
   a role is `event-driven: no` in config.md, it may not have Monitor running
   and `event_poll.py` may not be active — noop events would accumulate in the
   stream but never be cursor-advanced. The CLI should check the role's wake mode
   before probing.

3. **noop delivery mechanism — `target_role` vs `reacts-to`**: should noop
   be delivered via `payload.target_role` (per-probe targeting, no config.md
   change needed) or via the `reacts-to` list (always delivered, requires
   config.md + compose update for all roles)?
   - `target_role` approach: CLI sets `target_role=<role>` in the noop payload.
     No config.md change, no compose cycle. Simpler scope.
   - `reacts-to` approach: noop is always in every role's filter. Enables future
     harness-emitted noops (health canary scenario) without per-emit targeting.
   **Recommendation**: start with `target_role` for the ping tool (simpler), and
   defer the `reacts-to` config addition to a future "ambient canary" task.

4. **noop-ack emitter identity**: when an event-mode agent emits `noop-ack`, what
   role does it use? The agent's own role. The CLI must track `(noop_id, role)` →
   `noop-ack` correlation. This works if noop events carry a `probe_id` in the
   payload that the agent echoes in the `noop-ack` payload — needed when N noops
   are in-flight simultaneously.

5. **Sequencing vs fleet flip**: the issue says "ship before flipping event-driven:
   yes." This implies the noop infrastructure must be usable before any agent is
   in event mode. The harness storage and CLI are mode-agnostic; only the `noop-ack`
   response requires an event-mode agent. Is it acceptable to ship the CLI (emit +
   wait-for-ack) before the fleet flip, knowing that `noop-ack` responses will only
   arrive after the flip? Or should the CLI also have a mode that just emits without
   waiting for a response (latency = emit→harness-storage only, no RTT)?

6. **CQ spec scope**: the comprehension question should test:
   - That the agent does NOT run `work_queue()` on receiving noop.
   - That the agent emits `noop-ack` (if Option A) or does nothing (if not).
   - That the agent does NOT post a tracker comment or status transition.
   This is a behavioral boundary — the CQ spec is non-trivial and should explicitly
   name the actions the agent must NOT take.

---

## 6. Out of Scope

- **Diagnosing the root cause of the 5s stalls**: this task ships a diagnostic tool;
  root cause analysis is a follow-on task after data collection.
- **Polling-mode latency measurement**: `event_poll.py` in non-`--wait` mode
  (single-shot polling) is not the 5s-stall path. This feature targets event-mode
  agents only.
- **`dispatch()` re-activation**: the dormant dispatch/in-flight path in
  `EventLifecycleManager` is explicitly out of scope. Reactivating it would require
  a separate issue (large scope, Phase 4 plumbing per original #7630 design).
- **`POST /events/{event_id}/complete`**: this endpoint exists but returns 410 for
  all events since `dispatch()` is dormant. A noop ack via this endpoint is not
  viable without reactivating dispatch. Out of scope.
- **Harness-emitted ambient canary** (periodic noop from harness health poller):
  useful follow-on but separate from the operator-CLI probe.
- **Per-role reacts-to config changes**: deferred to the ambient canary task.
- **Windows-specific file-watching latency measurement**: Option C rejected; no
  platform-specific file-watching tooling needed.
