# CONTEXT-9331 — Harness eviction signal + event_poll.py detection

**Issue**: #9331
**Owner**: skill
**Status**: approved (human, 2026-05-19 cycle 1501)
**Unblocks**: #8999 §4.4 IT-EvictionGap
**Planning lead**: pm-lead (cycle 1502)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9331 is the authoritative scope. This file documents locked design and grounded file references — it does not redefine the ACs.

---

## 1. Locked Design

The eviction-gap behavior is already designed and locked in three artifacts. This task **implements what those artifacts already specify** — no architectural decisions remain.

- `.squidsquad/pm/planning/CONTEXT-8694.md` §2 third bullet (Event stream gap behavior — three scenarios → Eviction gap):
  > Eviction gap (cursor predates oldest retained event in the `maxlen=1000` deque): `GET /events?since=<cursor>` returns no events at the cursor position because they've been evicted. Log eviction details (oldest available event id, count of evicted events). Advance cursor to the oldest-available event id and skim forward from there. Forge current state subsumes the lost information.
- `references/sub-skills/common-events/cursor-management.md` (per CONTEXT-8694 cross-reference) — same eviction-gap rule on the agent side.
- `.squidsquad/pm/planning/TEST-PLAN-8694.md` §4.4 IT-EvictionGap — asserts agent logs warning naming oldest available id + evicted count, advances cursor to oldest-available, does NOT crash, proceeds to forge-read.

The two locked artifacts above are the design contract. #9331 only adds the missing implementation.

## 2. Grounded File References

### Harness (response shape + counter)

- `references/scripts/harness.py:455` — `class EventStream`, bounded deque (`maxlen=1000`).
- `references/scripts/harness.py:475` — `EventStream.get_since(since_id, limit=100)`. Current behavior:
  - Line 482-485: linear scan; if `since_id` is found, returns events **after** it (`items[i+1:]`).
  - Line 487: if `since_id` is **NOT found** (evicted case), returns `items[-limit:]` with **no eviction marker**. **This is the missing-signal gap.**
- `references/scripts/harness.py:1387` — `@app.get("/events")`. Wraps `get_since` at line 1403; returns `{"events": events, "total": len(event_stream)}`. No eviction passthrough today.
- `references/scripts/harness.py:1420` — `@app.get("/events/for/{role}")`. Wraps `get_since` at line 1449; filters by `reacts-to` then returns `{"events": filtered, "total": len(filtered)}`. No eviction passthrough today.

**Note on the slicing fix on PR #9320 (skill, in-flight)**: PR1 of #9320 fixed a separate bug at line 484 where `after[-limit:]` was newest-first for the **found** case (skim-then-advance). That fix is for the long-lag scenario (§4.10), not the eviction scenario. The eviction code path at line 487 is the one #9331 changes.

### event_poll.py (detection + warning)

- `references/scripts/event_poll.py:149` — `_fetch_once(url, http_timeout)`. Returns `(events, retryable, fatal_msg)`. **The caller currently extracts only `data.get("events", [])` at line 165 — eviction fields would be discarded.** Either widen this signature to surface eviction metadata, or read it inline in `poll()`.
- `references/scripts/event_poll.py:181` — `poll(role, since=None, limit=50, ...)`. The event-processing loop is at line 198+. Eviction detection + warning belongs here, before the cursor-advance loop runs against post-eviction events.
- `references/scripts/event_poll.py:91` — `_write_cursor_atomic(role, cursor)`. Existing atomic-write helper; eviction advancement reuses this (no new write semantics needed).

### Counter location

`EventStream` currently has no lifetime counter — `len(self._events)` is bounded by `maxlen`. The counter (`total_emitted_count`) belongs on `EventStream` itself, incremented on `append` (line 462–464). Persistence across harness restarts is nice-to-have but **not required for #9331's acceptance** — the counter resets on restart, the hint becomes coarse, agents still get a useful "many events evicted" signal rather than silence.

## 3. Shape Contract

Locked from the issue body, restated here for unambiguity:

**Cursor NOT in deque (evicted)** — `get_since` and both endpoints add three fields:
```json
{
  "events": [...],
  "evicted": true,
  "oldest_id": "<hex>",
  "evicted_count_hint": <int>,
  "total": <existing field>
}
```

**Cursor IN deque (normal)** — shape unchanged. `evicted` field omitted entirely (NOT `evicted: false`). This keeps the deserialization branch on a single key-presence check.

**Empty cursor (first boot)** — shape unchanged. Eviction is not applicable when there's no cursor to be evicted from.

## 4. event_poll.py Warning Format

Locked text (so the test in #9331's unit suite can grep it):

```
[event_poll] EVICTION: cursor predates retained window — advancing to <oldest_id>, ~<evicted_count_hint> events evicted
```

- Written to stderr exactly **once per detection** (not once per event in the post-eviction batch).
- Cursor advances to `oldest_id`. Subsequent events in the same batch process normally (atomic per-event writes per the existing loop at line 198+).
- No retries, no exit. The eviction is informational; the agent continues operating.

## 5. Test Coverage Boundary

Per the new workflow (#9184 just shipped), QA writes the AC-derived test plan. For #9331:

- **Skill's unit tests** (this PR): harness `get_since` returns the new shape on eviction; both endpoints pass it through; event_poll.py detects + emits the warning; counter increments on append. Run via `python tests/run_tests.py harness` and any new event_poll unit suite.
- **QA's TEST-PLAN-9331.md** (when picking up): live verification — boot harness with `maxlen=10`, fill past cursor, observe stderr warning shape on a real agent process. CQ specs at QA's discretion (skill changes are code, not LLM-consumed instructions, so CQs likely not required).
- **#8999 §4.4 integration test** (downstream): unblocked once #9331 ships. Skill picks it up under the existing #8999 umbrella.

## 6. Out of Scope

- Counter persistence across harness restarts (would need a state file; coarse hint is acceptable per the body).
- In-stream gap handling (#9265 — separate decision pending: revise CONTEXT or monotonic ids).
- Changing CONTEXT-8694 §2 — design is correct; #9331 only lands the missing implementation.
- Changing `maxlen=1000` — out of scope; eviction signal works at any deque size.

## 7. Open Questions for Skill at Pickup

- Should the counter on `EventStream` survive harness restarts? Recommendation: **no** for #9331 (acceptance allows coarse hint); file a follow-up if persistence is wanted later.
- Should `get_since` accept a kwarg like `include_eviction=True` for callers that don't want the fields, or always include them? Recommendation: **always include** when applicable — single shape, no opt-in. Callers that don't care ignore the keys.
- The dispatch tracking at `harness.py:1466-1469` (`event_lifecycle.dispatch`) runs on the filtered batch. Does eviction need to ack/skip those events differently? Recommendation: **no** — eviction is upstream of dispatch; the events returned post-eviction are real retained events and dispatch as usual.
