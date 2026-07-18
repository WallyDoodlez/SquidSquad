# TEST-PLAN #13353 — EAD suppresses handoff re-emit for an alive+active target agent

**Derived from the issue body "Suggested fix" — my own filed finding, observed live 2026-07-06 verifying #13335.**

Bug: the harness's ExternalActivityDetector re-emits `assigned-to` for a
handoff status (pending-test/pending-ship) every `_HANDOFF_REEMIT_SECONDS`
(600s) as an anti-starvation rescue (#12442), with no regard for whether the
target agent is demonstrably alive and working. Observed 18 redundant re-nudges
while verifier actively verified #13335 for ~3h (verifier's own transition
path is pending-test → pending-ship/reject, never in-progress, so the item
never looked "claimed" to the detector).

## Acceptance Criteria (independent reading — high-blast-radius, EAD dispatch path)

| AC | Contract |
|----|----------|
| AC1 | A handoff RE-emit (not a fresh transition) is suppressed when the target agent is `RUNNING` with an activity heartbeat inside the re-emit interval |
| AC2 | A **fresh transition** into a routed status is NEVER gated by this suppression — always reaches the agent regardless of its activity |
| AC3 | A silent (heartbeat older than the interval), stopped/stopping, or never-active agent is **NOT** suppressed — the #12442 rescue re-emit still fires |
| AC4 | Suppression is bounded/responsive: it lapses as soon as the agent's heartbeat gap exceeds the interval — never a fixed lockout once triggered |
| AC5 | Regression tests cover: active-suppressed, silent-not-suppressed, stopped-not-suppressed, absent-agent-backward-compat, fresh-transition-never-gated, boundary (exactly-at-interval not suppressed) |
| AC6 | Full static gate green; no regression to the pre-existing #12442 rescue-reemit test suite |

## Verification (branch squidsquad/task/13353, combined with current main)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | `TestHandoffReemitSuppressedUnit13353::test_running_recently_active_is_suppressed` | **PASS** |
| TC2 | AC1 | `TestEADHandoffReemitActivityGate13353::test_active_running_agent_suppresses_reemit` (full EAD path, not just the unit method) | **PASS** |
| TC3 | AC2 | `test_fresh_transition_never_suppressed` — active agent, fresh transition still emits | **PASS** |
| TC4 | AC3 | `test_running_but_silent_not_suppressed`, `test_never_active_not_suppressed`, `test_stopping_agent_not_suppressed_even_if_recent`, `test_silent_agent_still_reemitted`, `test_stopped_agent_still_reemitted`, `test_absent_agent_still_reemitted_backward_compat` | **PASS** |
| TC5 | AC4 | `test_boundary_exactly_interval_not_suppressed` (strict `<`, not `<=`) + structural review: `handoff_reemit_suppressed` recomputes `now - la` fresh on every poll, no cached/latched suppression state | **PASS** |
| TC6 | AC1, AC3 (verifier's own scenario) | **Independent** repro (not in the PR's own suite): simulated the exact #13335 scenario from the verifier side — actively-verifying qa (30s heartbeat) → suppressed; qa silent 3700s (e.g. post-crash/restart) → not suppressed | **PASS** |
| TC7 | AC5 | 10/10 new PR tests pass | **PASS** |
| TC8 | AC6 | All 7 pre-existing `TestEADHandoffReemit12442` tests still pass (17/17 combined); full static gate on combined state 5465/0 | **PASS** |

## Live-harness note

This modifies `harness.py`'s EAD dispatch path — the currently-running shared
harness's live re-emit logic. Verified entirely via direct unit/integration
calls against a patched `ExternalActivityDetector`/`AgentState` (as the PR's
own tests do, with `subprocess.run`/`time.time`/`_emit_event` mocked) — did
NOT restart the live shared harness. Worker's own comment notes a DeepSeek
review (NO_FINDINGS) was run given the high blast radius; I did not re-run an
independent DS pass but did independently reproduce the exact real-world
scenario (TC6) that motivated the fix, from the verifier's own perspective.

## Notes

- `type:issue`, severity:low (process/efficiency) — auto-approved, no human gate.
- No comprehension spec (code-only dispatch-logic change, not an LLM-consumed
  instruction).
