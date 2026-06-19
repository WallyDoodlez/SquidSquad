# QA-RESULTS-12824

**Verdict**: ✅ **PASS — zero gaps** → pending-ship (DM)
**Verified**: 2026-06-18 20:49 by qa (verifier), on branch `squidsquad/task/12824` (PR #12836)
**Issue**: #12824 (harness assigned-to-500 / lost-traceback) — type:issue, severity:high

## AC walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 unhandled→500 + REAL traceback on disk | ✅ PASS | LIVE: real `RuntimeError` raised in routing-critical `append` → propagated to global handler → `500 {"detail":"Internal Server Error"}` AND real `.squidsquad/harness-errors.log` written with `POST` + `/events` + `RuntimeError` + `LIVE-unhandled-12824` + `Traceback`. (Worker's HTTP test mocks persist; my check uses the REAL helper via SQUIDSQUAD_DIR override.) |
| AC2 4xx not captured | ✅ PASS | LIVE: `GET /events/cursor/bogus-role-zzz` → 404, error log byte-size unchanged (real persist path, not just mock-not-called). Worker tests also cover 400 + 404. |
| AC3 1 MB rotation | ✅ PASS | Worker `test_log_rotates_past_size_cap`: oversized log → rotated to `.1`, fresh log holds only new entry. Code: `_persist_harness_error` rotates via `log_path.replace(...".1")` when `st_size > 1_000_000`. |
| AC4 fail-soft post-append→200 | ✅ PASS | LIVE: real throw in `_update_agent_from_event` → `200 {"status":"ok"}`, `append` ran exactly once (routing-critical work preserved), REAL traceback `LIVE-failsoft-12824` persisted. |
| AC5 healthy + ack-cursor regression | ✅ PASS | LIVE: healthy `assigned-to` → 200, nothing persisted. Code: fail-soft wraps ONLY `_update_agent_from_event`/`_log_event` (post-append bookkeeping); ack-cursor's `advance_cursor` is upstream and untouched → non-200 retry signal preserved (DS-review F2 honored). |
| AC6 test suite + regression | ✅ PASS | Worker suite `test_12824_harness_error_capture.py` 9/9 green. Targeted regression `pytest -k "harness or event or receive_event or cursor or dispatch"` = **888 passed, 4 skipped, 0 failed**. |

## Test runs

- `pytest tests/test_12824_harness_error_capture.py -v` → **9 passed** in 0.64s
- `python /tmp/qa_12824_live.py` (QA independent end-to-end) → **ALL PASS** (AC1/AC2/AC4/AC5), EXIT=0
- `pytest tests/ -k "harness or event or receive_event or cursor or dispatch" -q` → **888 passed, 4 skipped, 3981 deselected, 0 failed** in 37.49s

## Notes

- **No CQ gate**: change is harness.py code + tests only — no LLM-consumed instructions touched.
- **Coverage observation (not a gap)**: worker's HTTP-path tests mock `_persist_harness_error`, so they verify the handler *invokes* persist but not that a real file lands through the HTTP path. My independent live check closes that loop with the real helper writing a real file — confirmed working. Not a blocking gap because the unit `test_writes_traceback_to_log_path` exercises the real write directly; the live check is the belt-and-braces end-to-end proof.
- **Live-instance caveat**: the running :7373 harness predates the fix (unmerged; takes effect on next restart). Verification ran the branch code under TestClient — the appropriate live level for a harness-internal change. **DM/operator note**: the fix only protects the routing path *after* the next harness restart.
- **Meta**: this verification was itself triggered by the idle-driver cron safety-net forge-read after this session's event listener died (see #12837, the sibling eviction-null-anchor bug) — i.e. the missed-nudge backstop worked.
- **Merge deferred to DM**: PR body has `Closes #12824` → a QA merge would auto-close + skip DM's ship. Counter NOT bumped (DM owns).
