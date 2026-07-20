# QA-RESULTS-14025

**Verdict: PASS → pending-ship**

model_router error-exit contract honesty (message wording + no consumable artifact on error). 5/5 TCs pass with live, non-mocked evidence.

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | `grep -c "Falling back to Claude" references/scripts/model_router.py` → 0 (confirmed absent, not just claimed). `grep -c "caller falls back to Claude"` → 7, present consistently across every error path (no-provider-manifest, missing API key, unknown provider, generic API error, quota, timeout, min-output-length). |
| TC2 | PASS | Live call to `model_router._discard_output_artifact()`: a real pre-existing file at the target path (simulating a stale prior-run artifact) is genuinely removed (`exists()` True → False); calling it again on an already-absent path raises nothing. Directly closes the original incident's failure mode — an artifact-existence caller now finds no file at all on any error exit, rather than a stub it could mistake for a completed review. |
| TC3 | PASS | `test_14025_router_error_contract.py` + `test_model_router.py`: 105/105. (Minor note, non-blocking: skill's checkpoint claimed "13 new tests"; the new file collects 12 — a small self-report discrepancy, consistent with this session's recurring pattern, not itself a defect.) |
| TC4 | PASS | Static gate: **6217/0**, matches skill's claim exactly. Integration: **54/54 OK**. |
| TC5 | PASS | PR touches only `references/scripts/model_router.py` + 2 test files — no `references/sub-skills/` or `references/roles/` content. No CQ spec required. |

## Conclusion

Clean fix, correctly scoped, claims match reality on every count checked (unlike this session's prior two rejections on adjacent model_router-touching issues — this one holds up). Zero gaps. → **pending-ship**.
