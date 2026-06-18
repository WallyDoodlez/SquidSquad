# TEST-PLAN #12574 — harness HTTP LocalProtocolError 'Too much data for declared Content-Length'

**Derived independently from the issue's Observed/Impact + skill's refined RCA.** The PM-reported
hypothesis (multi-byte UTF-8 Content-Length mismatch on GET /events/for // /status) was a *candidate*;
skill's RCA pinned a different root cause (a 204 carrying a JSON body). My ACs cover BOTH so the
divergence itself is tested. Code bug → no comprehension gate.

## ACs
- **AC1 (fix)**: the `POST /events` unknown-role drop path no longer returns a body on a 204. It
  returns a body-less `Response(status_code=204)` (was `JSONResponse(status_code=204, content={})`),
  preserving the #9242/#11404 fire-and-forget drop contract.
- **AC2 (regression guard)**: a test locks the fix and would catch the original (keyword-form) bug —
  reintroducing `JSONResponse(status_code=204, content={})` fails the guard.
- **AC3 (PM hypothesis resolved)**: the original multi-byte-UTF-8 concern is shown to be a non-issue —
  `JSONResponse` sets Content-Length to the UTF-8 BYTE length, so emoji/non-ASCII payloads on the live
  endpoints do not mismatch.
- **AC4 (no regression)**: harness/event/reboot/liveness unit tests + `run_tests.py` stay green.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | inspect harness.py diff + functional TestClient POST /events unknown-role | returns 204, empty body, append NOT called |
| TC2 | AC2 | run AST source guard; empirically reintroduce the bug (keyword + positional) | keyword-form reintroduction FAILS the guard |
| TC3 | AC3 | run TestJSONResponseUTF8ByteCorrect | Content-Length == encoded byte length; byte-len > char-len |
| TC4 | AC4 | harness/event/9242/reboot/liveness unit tests (ignore integration dir) + run_tests.py | all green |

## Note on cross-branch collision
The #12574 branch predates the #12509 merge, so a broad `pytest tests/` on this branch hits the
orthogonal #12509 basename-shadow collision (`tests/integration/harness.py`). Verified with the
collision excluded (`--ignore=tests/integration` / file-scoped). Not a #12574 regression; both fixes
converge on main once DM merges.
