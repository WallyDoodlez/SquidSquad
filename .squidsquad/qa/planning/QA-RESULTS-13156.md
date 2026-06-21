# QA-RESULTS-13156

**Issue**: #13156 — harness POST /events crashes (500) on unescaped control char; should fail closed (400)
**PR**: #13157 (branch squidsquad/task/13156 @ c742bddcf, base main, harness.py +14/-1 + tests/test_13156_malformed_event_body.py +78)
**Verdict**: ✅ **PASS — zero gaps (within scope)**
**Verified by**: verifier (qa), 2026-06-21 15:12
**Method**: Independent TEST-PLAN from issue; verified on a clean worktree of the PR branch, including a revert-the-fix proof that the regression test catches the original bug.

## AC Walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 fail closed | ✅ PASS | test_raw_control_char_body_returns_400_not_500 → 400; _persist_harness_error NOT called (not recaptured as 500) |
| TC2 | AC2 regression catches original | ✅ PASS | Reverted ONLY harness.py to origin/main → test FAILED `500 != 400`; captured stdout reproduced the exact bug ("500 on POST /events: JSONDecodeError: Invalid control character ... (char 64)"). Restored fix → passes. Proves the test would have caught the original. |
| TC3 | AC3 no over-rejection | ✅ PASS | test_well_formed_body_still_accepted (escaped multi-line) → 200 |
| TC4 | AC1 fix shape | ✅ PASS | harness.py receive_event: `try: body = await request.json() except (json.JSONDecodeError, ValueError) as e: _log(...); raise HTTPException(400, ...)`. Correct: JSONDecodeError/UnicodeDecodeError are ValueError subclasses |
| TC5 | AC4 no regression | ✅ PASS | `python tests/run_tests.py static` on fixed branch: 4886 gated PASS (0 fail, 0 error) — +3 vs prior 4883 are the new tests; known-failures pre-existing (#10360) |

## Findings

Fix is correct, complete, and well-tested within the issue's scope. The fail-closed guard converts the 500 crash to a clean 400 + log + drop, exactly as the issue's headline requirement specifies. The regression test is genuine (proven to fail pre-fix). Control test confirms no over-rejection of valid multi-line payloads.

**Non-blocking observation (flagged to PM, not a gap):** the fix is defensive hardening at the receiver; it does NOT address the *source* emit-path that posts the unescaped control-char body in a retry loop (the issue names the deploy-error multi-line `detail` field as the plausible trigger). The issue made the emit-path fix explicitly "and/or"/"suggested direction," so fail-closed alone satisfies scope. Post-fix, the retry loop degrades from 500 crashes to clean 400s (the intended behavior). If the 400 recurrence persists in harness-errors.log, a follow-up to JSON-escape the emit-path serialization may be warranted — PM's call (already named in the issue body).

## Disposition

Verdict PASS → transition pending-test → pending-ship. Regression test tests/test_13156_malformed_event_body.py committed in PR (tests/, preserved permanently). Merge + ship deferred to DM (verifier owns no release state). TEST-PLAN-13156 + QA-RESULTS-13156 on qa planning.
