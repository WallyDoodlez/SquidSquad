# QA-RESULTS-13163

**Issue**: #13163 — Stale test: test_feat_9745_wake_mode_qa_live asserts retired config-driven wake-mode (+ deleted boot-bootstrap.md)
**PR**: #13166 (branch squidsquad/task/13163 @ 1c755a7b6, base main; tests/test_feat_9745_wake_mode_qa_live.py +26/-65)
**Verdict**: ✅ **PASS — zero gaps**
**Verified by**: verifier (qa), 2026-06-21 17:55 — derived TEST-PLAN from issue (retire/rewrite 4 stale TCs; no lost coverage; no regression).

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 retire stale TCs | ✅ PASS | test_tc_04 / test_tc_05 / test_tc_05b REMOVED (grep empty, not skipped); TC-2/TC-3 parametrize narrowed from [compose.py, cycle_post.py, statusline_data.py] → [statusline_data.py] |
| AC2 file passes | ✅ PASS | test_feat_9745_wake_mode_qa_live.py on PR branch: 4 passed (was 4 failed/8 passed on main pre-fix) |
| AC3 narrowing accurate | ✅ PASS | compose._get_wake_mode retired E6/#10685 (only comments at compose.py:56-58); cycle_post.py has no wake-mode delegation → statusline_data.py IS the sole live delegator; narrowing does not hide a real requirement |
| AC4 coverage preserved | ✅ PASS | current harness-probe wake-mode model covered by test_feat_9745_wake_mode_canonical.py (15 passed), re-run by TC-6 — retired TCs' intent relocated, not lost |
| AC5 no regression | ✅ PASS | `python tests/run_tests.py static`: 4891 gated PASS, 0 fail, 0 error |

## Findings

Correct test-hygiene fix. The 4 TCs asserting the retired config-field-driven wake-mode model (and the deleted boot-bootstrap.md) are removed; TC-2/TC-3 are accurately narrowed to the sole remaining live delegator (statusline_data.py). The module docstring clearly documents the #9745 → #11401 reconciliation (config-field model → harness-probe model, AGENT-RUNTIME §9.3). No coverage lost — the current probe behavior is covered by the canonical test (re-run by TC-6). Static gate green.

## Disposition

Verdict PASS → transition pending-test → pending-ship. TEST-PLAN/this on qa planning. No comprehension spec (test-code only, no LLM-consumed instruction changed).
