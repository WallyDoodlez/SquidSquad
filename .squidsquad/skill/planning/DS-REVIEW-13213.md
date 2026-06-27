Now I have a complete understanding of the full code path. Let me compile my findings.

---

## Review Analysis

### Flow trace

1. **compose.py** `_ensure_activity_hooks()` now adds `UserPromptSubmit` alongside `PreToolUse`, `PostToolUse`, `PostToolUseFailure` — all using the same `_activity_hook_group()` template (async command hook → `activity_hook.py`).

2. **activity_hook.py** (unchanged) reads `hook_event_name` from stdin (line 97), POSTs `{"event": <name>}` to harness `/hooks/activity`. It's event-generic — works for any event name Claude Code passes.

3. **harness.py** `/hooks/activity` (line 2900) records `last_activity_at` + `last_activity` for ALL events (lines 2963-2964). The event-specific logic (lines 2974-2980) only acts on `PreToolUse` (sets `in_flight_until`, clears `waiting_since`), `PostToolUse`/`PostToolUseFailure` (clears both). `UserPromptSubmit` correctly falls through — it's a PLAIN heartbeat by design.

4. **Tests** verify: (a) compose places all 4 hooks as async command hooks, (b) harness records heartbeat without opening in-flight, (c) harness doesn't disturb an existing in-flight window.

### Issues found

```
NO_FINDINGS
```

The code change is correct and complete:

- **Correctness**: `_ensure_activity_hooks` adds `UserPromptSubmit` using the same `_activity_hook_group()` template as the other three hooks — all async command hooks, same script path, same timeout. The settings.json is valid JSON with the new entry.

- **No regressions**: The harness `/hooks/activity` handler treats `UserPromptSubmit` as a passthrough event (falls through the `if ev == "PreToolUse"` / `elif ev in ("PostToolUse", "PostToolUseFailure")` chain). It records `last_activity_at` and `last_activity` — same as any event — but touches neither `in_flight_until` nor `waiting_since`. Existing PreToolUse/PostToolUse/PostToolUseFailure/SessionEnd behavior is untouched. The `_ensure_hook_entries` idempotency check (`sort_keys=True` comparison on line 1901) works correctly regardless of whether UserPromptSubmit was already present from a prior compose.

- **Edge cases**: UserPromptSubmit arriving mid-flight (`test_userpromptsubmit_does_not_disturb_open_in_flight_13213`) correctly leaves `in_flight_until` alone. Unknown/missing role handling (lines 2930-2948) is event-agnostic. Corrupt file recovery is event-agnostic via `_ensure_hook_entries`.

- **Integration**: `activity_hook.py` reads `hook_event_name` generically (line 97) — no changes needed. The harness handler's event-dispatch pattern (lines 2974-2980) naturally accommodates new event names. The `test_all_ensures_play_together` test (renamed `test_coexists_with_activity_and_session_end`, line 669-680) verifies all 9 hooks coexist after all three `_ensure_*` calls.

- **Philosophy**: Fail-open preserved — harness always returns 200 (line 2994). Async command hook pattern preserved (not blocking http). PLAIN heartbeat design (no in-flight window) is deliberate per HARNESS-ARCH §15.1/§16.

### Non-finding notes (not actionable)

- `test_coexists_with_session_end_hook` (line 614-632) only asserts `PostToolUse`/`PostToolUseFailure` — it was already stale for `PreToolUse` (#12458) and remains so for `UserPromptSubmit`. The gap is pre-existing and covered by `test_adds_both_hooks_to_missing_file` (checks all 4) and `test_coexists_with_activity_and_session_end` (checks all 9). Not a regression from this change.

- `TestPauseHook12458` class docstring (line 4806) wasn't updated to mention #13213/UserPromptSubmit. Documentation-only, no functional impact.