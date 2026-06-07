All referenced files exist and all line references in the docs have been verified against the actual source code:

- **`harness.py:2023-2026`** → Lines 2023–2026 contain `ack_payload = body.get("payload")`, the `isinstance` guard, and `ack_event_id = ack_payload.get("event_id")`. ✅
- **`harness.py:2203-2208`** → Lines 2203–2208 construct the response with `"evicted": True`, `"oldest_id"`, and `"evicted_count_hint"`. ✅
- **`event_bus.py:186`** → Line 186 is `emit("ack-cursor", role, payload={"event_id": event_id, "role": role})`, confirming `role` in payload. ✅
- **`event_poll.py:6`** → Line 6 references advancing cursor in `working-state.md`, matching the transitional note. ✅
- **`event_poll.py:_write_cursor_atomic`** → Function at line 113 performs `.tmp` + `mv` atomic write of `Last Processed Event ID` to `working-state.md`. ✅

Cross-file consistency verified:

| Topic | cursor-management.md | event-mode-contract.md |
|---|---|---|
| Eviction gap recovery | forge-read + `ack-cursor` with `event_id = oldest_id` (L55) | forge-read + `ack-cursor(oldest_id)` POST (L31) |
| Cursor home | `.squidsquad/.event-state.json`, harness-owned (L12) | `.squidsquad/.event-state.json`, harness-owned (L22, L98) |
| Per-event ack | one ack per tended event, no batching (L46) | per-event ack-cursor in §7.1 loop (L56, L97) |
| Transitional note | Pre-#11329: legacy `Last Processed Event ID` line may exist (L14) | Pre-#11329: `event_poll.py` still writes legacy line (L98) |

The R5 fix is confirmed: `ack-cursor(current_head)` → `ack-cursor(oldest_id)` at event-mode-contract.md L31, now matching both cursor-management.md L55 and the harness response field `oldest_id` (harness.py L2206).

NO_FINDINGS