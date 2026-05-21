# RESEARCH-9873 — Restore Event Ack-on-Delivery: Revert #9741+#9813 + Wire Proper Ack Semantic

**Issue**: #9873
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## §1 Problem Statement

The event bus was designed for at-least-once delivery with retry on no-ack. Two cycles stripped the infrastructure that implemented this guarantee without completing the missing connecting line:

- **#9741 (commit 017b65a3)** stripped `event_lifecycle.dispatch()` from `GET /events/for/{role}` because agents never sent acks. The endpoint became a pure filtered-read with no lifecycle side effects.
- **#9813 (commit 11a3d5d4)** deleted `event_bus.ack()` entirely, since without the dispatch() producer it was a dead stub. The function is fully gone — not stubbed.

Today's de-facto signal: `event_poll.py` writes the cursor to `working-state.md` per event, which is "delivered to the agent's transport." Processing success/failure is invisible to the harness. A crashed agent silently loses events. `timeout_scan()` runs every 30s but finds nothing (no in-flight entries exist post-#9741). `POST /events/{event_id}/complete` returns 410 for every call because no events are ever dispatched.

This is a pre-flip blocker. The event-driven fleet flip must not happen until at-least-once delivery is restored.

---

## §2 Current State

### 2.1 EventLifecycleManager (harness.py)

`references/scripts/harness.py` — `EventLifecycleManager` class:

- **`:628-644`** — `dispatch(event_id, role, event)`: marks event in-flight in `_in_flight[role]`, persists to `.event-state.json`. Method is **intact**. No callers in live code; only called from tests.
- **`:646-658`** — `ack(event_id, role) -> bool`: clears in-flight entry, persists. Method is **intact** on harness side. This is the harness-internal ack; it is not the deleted `event_bus.ack()`.
- **`:665-686`** — `_persist()`: atomically writes `.event-state.json`. No change.
- **`:742-788`** — `timeout_scan()`: scans `_in_flight` for entries past `timeout_minutes * 60`. On overdue, increments `_retry_counts[event_id]` and resets dispatch time. On `retries >= max_retries`, removes from in-flight and returns `(role, event_id)` pairs as timed-out. **Scanner runs**, but because `_in_flight` is always empty (dispatch stripped), it finds nothing and does nothing.
- **`:790-809`** — `start_timeout_scanner()` / `_scan_loop()`: background thread running every 30s. Confirmed running; confirmed harmless with empty in-flight.

### 2.2 GET /events/for/{role} (harness.py:1630-1688)

