# Code review — #13148 (harness ack-stop settled-enum alignment)

**DeepSeek (model_router) was unavailable** — returned HTTP 402 "Insufficient Balance". Per the model-router auto-fallback rule ([[feedback_model_router_auto_fallback]]), the review was performed by a Claude (Sonnet) subagent instead. Findings below.

## Verdict: no functional regressions. 1 warning (incorporated), 1 note.

**(b) dropping `"stop-confirmed"` recognition** — SAFE. `event_bus.ack_stop()` has ZERO production callers (only its def, the catalog comment, and `test_event_bus.py`). The obsolete string was never reachable from a live emit path; dropping it removes a dead check.

**(c) no-clock-reset invariant** — PRESERVED. Under the new `if _stop_result in (...)` branch the body is `pass` inside the `INTENT_STOPPING` guard, identical to before; `intent_set_at` is never written.

**(d) `elif "deploy-halted"` still reachable** — YES. `"deploy-halted"` is not in `("checkpointed","aborted","drained")`, so the `if` is false and the `elif` evaluates. No swallowing.

**(e) other regressions** — none.

### Finding 1 (warning) — INCORPORATED
`event_bus.py` `ack_stop` docstring still advertised `"stop-confirmed"` as the canonical result (the contract a future wiring author reads), and `test_event_bus.py` used it in 6 examples. Both updated to the settled enum (`checkpointed`/`aborted`/`drained`) this change.

### Finding 2 (note)
Confirmed the dead-path-hygiene claim (zero emitters). The fix aligns the handler so it works correctly when an agent-side emitter is wired (the follow-on).

### Reviewer style note (not actioned)
The `elif` re-reads `ack_payload.get("result")` rather than reusing `_stop_result` — functionally equivalent (ack_payload not mutated between), left as-is to keep the deploy branch diff-free.
