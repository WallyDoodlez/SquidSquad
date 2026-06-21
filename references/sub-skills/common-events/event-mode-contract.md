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

1a. **Legacy-cursor migration (one-time, #11329).** If `working-state.md` still contains a `- **Last Processed Event ID**: <id>` line with a real id (not `none`/empty), this is a pre-#11329 (model-A) install where the cursor lived in `working-state.md` instead of the harness. Migrate it once:
   - If the `GET /events/cursor/{role}` above returned `null` (or an id the harness places earlier than `<id>`), POST a single `ack-cursor {event_id: <id>, role}` to seed the harness cursor — so you resume where model A left off rather than re-walking the whole retained deque.
   - Then **remove the legacy line** from `working-state.md` on your next working-state write (the model-B template no longer carries it).
   - **Idempotent**: on a fresh or already-migrated install (no such line), this step is a no-op. Skip it entirely.
   - **Safety net**: this migration is an optimization, not a correctness gate. Even if it is skipped, the §8.1 walk forge-reads each event (authoritative) and acks past already-tended ones — so the only cost of skipping is one wasteful re-walk of the retained deque, never duplicated work on the forge.

2. **Branch on what working-state shows:**
   - **In-progress tracker task** → verify against the forge: still my role? still `status:in-progress`? Yes → resume. No → clear the task field (`- **Task**: none` in working-state) and drop the task locally — **no forge transition is needed** because the forge already reflects the change (that is why verification failed). Fall through to a fresh `work_queue()` scan.
   - **Improvement-scan `Status: running`** (not a tracker item) → skip forge verification; restart the scan. Improvement scans are idempotent — a fresh scan subsumes a partial one. See [[idle-cooldown-loop]]. **When the scan completes, run `work_queue()`** before re-entering the cool-down loop, in case a task arrived during the outage.
   - **Idle / nothing in progress** → run `work_queue()` against the forge. If work is returned: **pick up the top item** — transition it to `status:in-progress`, write the issue number to the Task field in `working-state.md`, and begin work. If `work_queue()` is empty, defer to step 3 for the empty-queue path — the improvement-scan cool-down loop. (Harness reachability is guaranteed at this point per #9588; see step 3.)

3. **Harness reachability is guaranteed by the bootstrap (#9588).** If this fragment is being Read, the boot bootstrap (`common/boot-bootstrap.md`) has already verified that the harness is reachable — otherwise the bootstrap would have routed the agent to the polling fragment, not here. Continue to step 4. (If you got here from step 2's empty idle branch, after step 5 enter the improvement-scan cool-down loop — see [[idle-cooldown-loop]].)

4. **Drain events from cursor forward.** Issue `GET /events/for/{role}?since=<cursor>` against the harness and walk the returned events through the canonical §8.1 loop: care filter → cycle wrapper if cared → POST `ack-cursor` per event. Boot-drain events typically reflect forge state you can also discover via `tracker.py`, so the cycle wrapper's work is usually a no-op for cared events, but the loop discipline still applies — never jump-to-latest. Handle gap scenarios per [[cursor-management]] (long lag, eviction gap). In an eviction gap specifically, the recovery path is a forge-read followed by a single `ack-cursor(oldest_id)` POST to fast-forward — not a walk of the evicted range.

5. **Announce listener-active.** Emit `bootup-complete` (POST `/events` with `event_type=bootup-complete`, `role=<role>`, payload `{"listener_active": true}`); enter the event-listening loop via `event_poll.py`. Per-event cursor advances during the boot drain are POSTed via `ack-cursor` exactly as they will be during the steady-state loop (see [[cursor-management]] and the canonical §8.1 loop in `docs/AGENT-RUNTIME.md`).

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

`event_poll.py` writes a single literal `NUDGE\n` line (no payload) to stdout whenever events arrive past your cursor. A `NUDGE` is a wake signal only — it never carries event data. On each `NUDGE` you do your own `GET /events/for/{role}?since=<cursor>` and walk the returned events through the §8.1 loop (one `ack-cursor` POST per event). False-positive nudges are harmless: the GET simply returns `[]` and you idle again.

> **Monitor exit ⇒ exit the session immediately (#9742).** If the Monitor tool exits for ANY reason — `event_poll.py` terminates, non-zero exit, tool error, stream close — **end your session right away**. Do NOT attempt to re-invoke Monitor, do NOT wait for the harness to recover, do NOT pivot to forge-direct work or polling-mode fallback mid-session. The harness / `thin_launcher.py` auto-reboot path owns recovery; the agent exiting IS the signal that recovery is needed. This rule is unconditional — it applies whether Monitor exits before or after `bootup-complete` is emitted. `event_poll.py --wait` has a bounded retry ceiling (10 consecutive transient failures per CONTEXT-9742) so a sustained harness outage will cause Monitor to exit on its own; you do not need to enforce the ceiling yourself.

---

> **Cursor advance is per-event and agent-driven.** For each event returned by your `GET /events/for/{role}?since=<cursor>`, you process it (cared via the care filter → run the cycle wrapper; skipped → no wrapper) and then POST `ack-cursor {event_id, role}` to the harness. The harness writes `.event-state.json` and replies `200 OK`. There is no batched end-of-walk ack — one ack per tended event, inside the §8.1 loop. See [[cursor-management]].

> **Case precedence.** For each event you take from your GET response, **evaluate Case E (special events) first**, regardless of your current state. Only if the event type is not special, fall through to the state-based case (B if idle, D if mid-task; Case C is reached implicitly when work completes).

### Case B — Idle, event arrives

1. The `NUDGE` woke you — `GET /events/for/{role}?since=<cursor>` to fetch the event(s) and take the next one.
2. **Forge-read** the referenced item (if any) via `tracker.py`. The forge is the source of truth — see [[forge-read-pattern]].
3. Run `work_queue(<role>)` against the forge — pick up the top item if available, else stay idle (re-enter the improvement-scan cool-down loop — see [[idle-cooldown-loop]]).

---

### Case C — After completing work

1. You just transitioned a tracker item via `tracker.py transition`.
2. Update `working-state.md` → `- **Task**: none`, **and write the `current-state` idle marker** (`python references/scripts/cycle.py status-bar-self idle ""`) per **Keep `current-state` honest** in Always-On Rules — the task you just closed must no longer read as your current activity (#12854).
3. **Immediately run `work_queue()`** against the forge. Do NOT wait for your own transition event to come back through the stream.
4. Pick up the next item — **writing its marker as you start it** (per **Keep `current-state` honest**) — or, if `work_queue()` is empty, enter idle (improvement-scan cool-down) with the `idle` marker from step 2 standing.

---

### Case D — Mid-task, event arrives

1. A `NUDGE` arrived mid-task. You may leave it unread — the event sits past your cursor and your post-task `GET /events/for` (Case C) will surface it.
2. **Note but do NOT act.** The current task runs atomically to completion.
3. On task completion, fall through to **Case C** (transition the item, clear the Task field, run `work_queue()`). Case C's forge-read absorbs all mid-task events that arrived during the task.

---

### Case E — Special events

- **`stop-requested` (intent-driven — NOT a bus event).** A stop/restart is signalled by the harness flipping `intent` to `stopping`/`restarting`, **not** by a deque event — the `stop-requested` type is reserved/never-emitted (AGENT-RUNTIME §5.2), so there is nothing on the deque to react to. Honor it at a task boundary: checkpoint `working-state.md` (your agent-private current-work state), then **halt — cease output and end your turn**. You cannot terminate your own process (an LLM agent can only stop emitting output, not execute a real `/quit` — #13077); the harness's 60-second force-kill net (armed on the `stopping`/`restarting` intent) terminates your process and marks you stopped per the intent state machine.
  - **Do NOT emit `ack-stop` on this path.** Unlike the deploy-halt path below (which emits `ack-stop(result="deploy-halted")` so the harness runs a deploy instead of reading the exit as a crash), the stopping path emits no cooperative confirm today: the `ack-stop.result` enum IS settled (`checkpointed`/`aborted`/`drained` — AGENT-RUNTIME §10 Q11, closed 2026-05-30), but **no agent-side code emits a stop `ack-stop`**, and the 60s force-kill net is the termination mechanism. Emit nothing here unless/until such an emission is implemented.
  - **Nothing to `ack-cursor`.** The trigger is the intent flip, not a deque event, so there is no event id to ack. The cursor is harness-owned in `.event-state.json` and preserved automatically across your exit — no agent-side cursor checkpoint to perform; on any later restart you re-evaluate `intent`, you do not replay a stop event.
- **`deploy-signal`** (`event_type == "deploy-signal"`) — the harness detected compose-source drift and wants a coordinated halt so it can run the pull-first deploy sequence (recompose your `CLAUDE.md` from current `origin/main` source). A deploy-signal rides the `assigned-to` plumbing with `target_alias == your alias`, so it passes the care filter as "cared" — but you branch on `event_type` **before** the normal work wrapper and route it here, NOT to work pickup. Handle it as follows:
  - **Honor it only at a between-task boundary where you are back on `main` with a clean working tree** — never mid-task and never mid-feature-branch. In the eager loop you only read the deploy-signal as the next event *after* finishing your current atomic unit, so you are normally already between tasks when it surfaces. If you still have an in-flight task (e.g. a worker on a feature branch with unmerged work), **finish that task to its normal handoff first** — complete it, transition it, and return to `main` (your task-end step) so the tree is clean — and only then honor the deploy halt.
  - **A deploy-signal in your *boot drain* is legitimate — honor it; do NOT dismiss it as stale "residual restart telemetry."** On a full-team or operator restart the harness emits this signal (the boot-drift path — `_emit_boot_deploy_signals` / HARNESS-ARCH §10 step 1b) to every running agent whenever it cannot confirm your `CLAUDE.md` is current: its stored compose-checksum is absent or drifted from `origin/main`. In the common restart-while-idle case the boot drain runs before any new task pickup, so you **already** satisfy the on-`main`/clean-tree precondition above — honor it the moment you reach it in the drain (`ack-stop(deploy-halted)` → halt, per the steps below; the rest of the drain and `bootup-complete` happen on your respawned session). (If your boot instead **resumed an in-progress task** onto a feature branch before draining, the precondition is not yet met — apply the finish-first rule from the bullet above: complete and hand off that task, return to `main`, and only then honor the deploy halt.) Two traps to avoid:
    - **Do NOT self-assess drift from your local clone and skip.** Your clone may be behind `origin/main` — pull-first deploy exists precisely for this — so "no `references/` drift locally" does NOT prove your `CLAUDE.md` is current. The harness's stored-checksum comparison is authoritative; honor the signal and let the deploy sequence pull + recompose.
    - **Do NOT `ack-cursor` past it to stop the re-NUDGE.** Honoring is loop-free: the deploy sequence advances your cursor past the signal up front (before respawn), and a no-op recompose (output already current) is a clean idempotent success — checksum bumped, you respawn on your existing `CLAUDE.md`, no spurious `deploy-error`. A manual `ack-cursor` skip is the **one** path that can leave a genuinely-stale `CLAUDE.md` in place. (On this boot-drift path the emit side does not pre-set `intent=DEPLOYING`; the harness establishes it synchronously when it receives your `ack-stop`, so the imminent PID death is still not misread as a crash.)
  - At the boundary, emit `ack-stop` with `result="deploy-halted"`: `POST /events` with `event_type="ack-stop"`, top-level `role=<your alias>`, payload `{event_id: <the deploy-signal's event id>, result: "deploy-halted", role: <your alias>}`. This tells the harness you are halting for a deploy (NOT crashing), so it runs the deploy sequence instead of treating your exit as a crash.
  - Then **halt — cease output and end your turn**: stop all agent work (do NOT pick up new work, do NOT enter the improvement-scan cool-down loop) and **do NOT `ack-cursor` the deploy-signal** (the harness advances your cursor past it as part of the deploy sequence, so your respawned session does NOT re-fetch and re-process it — without this you would re-halt and loop: deploy → respawn → re-halt → deploy …). You **cannot terminate your own process** — an LLM agent can only stop emitting output, not execute a real `/quit` (#13077); a best-effort `/quit` is fine as an end-of-turn marker but is **not** what makes the deploy work. **The harness owns termination here**: a deploy-halted agent sits at `status="deploying"`, which the 60s STOPPING/RESTARTING force-kill net does NOT cover, so the deploy sequence **actively force-kills your old `claude` process** (reaping the Monitor-spawned `event_poll` sidecar too, #12363) and **confirms it is gone** — and it is that confirmed kill, **not** any self-exit on your part, that satisfies `boot_agent`'s singleton guard so the fresh process can spawn. Your one job at the halt boundary is to stop cleanly so the force-kill lands on an idle process.
  - The harness then runs (your old process still alive but halted): ensure-on-`main` → `git pull` → `compose.py deploy <your alias>` → commit → push → advance your cursor → **respawn**, which **force-kills your old process, confirms its death, then boots a fresh one** on the newly-committed `CLAUDE.md`. Your fresh session boots reading that `CLAUDE.md` (it does NOT recompose at boot — AGENT-RUNTIME §8.2). Any nudges that arrived during the deploy window are delivered after you are `ready` and drained normally.
  - **Loop/polling-mode agents never consume a deploy-signal** — the bus is event-mode only. A loop-mode agent picks up the updated, already-committed `CLAUDE.md` at its next session start's pull (AGENT-RUNTIME §7.8). If you are in loop mode, this branch does not apply.
- **`bootup-complete` from another agent** — informational. No action required.
- **Unknown event type** — log a warning to stderr. Do not block.

---

### Always-On Rules

- **Forge-read before acting.** Every decision consults the forge. Event payloads are hints, not state. See [[forge-read-pattern]].
- **One event at a time.** Process atomically. Never start a second event before the first is complete.
- **Cursor advance is per-event and agent-initiated.** You POST `ack-cursor {event_id, role}` after tending each event (cared or skipped); the harness writes `.event-state.json`. No client-side atomicity protocol applies — the harness owns the file and its durability. See [[cursor-management]].
- **`working-state.md` is agent-owned for agent-authored fields.** You are the sole writer of `- **Task**: …`, the `## Improvement Scan` block, and any agent-private metadata. The cursor is NOT here: it lives in `.event-state.json` (harness-owned), and you read/advance it via the harness API exactly as described in [[cursor-management]]. `working-state.md` carries no cursor line.
- **Keep `current-state` honest** (`python references/scripts/cycle.py status-bar-self <phase> "<short description>"`). It is a health-diagnosis signal read by the statusline, the health poller, and teammates — not a file-age cadence artifact. Write it **on the transition**, across **every** work-pickup and idle path (boot pickup, Case B, Case C, and the idle-cooldown-loop's absorb-work tick): write the task's marker when you **start** an item, and the `idle` marker (`status-bar-self idle ""`) when you go idle or when a task you held is closed, handed off, or reassigned away. `current-state` must **never name a task that is no longer your current activity** — that lingering-stale content is the #12854 defect that makes a closed issue read as live and sends diagnosers down wrong root-cause paths. (The `idle` marker is distinct from the `inline` operator-session marker — `status-bar-self inline ""` — you self-write during a human turn; don't conflate them.)
- **Bare comments do not wake anyone.** Urgent agent-to-agent signaling must ride a status transition or label change. See [[comment-handling]].
- **The harness owns git** — pull, commit, and push are managed at boot and shutdown by the harness. You do not run mechanical pre/post steps in event mode. Event IDs are the tracking unit; there is no per-iteration counter.
- **Context pressure is managed by the harness lifecycle.** When pressure exceeds threshold the harness initiates a restart via the `restarting` intent — the same intent-driven path as `stop-requested` above; **no `stop-requested` event is emitted**. Honor it at a task boundary: checkpoint and halt; the 60s force-kill net terminates the process (you cannot self-`/quit`).

---

### Harness-Loss Recovery (#9588)

If the harness becomes unreachable AFTER `bootup-complete` has been emitted, the agent keeps retrying `bootup-complete` at the 5-minute capped backoff but does **NOT** pivot to forge-direct work mid-session. Operator restarts the agent to recover; on restart the boot bootstrap detects the unreachable harness and routes to polling mode (see `common/boot-bootstrap.md`).

Rationale: agents log everything to the forge, so state is recoverable across a restart. The bespoke "degraded mode" that ran forge-direct from a live event-mode session was removed in #9588 in favor of polling-mode fallback at boot — a battle-tested mechanism without a third execution path to reason about.