The dispatch loop was cleanly deleted at what was `harness.py:1674-1678`. Current code at **`:1675-1681`** is a comment explaining the deletion (references #9741 and #9813). The endpoint returns filtered events with no side effects.

### 2.3 POST /events/{event_id}/complete (harness.py:1691-1746)

Endpoint is **intact** and calls `event_lifecycle.ack(event_id, role)`. Since no events are ever dispatched, `ack()` always returns `False`, and the endpoint always returns `410 {"status": "gone", ...}`. The rich side-effect machinery (`_execute_transition`, `_execute_comment`) is intact but unreachable.

### 2.4 event_bus.py — ack() is gone

The agent-side `event_bus.ack()` function was **fully deleted** in #9813 (not stubbed). The deleted code was:
```python
def ack(event_id, role):
    """Acknowledge event completion — posts ack event to harness (#7630 2-6)."""
    if not event_id:
        return
    emit("ack", role, payload={"event_id": event_id})
```
It emitted an `"ack"` event_type via `emit()`. No harness route consumed `event_type == "ack"` directly — the ack was expected to land as a generic event in the stream, not to trigger lifecycle clearing. (The lifecycle clearing happens via `POST /events/{id}/complete`, not via the event stream.)

**Critical finding**: the deleted `event_bus.ack()` was not the right mechanism to clear harness-side in-flight state. It emitted to the event stream, but `event_lifecycle.ack()` is invoked by `POST /events/{id}/complete` — not by an event-type listener. These were always two separate paths. The agent-side ack needed to POST to `/events/{id}/complete`, not emit an `"ack"` event. This mismatch existed pre-#9741 and was never wired.

### 2.5 event_poll.py — cursor management

`references/scripts/event_poll.py:251-271` — per-event loop:
1. `_write_cursor_atomic(role, str(event_id))` — advance cursor in `working-state.md`
2. `print(json.dumps(event), flush=True)` — emit to stdout for Monitor

Cursor advance happens **before** stdout emit (per spec §3.5). There is **no ack POST** here today.

### 2.6 Tests — current state post-#9741

- `tests/test_harness.py:1951-1971` — `test_does_not_dispatch`: asserts e3 is NOT in `get_in_flight("skill")` after a delivery. **This is the inverted form** that must flip back.
- `tests/test_harness.py:1994-2019` — `test_endpoint_does_not_touch_lifecycle_state`: asserts read-only invariant. **This is the inverted form** that must flip back (or be replaced by the original dispatch-assertion logic).
- `tests/test_harness.py:2026-2134` — `TestCompleteEventEndpoint`: 6 tests covering the `/complete` endpoint. Each test calls `event_lifecycle.dispatch(...)` directly (not via the polling endpoint) to put an event in-flight, then posts to `/complete`. **These tests are unaffected** by the dispatch strip — they bypass the endpoint and call dispatch() directly. They remain coherent and will stay passing through this work.
- `tests/test_harness.py:1718-1755` — `TestTimeoutScanner`: tests `EventLifecycleManager.dispatch()` + `timeout_scan()` directly (not via the endpoint). **Unaffected by the strip; run today.** Already cover retry logic correctly.

### 2.7 Agent contract (sub-skills)

`references/sub-skills/common-events/event-driven-workflow.md` and `cursor-management.md` have no mention of POSTing to `/events/{id}/complete` or of any post-processing ack. The agent contract documents only cursor advance. If we add an ack POST to `event_poll.py`, no sub-skill update is strictly required for implicit ack (cursor-advance-as-ack) — but if we want agents to know they can optionally or must call `/complete`, the contract needs to say so.

---

## §3 Options

### Path A — Cursor-advance-as-implicit-ack (smaller diff)

Re-add `dispatch()` call at `GET /events/for/{role}` + add a fire-and-forget ack POST in `event_poll.py` after writing the cursor + re-implement `event_bus.ack()` (deleted, must re-add; the implementation is trivial from git history).

**Concrete diff:**

1. `harness.py`: Restore the 5-line dispatch loop at the point where the explanatory comment now sits (`:1675-1681`). Identical to the code deleted in commit `017b65a3`.
2. `event_poll.py`: After `_write_cursor_atomic(role, str(event_id))` succeeds at line 264, add a fire-and-forget call: `_post_ack(port, event_id, role)`. The ack POST goes to `POST /events/{event_id}/complete` with `{"role": role, "status": "success", "summary": "cursor-advance-ack"}`. Fire-and-forget: failure is silent (no-op), matching `event_bus.emit()` contract. Port is already resolved in the `poll()` call.
3. `event_bus.py`: Re-add `ack()` function from git history. Note: this re-adds the function that emits an `"ack"` event_type to the stream — but based on §2.4 findings, this function was never the mechanism for clearing harness-side in-flight state. If the ack POST in step 2 is added to `event_poll.py`, the stream-level `event_bus.ack()` may be redundant. **Decision point: is event_bus.ack() needed, or is the event_poll.py POST sufficient?**
4. `tests/test_harness.py`: Invert `test_does_not_dispatch` back to `test_marks_dispatched` (assert `"e3" in get_in_flight("skill")`). Replace `test_endpoint_does_not_touch_lifecycle_state` with the original or a new test that verifies `dispatch()` is called and `"e4"` is in-flight after delivery. `TestTimeoutScanner` and `TestCompleteEventEndpoint` require no changes.
5. `event-driven-workflow.md`: Add a note that `event_poll.py` posts an implicit ack after each event's cursor advance. No agent code change needed — `event_poll.py` handles it mechanically.

**Estimated diff size**: ~25-35 lines net added (5 in harness.py dispatch loop, ~10 in event_poll.py for the ack POST helper, ~8 in event_bus.py re-add, test inversion ~10, sub-skill doc ~5).

**What it delivers**: "delivered to agent transport" = ack arrives at harness. This is delivery confirmation, not processing confirmation. If the agent crashes after cursor advance but before completing the task, the ack still fires — the harness sees it as "done." This is **ack-on-delivery semantics**, not ack-on-processing.

### Path B — Explicit POST /complete from agent after processing (cleaner architecture)

Re-add `dispatch()` at `GET /events/for/{role}` + require agents to POST `/events/{id}/complete` after finishing processing each event. `event_poll.py` is unchanged. `event_bus.ack()` re-implemented to POST to `/complete`. Agent code (l1-base.md / event-driven-workflow.md) updated to call `ack(event_id)` at the end of each event's processing block.

**Concrete diff:**

1. `harness.py`: Same as Path A step 1.
2. `event_bus.py`: Re-implement `ack(event_id, role)` to POST to `http://127.0.0.1:{port}/events/{event_id}/complete` with `{"role": role, "status": "success", "summary": "agent-processed"}`. Fire-and-forget.
3. Agent contract: `event-driven-workflow.md` / `l1-base.md` updated to add explicit step: "after processing each event, call `event_bus.ack(event_id, role)` or `POST /events/{event_id}/complete`."
4. `tests/test_harness.py`: Same test inversions as Path A.
5. Compose pipeline: `l1-base.md` fragment change triggers compose regeneration for all agent roles.

**Estimated diff size**: ~40-60 lines (harness restore ~5, event_bus re-impl ~10, agent contract in l1-base ~8-12, tests ~10, compose regen impacts all composed CLAUDE.md files).

**What it delivers**: "agent finished processing" = ack arrives at harness. This is the stronger semantic — harness knows the event was actually processed, not just delivered. If the agent crashes between delivery and processing, the ack doesn't fire, and `timeout_scan()` retries. **True at-least-once processing guarantee.**

**Risk**: requires agent code to call `ack()`. Agents that forget, crash, or run in contexts where `event_bus` isn't imported will never ack. Today's agents don't have this call — adding it to the contract requires comprehension tests (per `feedback_comprehension_tests_required`). Also, `l1-base.md` change goes through compose pipeline — larger blast radius.

### Hybrid (A+B together)

Path A's implicit ack in `event_poll.py` (cursor-advance-as-ack, immediately) PLUS an optional explicit Path B agent ack at processing end for richer semantics. The harness could interpret two acks for the same event_id as idempotent (ack() already checks `if event_id in self._in_flight[role]` — second call returns False harmlessly). This gives timeout_scan visibility from delivery (so no 10-min spam) while still allowing explicit processing confirmation for observability.

**Problem with Hybrid**: if cursor-advance-ack clears in-flight immediately, the explicit post-processing ack arrives for an event no longer in-flight and returns 410. The richer observability is lost. Hybrid only works if the harness implements two-phase state (dispatched → received → processed), which is a larger state machine change not in scope.

---

## §4 Recommended Option + Reasoning

**Recommend Path A (cursor-advance-as-implicit-ack).**

Reasoning:

1. **Issue #9873 body is explicit**: "Wire cursor-advance-as-implicit-ack: event_poll.py POSTs ack to harness after writing each event line to stdout." This is Path A. The issue body already locked the implementation direction.

2. **Smaller diff, lower blast radius.** Path A does not touch `l1-base.md` or require compose pipeline regen across all roles. Path B requires compose regen and adds mandatory agent-contract steps that need CQ specs for every role.

3. **Path A gives real at-least-once delivery semantics** for the failure modes that actually matter: agent crash before any work, harness restart losing in-flight state. The window where an agent dies between cursor-advance and processing is narrow; retry-on-timeout covers it if needed.

4. **The architectural argument for Path B ("delivered vs processed")** is correct, but the original design (#7630) used cursor-advance as the de-facto ack signal — the vault decision note confirms this is the intended path. Path B is the longer-term direction, not the blocker fix.

5. **Applying `feedback_minimal_repro_over_symptom_match`**: before asserting Path B is needed, we should verify the failure mode it solves (agent processes event but crashes between delivery and done) is actually observed. Path A gives the retry mechanism; whether we need processing-complete confirmation on top is an open question for the human.

**One concern to flag**: `event_bus.ack()` from git history emits `event_type="ack"` to the stream (not a POST to `/complete`). That function is not what clears harness-side in-flight state — `/complete` does. Path A's ack mechanism should be implemented as a direct HTTP POST to `/complete` from inside `event_poll.py`, not via re-adding `event_bus.ack()`. The `event_bus.ack()` function may be re-added for API completeness but would simply call the `/complete` endpoint under the hood (the re-implemented form, not the original stream-emit form). This is a clean re-implementation, not a revert.

---

## §5 Open Questions for PM/Human

1. **Cursor-advance-as-ack timing (most important)**: The issue body says "POSTs ack to harness after writing each event line to stdout." Current `event_poll.py:264-271` writes cursor THEN emits to stdout. The ack POST should go after which step?

   - Option 1: After cursor write, before stdout emit — harness marks ack even if stdout write fails. Agent never sees the event, but harness thinks it was acked. Risk: phantom ack on a lost event.
   - Option 2: After stdout emit — harness gets ack only if both cursor write and stdout emit succeeded. This is the tightest ordering: agent has the event, cursor is advanced, then ack fires. **Recommended**: lowest phantom-ack risk.
   - Option 3: After cursor write, regardless of stdout — not recommended (same as Option 1 risk).

   Recommendation: Option 2 (after stdout emit). Failure of the ack POST itself is silent (fire-and-forget), which means there's a window where cursor is advanced + event is on stdout but harness hasn't seen the ack — but this resolves on the next poll cycle when ack retry doesn't exist. This is acceptable at-least-once delivery (harness may retry, agent processes twice) rather than exactly-once.

2. **Does "at-least-once" mean ack-on-delivery or ack-on-processing?** The issue body says cursor-advance-as-ack (Path A). But the original design intent in the vault ("agent processes the event" → ack) implies Path B. Which is the blocker fix, and which is the future enhancement?

3. **event_bus.ack() re-add: re-implement or omit?** If the ack POST lives in `event_poll.py` directly (as a local HTTP call), there's no need to re-export `event_bus.ack()`. The function could remain absent from `event_bus.py` with a note that `/complete` is the ack mechanism. Or it could be re-added as a thin wrapper around the POST (replacing the old stream-emit form). Does the agent-facing API need to expose `ack()`?

4. **Timeout default**: `EventLifecycleManager.DEFAULT_TIMEOUT_MINUTES = 10`. The issue body says "default 10min." Is 10 minutes the right default for the flip? A fast agent cycle (30-min polling) means a crashed agent would get retried at the 10-min mark — the retry arrives in the next poll window. This seems reasonable, but confirm.

5. **What happens on retry today (timeout_scan)?** When `timeout_scan()` finds an overdue event (retries < max), it increments `_retry_counts[event_id]`, resets `_dispatch_times[event_id]` to now, and logs "Event overdue." It does NOT re-deliver the event — it just extends the dispatch time (keeping it in-flight longer). Re-delivery would require the harness to re-inject the event into the stream or call the polling endpoint again with that specific event. **This is a gap**: `timeout_scan()` tracks overdue events but does not yet re-deliver them. The retry-and-redeliver mechanism is not wired. Confirm scope: is redeliver-on-timeout in or out for #9873?

6. **TestCompleteEventEndpoint vs. inverted dispatch tests**: `TestCompleteEventEndpoint` (test_harness.py:2026-2134) calls `event_lifecycle.dispatch()` directly (not via the polling endpoint) to set up in-flight state, then tests `/complete`. With Path A re-adding `dispatch()` to the polling endpoint, these tests still work (they bypass the endpoint). No changes needed. Confirm this analysis.

7. **Compose pipeline**: If `event-driven-workflow.md` is updated to document cursor-advance-as-ack, does it need a compose regen? The sub-skill is included in composed CLAUDE.md files. Changes to `event-driven-workflow.md` require `compose.py deploy-all`. Same blast radius as Path B if the sub-skill changes, but smaller because l1-base.md (the agent execution loop) is not touched.

---

## §6 Out of Scope

- **Re-deliver on timeout**: `timeout_scan()` currently extends dispatch time but does not reinject the event for re-delivery. Implementing actual re-delivery (harness re-queues event to the stream) is a larger change. If in scope, it must be explicitly added to #9873's AC or filed as a follow-on.
- **Exactly-once delivery**: out of scope by design. At-least-once is the stated goal.
- **Two-phase state machine** (dispatched → received → processed): this is the Hybrid path. Not in scope unless the human confirms they want processing-complete confirmation separately from delivery confirmation.
- **`GET /events/in-flight/{role}`** (`harness.py:1749-1753`): this endpoint works correctly with `EventLifecycleManager` and requires no changes. It becomes useful again once dispatch is restored.
- **#9845 noop stress-test event**: per the vault note, once Phase 4 lands, #9845's CLI should use the real ack path. That retrofit is separate.
- **Path B (explicit agent-side ack)**: not recommended for this task. Future enhancement once the implicit ack is in place and its adequacy is evaluated.
- **`_execute_transition` / `_execute_comment` wiring**: the side-effect handlers at `/complete` are intact. Agents can optionally include `transitions` and `comments` in their ack POST to batch mechanical operations. Not a blocker for at-least-once delivery, but the capability exists.
