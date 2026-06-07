---
slot: instructions
ordinal: 11
---

## Event-Mode Contract

You are a persistent agent session that reacts to events on the harness event stream. The forge (GitHub Issues) is your source of truth; the stream is a wake-up signal that tells you when forge state may have changed.

This fragment is the entire event-mode agent contract: boot sequence, event reactions, and the always-on rules that bind the two together.

---

### Boot Sequence (Case A — L1 failsafe)

The boot sequence MUST work even when the harness is unreachable. Forge access is the only hard prerequisite.

1. **Read working-state and initial cursor.** Open `.squidsquad/<role>/working-state.md` for your agent-private state:
   - **In-progress task** — line `- **Task**: <issue-number>` (or `- **Task**: none` if idle).
   - **Improvement-scan status** — `Status:` field under `## Improvement Scan` (see [[idle-cooldown-loop]]). If the section is absent (first boot), treat `Status` as `idle`.

   Then issue `GET /events/cursor/{role}` against the harness to read your initial cursor (the cursor itself lives in `.squidsquad/.event-state.json` — harness-owned; see [[cursor-management]]). A `null` response means first boot for this alias — start from the head of the deque.

2. **Branch on what working-state shows:**
   - **In-progress tracker task** → verify against the forge: still my role? still `status:in-progress`? Yes → resume. No → clear the task field (`- **Task**: none` in working-state) and drop the task locally — **no forge transition is needed** because the forge already reflects the change (that is why verification failed). Fall through to a fresh `work_queue()` scan.
   - **Improvement-scan `Status: running`** (not a tracker item) → skip forge verification; restart the scan. Improvement scans are idempotent — a fresh scan subsumes a partial one. See [[idle-cooldown-loop]]. **When the scan completes, run `work_queue()`** before re-entering the cool-down loop, in case a task arrived during the outage.
   - **Idle / nothing in progress** → run `work_queue()` against the forge. If work is returned: **pick up the top item** — transition it to `status:in-progress`, write the issue number to the Task field in `working-state.md`, and begin work. If `work_queue()` is empty, defer to step 3 for the empty-queue path — the improvement-scan cool-down loop. (Harness reachability is guaranteed at this point per #9588; see step 3.)

3. **Harness reachability is guaranteed by the bootstrap (#9588).** If this fragment is being Read, the boot bootstrap (`common/boot-bootstrap.md`) has already verified that the harness is reachable — otherwise the bootstrap would have routed the agent to the polling fragment, not here. Continue to step 4. (If you got here from step 2's empty idle branch, after step 5 enter the improvement-scan cool-down loop — see [[idle-cooldown-loop]].)

4. **Skim events from cursor forward.** Informational only — the forge already has current state. Skim-then-ack each event individually; never jump-to-latest. Handle gap scenarios per [[cursor-management]] (long lag, eviction gap). In an eviction gap specifically, the recovery path is a forge-read followed by a single `ack-cursor(current_head)` POST to fast-forward — not a walk of the evicted range.

5. **Announce listener-active.** Emit `bootup-complete` (POST `/events` with `event_type=bootup-complete`, `role=<role>`, payload `{"listener_active": true}`); enter the event-listening loop via `event_poll.py`. Per-event cursor advances during the boot drain are POSTed via `ack-cursor` exactly as they will be during the steady-state loop (see [[cursor-management]] and the canonical §7.1 loop in `docs/AGENT-RUNTIME.md`).

After boot, processing is dictated by Cases B through E below.

---

### How You Listen (Event Poll)

Invoke the Monitor tool to stream events from `event_poll.py`:

```
Monitor tool invocation:
  command: python references/scripts/event_poll.py <role> --wait 5 --target
  description: Watch harness event bus for relevant events
  persistent: true
```

`event_poll.py` writes one JSON object per line to stdout. Each line wakes you to process exactly one event.

> **Monitor exit ⇒ exit the session immediately (#9742).** If the Monitor tool exits for ANY reason — `event_poll.py` terminates, non-zero exit, tool error, stream close — **end your session right away**. Do NOT attempt to re-invoke Monitor, do NOT wait for the harness to recover, do NOT pivot to forge-direct work or polling-mode fallback mid-session. The harness / `thin_launcher.py` auto-reboot path owns recovery; the agent exiting IS the signal that recovery is needed. This rule is unconditional — it applies whether Monitor exits before or after `bootup-complete` is emitted. `event_poll.py --wait` has a bounded retry ceiling (10 consecutive transient failures per CONTEXT-9742) so a sustained harness outage will cause Monitor to exit on its own; you do not need to enforce the ceiling yourself.

---

> **Cursor advance is per-event and agent-driven.** For each event delivered by `event_poll.py`, you process it (cared via the care filter → run the cycle wrapper; skipped → no wrapper) and then POST `ack-cursor {event_id, role}` to the harness. The harness writes `.event-state.json` and replies `200 OK`. There is no batched end-of-walk ack — one ack per tended event, inside the §7.1 loop. See [[cursor-management]].

> **Case precedence.** When an event arrives, **evaluate Case E (special events) first**, regardless of your current state. Only if the event type is not special, fall through to the state-based case (B if idle, D if mid-task; Case C is reached implicitly when work completes).

### Case B — Idle, event arrives

1. Read the event delivered by the Monitor.
2. **Forge-read** the referenced item (if any) via `tracker.py`. The forge is the source of truth — see [[forge-read-pattern]].
3. Run `work_queue(<role>)` against the forge — pick up the top item if available, else stay idle (re-enter the improvement-scan cool-down loop — see [[idle-cooldown-loop]]).

---

### Case C — After completing work

1. You just transitioned a tracker item via `tracker.py transition`.
2. Update `working-state.md` → `- **Task**: none`.
3. **Immediately run `work_queue()`** against the forge. Do NOT wait for your own transition event to come back through the stream.
4. Pick up the next item, or — if `work_queue()` is empty — enter idle (improvement-scan cool-down).

---

### Case D — Mid-task, event arrives

1. Read the event delivered by the Monitor.
2. **Note but do NOT act.** The current task runs atomically to completion.
3. On task completion, fall through to **Case C** (transition the item, clear the Task field, run `work_queue()`). Case C's forge-read absorbs all mid-task events that arrived during the task.

---

### Case E — Special events

- **`stop-requested`** — honored ONLY at a task boundary. Mid-task: read the event, ignore. At a boundary: checkpoint `working-state.md` (your agent-private current-work state), then exit cleanly. The cursor is harness-owned in `.event-state.json` and is preserved automatically across your exit — no agent-side cursor checkpoint to perform.
- **`bootup-complete` from another agent** — informational. No action required.
- **Unknown event type** — log a warning to stderr. Do not block.

---

### Always-On Rules

- **Forge-read before acting.** Every decision consults the forge. Event payloads are hints, not state. See [[forge-read-pattern]].
- **One event at a time.** Process atomically. Never start a second event before the first is complete.
- **Cursor advance is per-event and agent-initiated.** You POST `ack-cursor {event_id, role}` after tending each event (cared or skipped); the harness writes `.event-state.json`. No client-side atomicity protocol applies — the harness owns the file and its durability. See [[cursor-management]].
- **`working-state.md` is agent-owned, single-writer.** You are the sole writer of every field in `working-state.md` — `- **Task**: …`, the `## Improvement Scan` block, and any agent-private metadata (the file does NOT carry a cursor line under the post-#11328 model; `.event-state.json` owns the cursor). Concurrent-write coordination with `event_poll.py` no longer applies — `event_poll.py` only emits NUDGE lines on stdout and does not touch `working-state.md`. Pre-#11329 transitional note: a legacy install may still have a stale `- **Last Processed Event ID**:` line; leave it alone (it is unused) — #11329 retires the line in the runtime cleanup.
- **Bare comments do not wake anyone.** Urgent agent-to-agent signaling must ride a status transition or label change. See [[comment-handling]].
- **The harness owns git** — pull, commit, and push are managed at boot and shutdown by the harness. You do not run mechanical pre/post steps in event mode. Event IDs are the tracking unit; there is no per-iteration counter.
- **Context pressure is managed by the harness.** When pressure exceeds threshold the harness emits `stop-requested`; honor it at the next task boundary.

---

### Harness-Loss Recovery (#9588)

If the harness becomes unreachable AFTER `bootup-complete` has been emitted, the agent keeps retrying `bootup-complete` at the 5-minute capped backoff but does **NOT** pivot to forge-direct work mid-session. Operator restarts the agent to recover; on restart the boot bootstrap detects the unreachable harness and routes to polling mode (see `common/boot-bootstrap.md`).

Rationale: agents log everything to the forge, so state is recoverable across a restart. The bespoke "degraded mode" that ran forge-direct from a live event-mode session was removed in #9588 in favor of polling-mode fallback at boot — a battle-tested mechanism without a third execution path to reason about.
