# QA-RESULTS-12747

**Issue**: #12747 — Live tests ERROR/FAIL instead of clean SKIP when claude CLI / API keys absent (test-hygiene)
**PR**: #13164 (branch squidsquad/task/12747 @ fd5df7232, base main; tests/test_model_router_live.py +27/-15)
**Verdict**: ✅ **PASS — scoped fix verified; 1 separate pre-existing finding flagged to PM (non-blocking)**
**Verified by**: verifier (qa), 2026-06-21 18:10 — verified on a clean worktree, in a no-live-model env (natural no-prereq test bed).

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 model_router_live skips clean | ✅ PASS | `pytest tests/test_model_router_live.py` in my no-prereq env → **18 skipped** (was 13+ failed pre-fix). `_run_router_or_skip()` skips on non-zero exit / empty output (402/network); key-absent already covered by autouse `_require_api_key` |
| AC2 wake_mode (4) | ✅ PASS (split) | Correctly split to #13163 (distinct root cause = stale tests, not prereq-skip) — #13163 verified PASS this session |
| AC3 comprehension scope | ✅ accepted w/ flag | PR delegates to #12748 (comprehension_helpers). In isolation, comprehension live tests SKIP cleanly (verified: test_comprehension_361 → 4 skipped). PR does NOT touch comprehension → no regression introduced |
| AC4 no regression | ✅ PASS | Change is test-only, in a live (non-static-gated) file; direct behavior verified (clean skips). Static gate unaffected (excludes live tests) |

## Findings

**Scoped fix is correct.** The PR's empirical investigation (documented in the PR body) correctly re-scoped the partly-stale issue: model_router_live present-but-degraded was the one residual prereq-skip gap, now fixed (`_run_router_or_skip`). Verified directly — 18 clean skips in a no-live-model env. wake_mode split to #13163 (verified). Comprehension delegated to #12748.

**Separate finding flagged to PM (NOT a blocker for #13164):** comprehension live tests skip cleanly *in isolation*, but `test_comprehension_361` FAILED (not skipped) when run in the same pytest session AFTER `test_comprehension_9184` (118s — it spawned). This is a cross-file state/cache leak in the comprehension test infra (#12748 domain). It is **pre-existing** — PR #13164 does not touch comprehension, so the behavior is identical on main; #13164 neither introduced nor worsened it. Recommend PM triage a follow-up against the comprehension test infrastructure (#12748), as it keeps the full live-suite signal noisy when comprehension files run together.

## Disposition

Verdict PASS → transition pending-test → pending-ship. The comprehension cross-file finding is flagged to PM in the verdict comment for separate triage (pre-existing, #12748 domain — does not block this PR's verified model_router fix). QA-RESULTS-12747 on qa planning. No comprehension spec (test-code only).
