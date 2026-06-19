# TEST-PLAN-12824

**Issue**: #12824 — Harness `POST /events event_type=assigned-to` returns 500 persistently (breaks PM nudge + EAD handoff routing)
**PR**: #12836 (branch `squidsquad/task/12824`) — harness.py +112/-3, tests/test_12824_harness_error_capture.py +186
**Type**: type:issue (bug — auto-approved, no PM gate). Code change only → **no comprehension/CQ gate**.
**Derived by**: qa (verifier), independent of worker's tests, from the bug's intended behavior (issue body + skill RCA comment + PR change shape). The issue carries no explicit AC list (it's a bug); ACs below are derived from the documented fix shape.

## Derived ACs

- **AC1** — An unhandled exception on any harness HTTP route returns the standard 500 (`{"detail":"Internal Server Error"}`) AND appends a traceback entry (method + path + exc type + full traceback) to `.squidsquad/harness-errors.log`. (The core deliverable: makes the next 500 diagnosable instead of lost to terminal stdout.)
- **AC2** — Intentional `HTTPException`s (4xx/503) are NOT converted to 500 and NOT persisted as unhandled errors (404 stays 404, 400 stays 400). Guards DS-review F1.
- **AC3** — `harness-errors.log` rotates to `.1` once it exceeds 1 MB (single-file rotation, bounded ≤ ~2×). Guards DS-review F3 (disk exhaustion inside the repo checkout).
- **AC4** — `receive_event` fail-soft: a throw in the non-critical post-append work (`_update_agent_from_event` / `_log_event`) does NOT 500 the emission path — response stays 200 `{"status":"ok"}`, the routing-critical `event_lifecycle.append` still ran, and the traceback is persisted. (This is the path `assigned-to` nudges + EAD handoffs ride.)
- **AC5** — Regression: healthy `assigned-to` and `ack-cursor` POSTs still return 200; ack-cursor path is NOT fail-softened (per DS-review F2 decline — a non-200 ack is the agent's retry signal). No regression across the harness/event blast radius.
- **AC6** — Worker's test suite (`tests/test_12824_harness_error_capture.py`) passes; full-suite no regressions.

## Method

Execute against a live harness instance via FastAPI `TestClient` (the harness-internal-change-appropriate live level): the **currently-running** harness on :7373 predates the fix (fix is on the unmerged branch and "takes effect on next restart"), so live verification runs the branch's `harness.py` under TestClient. Independent live checks (`/tmp/qa_12824_live.py`) exercise the **real** global handler + **real** `_persist_harness_error` writing to a **real** temp file (SQUIDSQUAD_DIR override) — closing the end-to-end loop the worker's HTTP tests leave mocked (they mock `_persist_harness_error`, proving it is *called*, not that a real file lands).
