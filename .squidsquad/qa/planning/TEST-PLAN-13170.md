# TEST-PLAN-13170 — fail-closed JSON-body guard on POST /merge

**Derived independently** from the issue body (skill-filed improvement-scan).

## Expected behavior
`POST /merge` (`merge_pr`) must fail closed (HTTP 400) on a malformed JSON body or a valid-but-non-object body, instead of fail-open (500 traceback-to-disk via the global handler). Mirrors the established #13156 (POST /events) / #12495 (POST /work/assign) contract.

## ACs (independent)
- AC1 malformed body (truncated / empty / whitespace) → 400 "malformed JSON body"
- AC2 non-object body ([1,2] / null / 42 / JSON string) → 400 "body must be a JSON object"
- AC3 valid dict with pr_number → passes both guards, reaches merge path (202 + thread spawn)
- AC4 guard does not shadow the pre-existing `pr_number is required` 400

## Method
Live harness FastAPI app via TestClient. QA test (`tests/test_feat_13170_merge_body_guard.py`) adds valid-dict-reaches-merge-path + empty/whitespace-body coverage beyond skill's tests. No-regression: full `tests/test_harness.py`.
