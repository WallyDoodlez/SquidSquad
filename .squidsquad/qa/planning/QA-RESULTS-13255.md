# QA-RESULTS-13255 — exclude self-emitted events from GET /events/for/{role}

**Verdict: PASS — zero gaps.** Verified against live harness FastAPI app (TestClient). PR #13256 merged to main (squash).

## AC walk (independent — derived from issue, not skill's PR)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | self-emitted reacts-to event (emitter==role, no target_alias) excluded | PASS |
| AC2 | cross-agent reacts-to event delivered | PASS |
| AC3 | harness-emitted reacts-to (role=harness, no target_alias) delivered | PASS |
| AC4 | self-emitted w/ explicit target_alias==role delivered | PASS |
| AC5 | missing emitter ("") delivered | PASS |

## Evidence
- Code diff (harness.py:3545-3562): `emitter = e.get("role","")`; `emitter != role` added to **reacts-to branch only**; explicit `target==role` branch unconditional and untouched. Skim-then-advance / cursor / eviction logic unchanged.
- skill regression tests (test_harness.py): `test_excludes_self_emitted_reacts_to_events_13255`, `test_self_emit_filter_includes_event_with_missing_emitter_13255` — both PASS.
- QA independent test (`tests/test_feat_13255_self_emit_filter.py`): all 5 ACs PASS, including **AC3 (harness-emitted no-target) which skill's tests do not exercise explicitly**.
- No-regression: full `tests/test_harness.py` = 294 passed; with promoted QA test = 295 passed, 0 failures.

## Notes
- Behavioral verification against the running :7373 harness is not meaningful pre-restart (it runs the old code); the TestClient against branch/merged code is the authoritative live check for harness code.
- New code has corresponding tests (skill's 2 + QA's 1). Regression test present that would catch the original self-wake bug. Zero-gap gate satisfied.

Status: pending-test → pending-ship.
