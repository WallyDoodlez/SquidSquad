### Finding 1

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: 31
- **Severity**: error
- **Issue**: Eviction-gap recovery references `ack-cursor(current_head)` — the term `current_head` is a leftover from the pre-R4 incorrect contract. The harness's eviction-gap GET response returns the field `oldest_id` (not `current_head`), and the companion fragment `cursor-management.md` line 55 correctly instructs the agent to POST `event_id = oldest_id`. Using `current_head` here creates a mismatch: the agent would look for a field that does not exist in the harness response.
- **Evidence**: 
  - `cursor-management.md:55` defines the harness response as `"oldest_id": "<oldest retained event id>"` and the recovery as `ack-cursor` POST with `event_id = oldest_id`.
  - `event-mode-contract.md:31` says `ack-cursor(current_head)`. `current_head` was the field name in the old (pre-R4, incorrect) eviction-gap response shape (`cursor_evicted`/`current_head`, HTTP 410). The R4-corrected contract uses `oldest_id` — `current_head` no longer appears anywhere in the harness response.
  - An agent reading only `event-mode-contract.md` would not find `current_head` in the actual JSON response and could either crash or use a wrong/null `event_id` in the ack-cursor POST — which the harness silently ignores (returns 200, no cursor advance per `cursor-management.md:47-49`).
- **Suggested fix**: Replace `ack-cursor(current_head)` with `ack-cursor(oldest_id)` on line 31 of `event-mode-contract.md`, matching the harness response field and the recovery prescription in `cursor-management.md:55`.

```diff
- single `ack-cursor(current_head)` POST to fast-forward
+ single `ack-cursor(oldest_id)` POST to fast-forward
```