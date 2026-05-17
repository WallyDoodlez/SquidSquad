Now I have full context. Let me compile my findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 198-204 (TC-N2)
- **Severity**: error
- **Issue**: TC-N2's verification is internally contradictory. It asserts "phase/task fields update when the harness state updates, even though `current-state` mtime is frozen" (line 203-204). But `harness.py:710-712` reads `current_phase` directly from the `current-state` file — there is no alternative data path. If `cycle_pre`/`cycle_post` are blocked and `current-state` mtime is frozen, the harness cannot return updated `current_phase` data, so the panel cannot display updated phase fields. The verification demands behaviour the system architecture cannot produce.

- **Evidence**: `harness.py:710-712` shows `result["current_phase"] = state_file.read_text(encoding="utf-8").strip()` — the only mechanism for the harness to learn `current_phase`. TC-N2's precondition blocks the writers that update this file. The `AgentState` model (per CONTEXT.md §5.2) carries `bootup_complete` (event-driven) and `status` (process-checked), but `current_phase` is file-derived only.

- **Suggested fix**: Split the verification into two distinct assertions: (a) the panel does NOT independently check `current-state` mtime or emit a "stale" warning for events-mode roles — even when harness data is stale because the source file is frozen; (b) the panel's `bootup_complete` and `status` fields DO update via harness event-driven `AgentState` changes, since those fields don't depend on `current-state` file reads. Clarify that `current_phase` staleness in this test is expected and not a panel bug. Alternatively, update the precondition to allow harness mock injection of phase data bypassing file reads.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 157-168 (TC-I4) and Section 5 generally
- **Severity**: warning
- **Issue**: No test covers harness HTTP error responses (5xx, 4xx, malformed JSON). TC-I4 only tests "harness unreachable" (connection-refused). The panel could crash on a 500 Internal Server Error, a 404 for a specific agent endpoint, or a response body that doesn't match the expected JSON schema. These are distinct failure modes from connection-refused and are more likely in production (e.g., harness crashes mid-response, harness upgrade changes response shape).

- **Evidence**: Section 5 (Negative Tests) has TC-N1 through TC-N4, all targeting file-read/write isolation. Section 4 (Integration) has TC-I4 for "harness unreachable" only. No test injects a 500, 502, 404, or malformed JSON response from an otherwise-reachable harness. `harness.py:656` returns `{"status": "unknown", "message": "No health data yet"}` for a missing agent — this is a well-formed 200, not an error. An actual harness crash mid-request produces a different failure than connection-refused.

- **Suggested fix**: Add a negative test (TC-N5) that covers: (a) mock harness returns HTTP 500 → panel renders degraded indicator, does not crash; (b) mock harness returns HTTP 200 with unexpected JSON shape (e.g., missing `agents` key) → panel handles gracefully, does not crash; (c) mock harness returns HTTP 200 with valid shape but a per-agent record missing expected fields → panel renders available fields, does not crash.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 363-386 (Open Questions), specifically Q6, and TC-I4 line 157-168
- **Severity**: error
- **Issue**: Open Question 6 (TUI process model) is not merely an "implementation decision" — it is an architectural gap that makes TC-I4 impossible under one plausible interpretation of CONTEXT.md §5.7. CONTEXT.md §5.7 says "the same display surface (one TUI process)" and "harness-served TUI." The test plan assumes the TUI runs as a separate process from `harness.py` (line 384: "Recommend separate process for fault isolation; this plan's tests assume that model"). TC-I4 requires stopping the harness before starting the panel. If the TUI runs *inside* `harness.py`, stopping the harness kills the TUI — the test cannot execute. This is not a minor implementation detail; it determines whether an entire class of fault-isolation tests is valid.

- **Evidence**: TC-I4 line 158-159: "Stop the harness before the panel starts. Run the panel for 15s." Open Question 6 line 382-386 acknowledges the ambiguity but treats it as deferrable. CONTEXT.md §5.7 line 669 says "one TUI process" but does not state whether that process IS the harness process or a separate consumer. The glossary entry for "TUI" (CONTEXT.md line 816-819) says "single harness-served terminal UI" — still ambiguous.

