# Iteration 290 — 2026-06-17 (extended session, post-#12509)

**Mode**: POLLING. PT queue surfaced 2 high-pri items (skill submitted during #12509 verification).

**Outcome**: **2 VERIFIED → PASS → pending-ship** (#12574, #12525). #12509 also DM-merged to main this session.

## #12574 — harness HTTP LocalProtocolError (body-on-204 freeze) — PASS
Severity:high (overnight ~6h squad freeze). Branch squidsquad/task/12574, PR #12643.
- skill's RCA **corrected the PM hypothesis**: not multi-byte UTF-8 — the fault was `POST /events` unknown-role drop returning `JSONResponse(204, content={})` (a 204 with a 2-byte body) → h11 `LocalProtocolError` → poisons keep-alive → event delivery stalls. Fix: bodyless `Response(204)`.
- AC1 fix (functional TestClient: 204 + empty body + append not called); AC3 PM hypothesis confirmed non-issue (JSONResponse byte-correct Content-Length, emoji payload); AC4 no regression (harness/event/reboot unit EXIT=0 + run_tests.py OK).
- **AC2 regression guard — PASS + non-blocking flag**: AST source guard catches the actual keyword-form bug (empirically proved: reintroduce → guard FAILS). Skill's "TestClient can't reproduce h11 wire error" is correct (ASGI transport lenient). **Gap flagged**: guard scans only `node.keywords`, misses positional `JSONResponse({}, 204)` — non-blocking (actual bug + codebase convention are keyword-form), recommended fast-follow (also check `node.args[1]`).
- Cross-branch: this branch predates #12509 merge → broad `pytest tests/` hits the orthogonal #12509 collision; verified collision-excluded.
- Merge deferred to DM (PR `Resolves #12574`). Counter NOT bumped.

## #12525 — bare-harness launchers (start-harness.bat/.sh) — PASS
Priority:high (operator request). Branch squidsquad/task/12525, PR #12617.
- AC1 bat (cd + `python harness.py %*` + pause; /status→200 via TestClient on real app); AC2 sh (`exec python3 ... "$@"` foreground); AC3 no git/pip (both); AC4 manifest both-listed + **count claim independently verified (202==202**, stale 197→200 corrected) + bare-vs-full headers; AC5 start.* untouched.
- 16 unit tests green.
- **Non-blocking**: AC1/AC2 OS-GUI (double-click visible window / real-shell foreground) deterministic from tested script content → operator-confirmable, NOT blocked:human-action (no env setup). **@pm flagged**: Scope's INSTALLER-ARCH/README one-liner is PM doc-lane; AC4 satisfied by file headers.
- Merge deferred to DM (PR `Resolves #12525`). Counter NOT bumped.

## Session notes
- Detected + flagged a pre-existing L4 test cwd/stdout-clobber quirk (swallows full-suite pytest summary + junitxml at ~57%) during #12509 — candidate improvement issue (orthogonal, not a #12509 gap).
- Vault: dedup — skill already authored `learning-in-process-import-resolution-test-contaminates-suite` (covers my verifier-lane insight); no duplicate written.

**Quiet Cycle Counter**: 0 (productive).
