# Working State

- **Task**: none (idle)
- **Status**: idle
- **Updated**: 2026-06-14 (skill — event-mode session; harness restarted mid-session, EAD fix #12342 now live)
- **Quiet Cycle Counter**: 0

## Shipped this session
- **#12282** SHIPPED — reboot-churn root cause (test POSTing real /restart to live harness). Vault: [[learning-default-port-fallback-is-live-egress-trap-in-tests]].
- **#12244** SHIPPED — re-marked from stuck per PM AC-amendment (cause-agnostic backoff).
- **#12342** SHIPPED — event-mode EAD routes pending-test→qa / pending-ship→dm (was starving QA/DM). NOW LIVE (harness restarted — confirmed by receiving real routed assigned-to events; QA/DM pipeline now works end-to-end). Vault: [[learning-ead-status-routing-and-back-transition-dedup]], [[learning-runtime-resolves-by-alias-not-role-class]].
- **#12380** SHIPPED (PR #12391) — compose `.local-config` alias-keying (QA boots into PM's clone). QA rejected once (a clone-refusal test asserted the qa-absent BUG as its premise) → fixed by mocking `_get_clone_path`, re-verified, shipped. #11600 (role:pm) can close as tracked-under-#12380. PM can stop band-aiding `.local-config`.

## Filed (my domain, deferred to fresh cycle — all reboot-churn cluster)
- **#12409** (open, high) — slow reboot loop (>60s, #12244 backoff misses it). **Ask 1 = frequency-based breaker = my next pickup.** Ask 2 → #12271 (SessionEnd-reason); Ask 3 → #12363 (orphans). Triaged. qa stable on loop-mode stopgap.
- **#12397** (open, high) — l4_file_watcher emits restart-required on NO-OP recompose (got a spurious one, declined to reboot). Fix design in issue.
- **#12408** (open, high, QA-filed) — run_tests.py static gate exits 0 despite failing tests (masked my #12380 regression). Use pytest exit codes until fixed.
- **#12363** (open, medium) — orphan claude/event_poll accumulation.
- **#10855** (in-progress, QA FAIL-back) — inert/zombie boot. FAIL reason was "harness down, couldn't test AC-4 live" (not a code defect found); real fix overlaps #12271 progress-based liveness. Effectively blocked on #12271.

## Approved (next feature work)
- **#10690** (approved, medium, gate lifted) — Wiki-link rework + documentation-linkage sub-skill (LLM-consumed → CQ + DS-review + compose).
- **#10686** (approved, medium) — PRD-E E7 V2 migration smoke.

## Resolved / off-plate
- **#11505** — PM pipeline-sentinel **verified my analysis** and ruled it superseded-by-#10025 (capability-check is one load-bearing unit owned by #10025; #11505's only bounded scope was already done in the 05-27 cleanup). PM recommends OPERATOR close it (part of an operator bundle). skill: stay off it; capability-check resumes under #10025. **Done — no skill action.**

## Pending-approval (future skill work — not buildable yet)
- **#10025** (task, pending, low) — now owns the FULL capability-check framework retirement (`capability-check.md`, `capability_check.py`, DM wiring, PM task-intake step 7, INSTALLER-ARCH §8). Mine once approved.
- **#12271** (task, pending, high) — progress-based liveness redesign; subsumes #10855 + #12409-ask2. Major skill work once approved.
- **#12416** (task, pending, low) — delete thin_launcher.py / direct spawn (HARNESS-ARCH §14).

## Process learnings this session
- DS per-change review caught real regressions in BOTH #12342 (back-transition dedup) and #12380 (duplicate alias) that forward-only tests missed. Hold pending-test for DS on high-blast-radius.
- #12380 regression: a test asserted the inverted invariant (qa absent = the bug). Tests must control config state, not depend on live `.local-config`. (QA vault: pattern-resolve-config-against-live-install-not-test-fixture.)
- Verify with pytest exit codes, NOT run_tests.py gate (#12408 masks failures).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
