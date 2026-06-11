# #11329 AC3 — Harness ack-cursor consumer verification

**Date**: 2026-06-11
**Verdict**: PASS — the harness ack-cursor consumer is per-event (not batched), and the boot-time cursor read is accurate. No separate issue needed.

## AC3 requirements

- Verify per-event `ack-cursor` handling on the harness side is correct (not assuming batched semantics).
- If the consumer assumes batched, file a separate issue (do not silently fix here).
- Boot-time `GET /events/cursor` is still accurate per AGENT-RUNTIME §7.2.

## Findings (evidence)

### Per-event, not batched ✓

`harness.py:2018-2047` — the `POST /events` handler's `ack-cursor` branch:

- Reads a **single** `event_id` from `body.payload.event_id` (`harness.py:2026`) — no list, no batch field. One `event_id` per POST.
- Calls `event_lifecycle.advance_cursor(role, ack_event_id)` (`harness.py:2032`) off the asyncio loop via `asyncio.to_thread` (D4/AC-9).
- `advance_cursor(role, event_id)` (`harness.py:973`) advances the **per-role** cursor (`self._cursors`, line 909) to that single id, with two rejections:
  - **evicted** (D8/AC-8/AC-16): event_id no longer in the retained deque → no-op + debug log.
  - **regression** (D15/AC-17): event_id appears earlier in the deque than the current cursor → no-op (out-of-order ack delivery cannot silently regress the cursor; insertion order is the monotonic signal since ids are random 16-hex).

This is exactly the D2 per-event model: each agent `ack-cursor` POST advances the cursor by one tended event. The consumer does **not** assume or require batched (end-of-walk) semantics. The model-B `event_poll.py` rewrite (AC1) and the agent's §8.1 eager loop both POST one `ack-cursor` per event, which the consumer handles natively.

### Boot-time cursor read accurate (§7.2) ✓

`GET /events/cursor/{role}` (`harness.py:2217`) → `{cursor, role}`, backed by `get_cursor(role)` (`harness.py:960`):

- Returns the current per-role cursor, or `None` when no cursor exists (first boot, or role has never acked) — D7 locks `null` as the absent value.
- Lock-free atomic dict read (R2 D5/AC-3) — does not block the asyncio loop (H6 mitigation).

The agent boot sequence (`event-mode-contract.md` Case A step 1) reads this endpoint to resume; the model-B migration introduces no change to the consumer or the read endpoint — both pre-date #11329 and are audit-verified.

## Conclusion

The harness side already implements the canonical per-event consumer #11329's producer side (event_poll → agent ack) migrates toward. AC3 is satisfied with no code change and no separate issue.
