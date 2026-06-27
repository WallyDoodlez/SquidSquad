## #13170 — fail-closed JSON-body guard on `POST /merge`

(skill-filed improvement-scan; the last unguarded JSON-body POST handler.)

### Root cause
`merge_pr` parsed its body with a bare `await request.json()` and then called `body.get(...)` without an `isinstance(body, dict)` guard:
- a truncated / control-char / empty body → `json.JSONDecodeError` / `ValueError`
- a valid-but-non-object body (`[1,2]`, `null`, `42`) → `AttributeError` on `.get()`

Either propagated to the global `_capture_unhandled_exception` handler → traceback-to-disk + HTTP **500**, where a clean **400** is the contract. Same fail-open class already fixed for `POST /events` (#13156) and `POST /work/assign` (#12495); `/merge` was missed by both.

### Fix
Mirror the established pattern — `try/except (JSONDecodeError, ValueError) → 400` and `if not isinstance(body, dict) → 400` — before the first `.get()`.

### Verification
- +3 tests: malformed JSON → 400; non-dict body (raw `[1,2]` / `null` / `42`) → 400; a well-formed object missing `pr_number` keeps its **own** 400 (the new guard doesn't shadow the pre-existing required-field check). Both new rejections fire **before** any merge thread spawns, so no `git_ops` mocking is needed.
- Full static gate: **4970 passed, 0 failures, 0 errors**.
- No DS-review: deterministic fail-open guard, same class as #13156/#12495 where DS-review was skipped, comprehensive tests. No CQ (deterministic). No manifest (no new files).
