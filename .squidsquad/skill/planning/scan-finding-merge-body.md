**Observation**: The `POST /merge` handler (`merge_pr`) parses its request body with a bare `await request.json()` (no try/except) and then calls `body.get(...)` without an `isinstance(body, dict)` guard. A malformed JSON body (truncated/control-char/empty-with-wrong-content-type) raises `json.JSONDecodeError`/`ValueError`, and a valid-but-non-object body (`[1,2]`, `null`, `42`) raises `AttributeError` on `.get()`. Either propagates to the global `_capture_unhandled_exception` handler → traceback-to-disk + HTTP 500, where a clean **400** is the correct contract.

This is the same fail-open class already fixed for `POST /events` (`receive_event`, #13156) and guarded in `POST /work/assign` (#12495). `/merge` was missed by both. Low blast radius (agent-internal caller during the #12912 deploy sequence, not untrusted input), but a truncated body from a caller bug or network hiccup yields a non-retryable 500 instead of a retryable 400 — operationally worse and inconsistent with the established codebase contract.

**Location**: `references/scripts/harness.py:4132` — `merge_pr` (`@app.post("/merge")`).

**Suggested-fix**: Mirror the #13156/#12495 pattern at line 4132:

    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"malformed JSON body: {e}")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")

Add a regression test pair (malformed-body → 400; non-dict-body → 400) mirroring the `receive_event` tests added by #13156. Deterministic code → no CQ, no manifest.

_Filed via improvement-scan (skill, idle cool-down). Default low priority; not auto-fixed — human/PM triages._
