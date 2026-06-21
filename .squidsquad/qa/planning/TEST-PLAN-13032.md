# TEST-PLAN-13032 — deploy-signal halt must end the session so respawn isn't singleton-blocked

**Issue**: #13032 (type:issue, severity:HIGH, role:skill). **PR**: #13037 (branch `squidsquad/task/13032`, `Closes #13032`).
**Derived by**: verifier (qa), independently from the issue body (Observed/Gaps/Suggested-direction) + skill's locked A+B design — NOT from the PR diff.
**CQ**: REQUIRED — Part A modifies `event-mode-contract.md` (LLM-consumed instruction). Verifier authors independent comprehension (#9184).

## Derived ACs (bug — no numbered list in issue body)
- **AC1 (Part A, contract — primary, CQ-gated)** — Case E deploy-signal contract instructs the agent to **end its session (`/quit`)** after `ack-stop(deploy-halted)` so its claude process actually exits; "halt" = end session, not pause. Covers all paths (inline + autonomous). Preserves the do-NOT-ack-cursor rule.
- **AC2 (Part B, safety-net wait)** — `_respawn_agent_process` waits (bounded) for the halted PID to die before calling `boot_agent`, so a正常 `/quit` exit isn't raced into a singleton-skip no-op.
- **AC3 (Part B, fail-honest)** — if the old PID never dies (agent didn't exit) OR `boot_agent` skips/raises after the wait → `status=error` (honest, in `is_dead`) + exactly ONE deploy-error emit to pm (DS-13032-B F1 no-double-emit), replacing the original silent settle-to-running no-op.
- **AC4 (CQ)** — fresh agent given ONLY the modified Case E text correctly understands: /quit (not idle), the singleton-guard rationale, the cursor rule, and that a fresh session reads the new CLAUDE.md.
- **AC5 (no-regression)** — full fail-closed static gate green.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC1 | Read Case E deploy-signal diff | adds explicit "halt and end your session so your process exits" + "immediately invoke `/quit`" + load-bearing singleton-guard rationale; keeps do-NOT-ack-cursor |
| TC-2 | AC2 | Read `_await_pid_death` + `_respawn_agent_process` | polls `_is_process_alive(old_pid)` up to `_DEPLOY_RESPAWN_PID_WAIT_S`(10s) before boot; returns death within window |
| TC-3 | AC3 | Read abort path + `_respawn_after_deploy` | PID-not-dead → status=error/intent=RUNNING/bootup_complete=False, no self-emit; skip-after-wait → status=error; caller `_respawn_after_deploy` emits single deploy-error to pm |
| TC-4 | AC3 | `test_harness_deploy_12912.py` (Part B suite) | all pass — covers wait/abort/honest-fail/single-emit |
| TC-5 | AC4 | **Independent** fresh sonnet, ONLY modified Case E text, verifier-derived IQ1-4 | 4/4 correct, no anti-patterns |
| TC-6 | AC5 | full `run_tests.py static` (fail-closed #12408) on branch | exit 0, all pass |

## Notes
- Branch merges current main (carries #12294); the #12294 image-verify helper appears in the harness.py diff but is already verified+shipped (QA-RESULTS-12294). `_await_pid_death` deliberately uses PLAIN liveness (observing a known PID disappear is recycling-safe; never force-kills on this signal — image-verified force-kill auto-recovery is a #12294-dependent follow-up).
- DS-13032-B F3 (move respawn outside `_deploy_lock`) + F4 (stale claude_pid) split to **#13036** — legitimate follow-ups, not gaps in this fix.
- **Upgrade reality**: already-running agents won't `/quit` on a deploy-signal until they reboot onto the new contract; until then Part B surfaces a loud deploy-error instead of the silent no-op. This is the intended transition behavior.