- **Suggested fix**: The TUI process model must be locked before #8700 implementation begins. Add explicit language to CONTEXT.md §5.7: either "The TUI runs as a separate process consuming harness HTTP endpoints" or "The TUI runs within the harness process." If the decision is "separate process," the test plan is correct as written. If the decision is "in-process," TC-I4 must be redesigned (e.g., test harness restart rather than harness stop-before-panel-start). Flag this as a blocking open question, not a deferrable one.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 34-36 (A5) and Section 2 map, lines 60-66
- **Severity**: warning
- **Issue**: Acceptance criterion A5 requires the panel to run "its own delayed refresh loop independent of agent cycles." The test plan maps A5 to TC-U4 (refresh cadence counting) and TC-I5 (latency measurement), but neither test verifies independence from agent activity. TC-U4 proves the loop fires at the configured interval against a mock harness. TC-I5 proves a state change propagates within 2× interval. But if the panel's refresh were triggered by harness event callbacks that fire when agents cycle, both tests could still pass. The panel's loop could be agent-cycle-coupled and still appear to have correct cadence in a test where agents happen to cycle.

- **Evidence**: CONTEXT.md §5.4 deliverable 2: "Status line panel reads GET /status (or GET /agents) from the harness on a 2–5 second refresh loop." The §2 glossary: "Status line queries harness HTTP API — own delayed refresh loop, not file-tail." Neither TC-U4 nor TC-I5 explicitly tests: "run panel with zero agent activity (all agents idle, no cycles, no events); panel still refreshes at the configured cadence." TC-U4's mock harness doesn't simulate agent cycles, which indirectly tests independence — but only if the mock doesn't emit events that could trigger a coupled refresh path.

- **Suggested fix**: Add an explicit assertion to TC-U4 or create a new unit test (TC-U6): run the panel against a mock harness that emits zero events and has zero agent state changes for 15s; assert the panel makes the expected number of HTTP requests (one per refresh interval) regardless. Document that the mock harness must NOT simulate agent cycles, events, or state transitions during this test window.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 215-227 (TC-N4)
- **Severity**: warning
- **Issue**: TC-N4 verifies "Zero writes to `.squidsquad/`" but the tracer scope is under-specified. The `writable-path tracer` (line 216) should also cover `/tmp`, `~/.cache`, and the CWD outside `.squidsquad/`. A panel implementation could write temporary cache files, HTTP response caches, or debug logs outside `.squidsquad/` and still pass this test. Additionally, the note on lines 222-227 creates a test specification loophole: if the implementer decides to preserve `context-pressure` writes for back-compat, the test's pass/fail criterion changes. This makes the test non-deterministic until the implementation decision is made.

- **Evidence**: Line 219-220: "Zero writes to `.squidsquad/` (no `.tmp + mv` activity, no log file appends from the panel itself — logging is to stderr only)." Line 222-227: "Note: today's `statusline.sh` writes `.squidsquad/<role>/context-pressure` (line 72) — this side-effect should NOT be reproduced in the new panel since the harness owns context-pressure exposure via `GET /agents/{role}/health`. Confirm with implementer; if retained for back-compat, document the exception here."

- **Suggested fix**: (a) Expand the tracer scope to include common temp/cache locations (`/tmp`, `~/.cache`, the repo root outside `.squidsquad/`). (b) Lock the `context-pressure` decision before test finalization: either hard-require zero writes including context-pressure, or explicitly carve it out with a documented exception. Make the test assertion unconditional rather than subject to an implementer decision.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 98-104 (TC-U4)
- **Severity**: warning
- **Issue**: TC-U4 counts "Total request count to `/agents` (or `/status`)" but the A4 measurable criterion says "≤1 HTTP call per refresh per panel." If the implementation uses `/agents` for the list and then per-agent calls to `/agents/{role}`, TC-U4's counting middleware would need to count ALL endpoints, not just the one named. The test as written would pass even if the panel makes 1 call to `/agents` + 4 calls to `/agents/{role}` = 5 calls per refresh, because only `/agents` calls are counted. The test should count all HTTP requests made by the panel, regardless of endpoint.

