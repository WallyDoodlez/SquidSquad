## #13213 — Wire UserPromptSubmit activity hook → activity_hook.py

Closes the **freeze-after-prompt-before-first-tool-call** liveness gap (sibling of the #12271 wedge class). Today the activity heartbeat fires only on tool-call boundaries (PreToolUse opens an in-flight window; Post* closes it). An agent that receives a prompt and then freezes *before* its first tool call emits no new heartbeat — `last_activity_at` stays frozen and the harness can't distinguish "received input, now wedged at prompt-processing" from "legitimately idle". `UserPromptSubmit` stamps activity at prompt-receipt (nudge tick, idle-driver tick, or inline operator turn).

### Design decision (the "skill's call" in the issue scope)
`UserPromptSubmit` is wired as a **PLAIN heartbeat** — it advances `last_activity_at` but does **NOT** open an in-flight window. The harness `/hooks/activity` handler already sets `in_flight_until` only on `PreToolUse` (harness.py:2975), so the new event falls through as a passthrough heartbeat with **no harness change required**. This is deliberate: arming an in-flight "work-should-follow" window on UserPromptSubmit would *mask* the very freeze-after-prompt window this signal exists to expose. Documented in the `_ensure_activity_hooks` docstring (HARNESS-ARCH §15.1/§16).

### Wiring-only (no rewrite)
`activity_hook.py` is already event-generic (reads `hook_event_name` from stdin) and `/hooks/activity` already ingests any event → the change is a compose-template addition plus tests, exactly as the issue predicted.

### Acceptance criteria
- **AC1** — `compose._ensure_activity_hooks` emits `UserPromptSubmit` as an async command hook → `activity_hook.py` (same group as the other three). Tests: `test_user_prompt_submit_heartbeat_13213`, updated `test_adds_both_hooks_to_missing_file`. ✅
- **AC2** — On a prompt submission the harness records a heartbeat: `last_activity` shows `event: "UserPromptSubmit"` and `last_activity_at` advances. Test: `test_userpromptsubmit_records_heartbeat_no_in_flight_13213`. ✅
- **AC3** — Existing PreToolUse/PostToolUse/PostToolUseFailure + SessionEnd hooks unaffected. Test: updated `test_coexists_with_activity_and_session_end` (all 9 hooks coexist). ✅
- **AC4** — Fail-open preserved (async command hook, never blocks/delays the turn; harness always 200). Verified in compose group assertions + harness handler. ✅
- **AC5** — Integration test covering UserPromptSubmit → heartbeat, incl. that it does not disturb an open in-flight window (`test_userpromptsubmit_does_not_disturb_open_in_flight_13213`) so progress_liveness/shadow verdict sees the signal. ✅
- **AC6** — Coordination with #12271/#12492: lands **before** the cutover; the shadow `progress_liveness()` verdict (harness.py:731, reads `last_activity_at`) automatically includes the new signal with **no verdict-semantics change**. Noted on #12271. ✅

### Verification
- Full static gate (post merge of origin/main): **4963 passed, 0 failures, 0 errors**.
- DS code-review: **NO_FINDINGS** (DS-REVIEW-13213.md on main).
- No CQ spec: change is deterministic config/code (compose template + harness passthrough), not LLM-consumed agent instructions ([[feedback_cq_applies_to_llm_consumed_not_composed_files]]).
- No manifest update: no new tracked files (activity_hook.py already tracked).
- `.claude/settings.json` is per-clone state (stripped from the PR by the #11511 guard); the compose source in this PR regenerates it on every clone.
