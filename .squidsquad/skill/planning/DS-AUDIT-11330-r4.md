All three R3 warnings are indeed resolved. However, I found two new regressions (one critical, one significant) plus a documentation inconsistency in the same category as R3's third warning.

---

### Finding 1

- **File**: `references/sub-skills/common-events/cursor-management.md`
- **Line**: 33–38
- **Severity**: error
- **Issue**: The ack-cursor POST example places `event_id` at the top level of the JSON body. The harness reads `event_id` from inside `payload`, not from the top level. An agent following this example literally would produce silently-failing cursor advances (the harness would accept the POST with 200 but never advance the cursor).
- **Evidence**:
  - `cursor-management.md:35-36`: `"event_id": "<the id of the event you just tended>"` — top-level key.
  - `harness.py:2023-2026`: `ack_payload = body.get("payload")` → `ack_event_id = ack_payload.get("event_id")`. The handler reads `event_id` from the `payload` sub-object, not from the top-level body.
  - `event_bus.py:186`: the canonical emit path: `emit("ack-cursor", role, payload={"event_id": event_id, "role": role})` — `event_id` is nested inside `payload`.
  - `event_bus.py:128-134`: the wire format is `{"id": ..., "event_type": ..., "role": ..., "timestamp": ..., "payload": {...}}` — `event_id` at top level would be ignored.
  - `CONTEXT-9873-A.md` D6 (line 53): locked payload schema `{event_id: str, role: str}`, and line 189 locks `event_id` as the **payload** field.
- **Suggested fix**: Rewrap the example to show `event_id` inside `payload`:
  ```
  POST /events
  {
    "event_type": "ack-cursor",
    "role": "<your alias>",
    "payload": {
      "event_id": "<the id of the event you just tended>",
      "role": "<your alias>"
    }
  }
  ```

### Finding 2

- **File**: `references/sub-skills/common-events/cursor-management.md`
- **Line**: 50
- **Severity**: warning
- **Issue**: The eviction-gap description says `GET /events/for/{role}?since=<old>` returns `HTTP 410 Gone` with body `{"cursor_evicted": true, "current_head": "<event_id>"}`. The actual harness returns `200 OK` with body fields `"evicted"`, `"oldest_id"`, and `"evicted_count_hint"`. Status code and all field names are wrong. An agent programmed to watch for 410 or read `cursor_evicted`/`current_head` would never detect an eviction condition.
- **Evidence**:
  - `cursor-management.md:50`: claims `HTTP 410 Gone`, `cursor_evicted`, `current_head`.
  - `harness.py:2203-2208` (`/events/for/{role}` endpoint): returns `200` with `response["evicted"] = True`, `response["oldest_id"] = eviction["oldest_id"]`, `response["evicted_count_hint"] = eviction["evicted_count_hint"]`.
  - `harness.py:789-801` (`get_since_with_eviction` docstring): eviction marker shape is `{"oldest_id": ..., "evicted_count_hint": ...}` — no `cursor_evicted` or `current_head`.
  - `event_poll.py:237-239`: reads `payload.get("evicted")` and `payload.get("oldest_id")` from the 200 response — confirming the actual contract.
  - The only `410` in `harness.py` is at line 2260 for the unrelated `/events/{event_id}/complete` endpoint (not-in-flight response).
- **Suggested fix**: Correct the status code and field names to match the harness:
  > `GET /events/for/{role}?since=<old>` returns `HTTP 200 OK` with `"evicted": true`, `"oldest_id": "<oldest retained event id>"`, and `"evicted_count_hint": <count>` in the response body.

---

**Note on `.event-state.json` bare references**: Both `cursor-management.md` (L41, L58) and `event-mode-contract.md` (L87, L97, L98) use bare `.event-state.json` without the `.squidsquad/` prefix, while other lines in the same files use the canonical `.squidsquad/.event-state.json` (cursor-management.md L12, event-mode-contract.md L22). This is the same class of issue that R3 flagged in `event-driven-workflow.md` L8+L13. However, since the full path is established early in each file, these are low-impact cosmetic inconsistencies — not blocking for #11330 pending-test.