- **Evidence**: Line 102-103: "Expected: Total request count to `/agents` (or `/status`) is between 9 and 11." This counts a single endpoint. If the panel is composed of `/agents` + per-agent detail calls, the per-agent calls go to a different URL path and would not be counted. A4 line 31-32: "the panel makes ≤1 HTTP call per refresh per panel" — this is a hard constraint.

- **Suggested fix**: Change the expected to count all HTTP requests to the mock harness across all endpoints, not just `/agents` or `/status`. The middleware should increment a counter for any request path. Expected count: exactly 10 (30s / 3s interval) if using a bulk endpoint; higher if using per-agent endpoints (which would violate A4 and should fail the test).

---

### Finding 7

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 293-301 (TC-T4)
- **Severity**: warning
- **Issue**: TC-T4 conflates two independent data-change propagation paths under a single consistency assertion. The status panel consumes `GET /agents` (agent state: task id, phase, bootup_complete, health). The human-queue panel consumes `GET /human/queue` (pending-human items). When an agent transitions an issue to `pending-human-*`, the agent's own status changes (it completes a task and picks up new work or goes idle), AND a new item appears in the human queue. These are two separate data sources updated by two separate mechanisms (agent state update via harness `update_health` vs. `gh issue list` shell-out). They can update at different times. The test asserts they both appear "in the same render window or adjacent windows" (line 301), but if the harness caches `/human/queue` for 5-10s (per CONTEXT.md §5.6 line 639) while agent state updates immediately, the panels WILL show the change in different windows. The test's expected result over-constrains the system.

- **Evidence**: CONTEXT.md §5.6 line 639: "cache briefly (5–10s) to avoid hammering the forge." TC-T4 line 298-301: "Both panels reflect the change within ≤ 2 × the configured refresh interval. The agent's status panel shows the new phase and the human-queue panel shows the new pending-human item in the same render window or adjacent windows." A 5-10s cache on `/human/queue` combined with a 4s refresh cadence means the human-queue panel could lag up to 2-3 refresh cycles behind the status panel for the same triggering event.

- **Suggested fix**: Decouple the propagation assertions: (a) status panel reflects agent phase change within ≤ 2 × configured interval; (b) human-queue panel reflects the new pending-human item within ≤ 2 × configured interval + the `/human/queue` cache TTL. Remove the "same render window or adjacent windows" expectation unless the `/human/queue` cache is bypassed or invalidated on state transitions.

---

### Finding 8

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 157-168 (TC-I4), verification line 167
- **Severity**: warning
- **Issue**: TC-I4 asserts "exit code 0 on SIGTERM" (line 167). This is an implicit design requirement — the panel must trap SIGTERM and call `sys.exit(0)` — that is not stated in any acceptance criterion. Default OS behaviour for SIGTERM is exit code 143 (128 + 15). If the implementer doesn't add a signal handler, the test fails for a behaviour that was never explicitly required. This design requirement should either be promoted to an acceptance criterion or removed from the test.

- **Evidence**: Line 167: "assert exit code 0 on SIGTERM." No acceptance criterion in Section 1 mentions graceful SIGTERM handling or exit code behaviour. The A4 criterion covers CPU/API load, not signal handling. The test is testing something not in the ACs.

- **Suggested fix**: Either (a) add an explicit acceptance criterion: "Panel handles SIGTERM gracefully, exiting with code 0" or (b) change the verification to "assert panel process terminates without unhandled exception (exit code 0 or 143 acceptable)" or (c) change the test to send SIGINT (Ctrl-C) which is the more typical TUI shutdown signal.

