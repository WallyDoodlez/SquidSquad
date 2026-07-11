# TEST-PLAN-13213 — Wire UserPromptSubmit activity hook → activity_hook.py

**Source**: GitHub issue #13213 Acceptance Criteria (AC1–AC6). Doc spec: HARNESS-ARCH v29 §15.1/§15.3, AGENT-RUNTIME rev19 §8.2.
**Derived without reading the diff.**

## Test Cases

### TC-1 (AC1): compose emits the hook
- **Steps**: Invoke `compose._ensure_activity_hooks(<fresh settings.json>)` on a live system.
- **Expected**: `hooks.UserPromptSubmit` present; its hook is `type: command`, args end with `references/scripts/activity_hook.py`, `async: true`.
- **Command**: live `compose._ensure_activity_hooks` call + JSON inspect.

### TC-2 (AC2): live heartbeat end-to-end
- **Precondition**: harness running on :7373.
- **Steps**: Run the real `activity_hook.py` with stdin `{"hook_event_name":"UserPromptSubmit"}` and `SQUIDSQUAD_ROLE=qa`; read `/status` before/after.
- **Expected**: `/status` qa `last_activity.event == "UserPromptSubmit"` and `last_activity_at` advances.

### TC-3 (AC3): existing hooks unaffected
- **Steps**: After TC-1, confirm PreToolUse/PostToolUse/PostToolUseFailure still present; SessionEnd preserved; second `_ensure_activity_hooks` call is a no-op (idempotent).
- **Expected**: all 4 heartbeat hooks present; idempotent (2nd run returns False); SessionEnd coexists.

### TC-4 (AC4): fail-open / async / exit-0
- **Steps**: Confirm emitted hook `async: true`; run `activity_hook.py` and check exit code; inspect `post_activity`/`main` swallow all exceptions.
- **Expected**: `async: true`; process exits 0 even on error; never raises.

### TC-5 (AC5): tests + shadow verdict
- **Steps**: Run the new unit/integration tests; confirm a UserPromptSubmit heartbeat is a PLAIN heartbeat (no in-flight window) and that `progress_liveness` (shadow) reads `last_activity_at`.
- **Expected**: 13213 tests green; `in_flight_until` stays None on UserPromptSubmit; an open in-flight window is not disturbed.

### TC-6 (AC6): coordination documented
- **Steps**: Confirm #12271/#12492 timing + verdict-semantics are documented.
- **Expected**: a coordination note states land-before-cutover and whether a verdict-semantics change is needed.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-2
- AC3 → TC-3
- AC4 → TC-4, TC-2 (live exit-0)
- AC5 → TC-5
- AC6 → TC-6

## Comprehension Questions
N/A — change is compose-template config (`.claude/settings.json` hooks block) + Python (compose.py / activity_hook.py / harness endpoint), not LLM-consumed instruction.
