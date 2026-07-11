# QA-RESULTS-13170 — fail-closed JSON-body guard on POST /merge

**Verdict: PASS — zero gaps.** PR #13258 merged (squash). Verified against live harness FastAPI app (TestClient).

## AC walk (independent — derived from issue body)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | malformed JSON body (truncated/empty/whitespace) → 400 "malformed JSON body" (not 500) | PASS |
| AC2 | non-object body (`[1,2]`, `null`, `42`, JSON string) → 400 "body must be a JSON object" | PASS |
| AC3 | valid dict (with pr_number) passes both guards → reaches merge path (202 + thread spawn) | PASS |
| AC4 | guard does NOT shadow the pre-existing `pr_number is required` 400 | PASS |

## Evidence
- Code (harness.py:4160-4166): `try: body = await request.json() except (JSONDecodeError, ValueError) → 400`; `if not isinstance(body, dict) → 400` — both before the first `.get()`. Mirrors #13156 (POST /events) and #12495 (POST /work/assign). `/merge` was the last unguarded JSON-body POST handler.
- skill unit tests (test_harness.py `TestMergeBodyGuard13170`): 3 tests PASS (malformed→400, non-dict [1,2]/null/42→400, missing-pr_number keeps own 400).
- **QA independent test** (`tests/test_feat_13170_merge_body_guard.py`): confirms a **fully-valid dict reaches the merge path** (status 202, thread spawned — skill only tested missing-pr_number) and adds **empty-body + whitespace-body** malformed cases + JSON-string non-object case skill did not cover. ALL PASS.
- No-regression: full `tests/test_harness.py` (post-merge, all 4 fixes integrated) green.

## Notes
- Behavior is now consistent with the established #13156/#12495 fail-closed contract: a truncated/non-object body yields a retryable 400 instead of a non-retryable 500 traceback-to-disk.
- Deterministic code → no CQ. No new manifest files.

Status: pending-test → pending-ship.
