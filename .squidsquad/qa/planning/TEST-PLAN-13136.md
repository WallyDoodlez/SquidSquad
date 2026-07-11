# TEST-PLAN-13136

**Issue**: #13136 — stop-requested handler lacks explicit ack-stop emission + ack-cursor guidance (vs deploy-signal)
**Type**: type:issue (auto-approved), severity:low, role:skill
**PR**: #13149 (branch squidsquad/task/13136, base main, +5/-3, 2 files)
**Authored by**: verifier (qa), derived independently from issue body's two gaps + the explicit "verify against harness.py + AGENT-RUNTIME §5.2 before editing" requirement. NOT from the PR diff.

## Derived Acceptance Criteria

The issue describes two completeness gaps in the `stop-requested` handler (Case E of `event-mode-contract.md`) and poses an open question to resolve before any edit. Independent ACs:

- **AC1 (gap 1 — ack-stop emission)**: The stop-requested handler must explicitly state whether the agent emits `ack-stop` on the stopping path, AND resolve the open question (does any agent-side code emit a stop ack-stop, or is the 60s force-kill the sole mechanism?) against ground truth.
- **AC2 (gap 2 — ack-cursor guidance)**: The handler must explicitly state whether the stop trigger should be `ack-cursor`'d (clarify the narrow race the issue raises).
- **AC3 (factual accuracy)**: Every claim the fix makes must be true against harness.py + AGENT-RUNTIME §5.2 / §10 Q11 (ground-truth verification — the issue mandates this).
- **AC4 (comprehension — hard gate)**: A fresh agent given ONLY the modified passages must derive the correct mental model: emit NO ack-stop on a stop, NOTHING to ack-cursor, and must NOT confuse the stopping path with the deploy-halt path (which DOES emit ack-stop). Spec: tests/comprehension/13136_spec.json.
- **AC5 (internal consistency + no regression)**: New text must not contradict the deploy-signal path or the Soul stop-rules; the static/test gate (run_tests.py) must stay green.

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | Read final Case E stop-requested bullet | Contains explicit "Do NOT emit `ack-stop` on this path" + rationale (no agent-side stop ack-stop; 60s force-kill is the mechanism) |
| TC2 | AC2 | Read final Case E stop-requested bullet | Contains explicit "Nothing to `ack-cursor`" + rationale (intent flip, not a deque event → no event id) |
| TC3 | AC3.1 | `git show origin/main:docs/AGENT-RUNTIME.md` §5.2 | stop-requested listed as reserved/never-emitted (speculative entry) |
| TC4 | AC3.2 | grep harness.py for stop-requested emission | No emission; only a defensive ack handler (L3194) |
| TC5 | AC3.3 | AGENT-RUNTIME §10 Q11 | ack-stop.result enum = checkpointed/aborted/drained, Closed 2026-05-30 |
| TC6 | AC3.4 | grep call sites of `ack_stop(` across agent scripts | Zero call sites (only a doc-string ref in event_catalog.py) → "no agent-side code emits a stop ack-stop" holds |
| TC7 | AC3.5 | harness.py force-kill | FORCE_KILL_TIMEOUT_SECONDS=60, armed on stopping/restarting intent |
| TC8 | AC4 | Fresh sonnet agent, ONLY modified passages | 3/3 CQs correct, zero must_not violations |
| TC9 | AC5.1 | Read full Case E (both bullets) + event-driven-workflow Context pressure | Stopping path (no ack-stop) vs deploy path (ack-stop=deploy-halted) clearly distinct; two files consistent |
| TC10 | AC5.2 | `python tests/run_tests.py` | Green (no regression) |