---

### Finding 9

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 84-96 (TC-U2, TC-U3)
- **Severity**: warning
- **Issue**: TC-U2 and TC-U3 test mode detection for three config states (`yes`, `no`, absent) but do not test edge cases that the `_read_config_value()` mechanism could encounter in a malformed `config.md`: whitespace padding (`event-driven:  yes` with double space), trailing whitespace (`event-driven: yes\n` vs `event-driven: yes \n`), case variations (`event-driven: Yes`), or the key appearing under the wrong role section. If `_read_config_value()` already handles these (it's shared with `compose.py`), that's fine — but the test plan should note this dependency rather than appearing to test mode detection exhaustively with only three fixtures. If `compose.py`'s `_read_config_value()` has a different tolerance than what the panel needs (e.g., `compose.py` rejects ambiguous values but the panel should be lenient), this could hide a divergence.

- **Evidence**: Lines 84-96 test exactly three config states. A6 (line 37-39) says "using the same mechanism `compose.py` uses (`_read_config_value()`)." The test plan doesn't state whether whitespace/case edge cases are tested in `compose.py`'s test suite and inherited by the panel, or need separate coverage.

- **Suggested fix**: Add a note to TC-U2/TC-U3: "Edge cases (whitespace, case, malformed sections) are covered by `compose.py`'s existing `_read_config_value()` tests. If the panel reimplements rather than reuses this function, add those edge cases here." Or, if the panel is expected to have its own implementation, add TC-U2b and TC-U3b for whitespace/case variants.

---

### Finding 10

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 376-381 (Open Question 5)
- **Severity**: warning
- **Issue**: Open Question 5 (refresh interval source — configurable vs hard-coded) affects TC-U4's validity. TC-U4 says "Status line panel configured with refresh interval = 3s" (line 99) but doesn't specify HOW it's configured. If the interval source is `config.md`, the test needs a fixture setup for the config key. If it's hard-coded, the test can't vary it. TC-U4 as written assumes configurability without stating the mechanism, making the test unimplementable until Open Question 5 is resolved.

- **Evidence**: Line 99: "Status line panel configured with refresh interval = 3s." Line 379-381: "Is the cadence configurable via `config.md` (e.g. a new key under a `## TUI` section) or hard-coded with a default? Defer to implementer; if configurable, add a unit test covering the read path analogous to TC-U4." The test plan writes TC-U4 as if the answer is already known (configurable), then defers the question to the implementer. If the answer is "hard-coded," TC-U4 can't set the interval to 3s and must use whatever the hard-coded default is.

- **Suggested fix**: Resolve Open Question 5 before test plan approval. If configurable, specify the config key path in TC-U4's precondition. If hard-coded, update TC-U4 to use the hard-coded default (e.g., 5s, yielding 6 requests in 30s). The test plan should not defer a question that determines whether a test case is implementable as written.

---

### Summary of Open Question Evaluations

| # | Question | Verdict |
|---|----------|---------|
| 1 | `/status` vs `/agents` endpoint choice | **Implementation decision.** Test plan correctly defers with a recommendation. Not a gap. |
| 2 | Aggregate endpoint (`/status/tui`) | **Implementation decision.** Test plan acknowledges impact on mock shapes. Not a gap. |
| 3 | Degraded indicator string | **Minor gap.** TC-I4 can't be fully coded until the string is chosen, but the test structure is sound. Acceptable deferral. |
| 4 | `context-pressure` writes | **Real design gap in CONTEXT.md.** Test plan handles it correctly by recommending removal and documenting the exception. The CONTEXT.md silence on this is the problem, not the test plan. |
| 5 | Refresh interval source | **Real planning gap.** See Finding 10. Must be resolved before TC-U4 is implementable. |
| 6 | TUI process model | **Real architectural gap.** See Finding 3. Must be locked before implementation; affects TC-I4 and Section 7 viability. |