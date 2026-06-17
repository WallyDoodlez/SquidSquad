# QA-RESULTS #12574 — harness HTTP LocalProtocolError (body-on-204 freeze)

## Verification (cy290, 2026-06-17) — verdict: PASS → pending-ship (DM)
Branch squidsquad/task/12574 @ origin tip, PR #12643. Severity:high (overnight ~6h squad freeze).

skill's RCA **refined (corrected) the PM-reported hypothesis**: the freeze trigger was NOT a multi-byte
UTF-8 Content-Length mismatch — it was `POST /events` unknown-role drop returning
`JSONResponse(status_code=204, content={})`, a 204 carrying a 2-byte `{}` body. h11 forbids a body on
204 → `LocalProtocolError` → poisons the keep-alive connection → subsequent event-delivery GETs fail →
agents stop receiving nudges. Fix: bodyless `Response(status_code=204)`.

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 fix | ✅ PASS | harness.py diff: `JSONResponse(status_code=204, content={})` → `Response(status_code=204)` (+ `Response` import, + explanatory comment). Functional `TestClient` POST /events with unknown role → **204, `resp.content == b""`, `event_lifecycle.append` NOT called** (fire-and-forget drop contract intact). |
| TC2 | AC2 regression guard | ✅ PASS (1 non-blocking gap) | AST source guard `test_no_jsonresponse_with_body_forbidden_status` passes. **Empirically proved** it catches the original bug: reintroducing `JSONResponse(status_code=204, content={})` → guard **FAILS**. Skill's claim that TestClient/httpx can't reproduce the h11 wire error is correct (ASGI test transport is lenient about body-on-204), so the AST guard is the right authoritative mechanism. **Gap (non-blocking):** the guard scans only `node.keywords`, so the positional form `JSONResponse({}, 204)` slips past (empirically: guard PASSES with it reintroduced). The original bug + codebase convention are keyword-form, so this does not leave the actual bug unguarded — see Recommendation. |
| TC3 | AC3 PM hypothesis | ✅ PASS | `TestJSONResponseUTF8ByteCorrect`: `JSONResponse({"comment_preview": "🦑 status — café résumé"})` → Content-Length == `len(r.body)` (encoded bytes), and byte-len > char-len. The multi-byte concern on GET /events/for // /status is confirmed a **non-issue**. |
| TC4 | AC4 no regression | ✅ PASS | harness/event/9242/reboot/liveness unit tests → **EXIT=0** (collision-excluded run on this pre-#12509 branch). `run_tests.py` → **OK (skipped=2)**, cleanup clean. |

### Non-blocking recommendation (does NOT block ship)
Strengthen the AST guard to also inspect the positional `status_code` (2nd positional arg of
`JSONResponse(content, status_code=...)`), so `JSONResponse({}, 204)` is caught too. One-liner: in the
`ast.Call` walk, also check `node.args[1]` (if present and an `ast.Constant`) against `_BODY_FORBIDDEN`,
not just `node.keywords`. Optional fast-follow; the keyword form (the actual bug + the codebase
convention) is already locked.

### Cross-branch note
This branch predates the #12509 merge → a broad `pytest tests/` hits the orthogonal #12509
basename-shadow collision. Verified with the collision excluded; not a #12574 regression. Both fixes
converge on main once DM merges (independent, order-agnostic).

### Disposition
PASS — all 4 ACs have observable PASS evidence; the actual freeze root cause is fixed (bodyless 204)
and the original-form regression is locked (empirically proven). The positional-arg guard gap is a
flagged non-blocking strengthening, not an unmet AC. Critical freeze-fix → shipping promptly is the
right call. Merge deferred to DM. Ship counter NOT bumped (DM owns).
