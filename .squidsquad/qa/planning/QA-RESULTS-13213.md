# QA-RESULTS-13213 — Wire UserPromptSubmit activity hook → activity_hook.py

**Verifier**: qa
**Date**: 2026-06-26 23:xx
**Verdict**: PASS (zero gaps) — Status pending-test → pending-ship.
**Change under test**: PR #13237, branch `squidsquad/task/13213`, commit `e3152028d` (+ origin/main merge `7a5bd917a`).
**Files**: `references/scripts/compose.py` (+`tests/test_compose.py`, `tests/test_harness.py`). Doc spec: HARNESS-ARCH v29 / AGENT-RUNTIME rev19.

## AC walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 compose emits UserPromptSubmit async command hook → activity_hook.py | PASS | Live `compose._ensure_activity_hooks(tmp)`: `UserPromptSubmit` emitted, `type:command`, args end `references/scripts/activity_hook.py`, `async:true` |
| AC2 harness records heartbeat; `/status` event=UserPromptSubmit, last_activity_at advances | **PASS (live E2E)** | Ran real `activity_hook.py` (stdin `{"hook_event_name":"UserPromptSubmit"}`, `SQUIDSQUAD_ROLE=qa`) against running harness :7373 → `/status` qa `last_activity_at` 1782530625.107→.299 (advanced), `event:"UserPromptSubmit"` |
| AC3 existing PreToolUse/PostToolUse/PostToolUseFailure + SessionEnd unaffected | PASS | All 4 heartbeat hooks present; 2nd `_ensure_activity_hooks` call no-op (idempotent); `test_coexists_with_session_end_hook` PASS |
| AC4 fail-open — async, exit 0 always | PASS | Emitted hook `async:true`; live `activity_hook.py` exit=0; `post_activity`/`main` swallow all exceptions (documented fail-open contract); `test_*_fail_open` PASS |
| AC5 unit/integration test of the path + progress_liveness/shadow sees it | PASS | `test_user_prompt_submit_heartbeat_13213`, `test_userpromptsubmit_records_heartbeat_no_in_flight_13213`, `test_userpromptsubmit_does_not_disturb_open_in_flight_13213` PASS; shadow `progress_liveness()` reads `last_activity_at` so it auto-includes the signal |
| AC6 coordinate w/ #12271/#12492; document timing/verdict-semantics | PASS | skill posted coordination note on #12271: lands BEFORE #12492 cutover; **no verdict-semantics change** (PLAIN heartbeat, no in-flight window; shadow auto-promotes the signal) |

## Test runs
- New 13213 tests (compose+harness, -k filter): **19 passed**.
- Full touched suites `test_compose.py` + `test_harness.py`: **377 passed** (regression clean).
- Ship gate `python tests/run_tests.py`: **53/53 OK**.
- Live E2E (AC2): real `activity_hook.py` → running harness → `/status` advance confirmed.

## Design soundness
UserPromptSubmit is wired as a **plain heartbeat** — it advances `last_activity_at` but deliberately does NOT open an in-flight window (only PreToolUse sets `in_flight_until`, harness.py). This is correct: an in-flight window on prompt-receipt would MASK the freeze-after-prompt-before-first-tool-call gap this signal exists to expose. Verified live (in_flight not disturbed) + by the no-in-flight tests.

## Verdict
**PASS — zero gaps.** All 6 ACs observably satisfied (AC2 confirmed live end-to-end on the running harness). Regression clean; ship gate green. Status pending-test → pending-ship; PR #13237 to merge.
