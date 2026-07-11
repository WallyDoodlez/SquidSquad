# TEST-PLAN-13148

**Issue**: #13148 — harness ack-stop handler keys on obsolete 'stop-confirmed'; settled enum (§10 Q11) is checkpointed/aborted/drained
**Type**: type:issue (auto-approved), severity:low, role:skill
**PR**: #13159 (branch squidsquad/task/13148 @ 099256b8e, base main; harness.py + event_bus.py + event_catalog.py + 3 test files)
**Authored by**: verifier (qa), derived from issue's observed drift. Independent of PR.

## Derived Acceptance Criteria

- **AC1**: harness.py ack-stop branch keys on the settled enum (checkpointed/aborted/drained per AGENT-RUNTIME §10 Q11) instead of obsolete 'stop-confirmed'; aborted gets the "graceful stop failed → escalate" disposition; intent_set_at not reset (preserves 60s window).
- **AC2**: regression test that would have caught the obsolete-key drift (fails pre-fix).
- **AC3**: no regression (static gate); event_bus docstring + catalog updated for accuracy + consistency.
- **AC4 (consistency)**: no agent-side emitter wired (consistent with #13136 "emit nothing on stop path"); fix is latent-correct.

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | Inspect harness.py diff | `_stop_result in ("checkpointed","aborted","drained")`; aborted logged; no intent_set_at reset |
| TC2 | AC2 | Run test_13148 + test_event_bus + test_harness on fixed branch | All pass (320) |
| TC3 | AC2 | Revert ONLY harness.py to origin/main, re-run test_13148 | FAILS (aborted not logged) — proves it catches the drift |
| TC4 | AC3 | event_bus.py docstring + event_catalog.py reflect settled enum | obsolete 'stop-confirmed' removed; checkpointed/aborted/drained documented |
| TC5 | AC3 | `python tests/run_tests.py static` | PASS, no regression |
| TC6 | AC4 | Confirm event_bus.ack_stop has no callers (no emitter) | consistent with #13136; latent-correct |
