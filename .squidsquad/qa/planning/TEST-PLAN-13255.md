# TEST-PLAN-13255 — exclude self-emitted events from GET /events/for/{role}

**Derived independently from the issue body** (#13255 is a qa-filed bug; no formal AC list — ACs below are derived from the Observation + Suggested-direction sections, not from skill's PR diff).

## Expected behavior
`GET /events/for/{role}` must not return events the requesting role emitted itself when the match is via the reacts-to list (broadcast). Explicit `target_alias` targeting must still win. Cross-agent and harness-emitted events must be unaffected.

## Acceptance criteria (independent)
- **AC1** — A self-emitted reacts-to event (emitter `role` == requesting role, no `target_alias`) is NOT returned.
- **AC2** (no-regression) — A cross-agent reacts-to event (different emitter) IS returned.
- **AC3** (no-regression) — A harness-emitted reacts-to event (`role=harness`, no `target_alias`) IS returned (harness ≠ requester). Covers the case skill's unit tests do not exercise explicitly.
- **AC4** — A self-emitted event with explicit `target_alias==role` IS returned (explicit-target branch unconditional).
- **AC5** — An event with missing emitter (`""`) IS returned (unattributable → conservative include).

## Method
Live-instance: harness FastAPI app via `TestClient` (the authoritative live behavior for harness code; the running :7373 harness still runs pre-fix code until restart, so the TestClient against branch code is the correct live check). Independent test: `tests/test_feat_13255_self_emit_filter.py`.

## No-regression
Full `tests/test_harness.py` (294 tests).
