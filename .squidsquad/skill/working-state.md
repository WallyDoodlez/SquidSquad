# Working State

- **Task**: none (between tasks) — next: #12443
- **Status**: idle (just shipped #12442 to QA)
- **Updated**: 2026-06-15 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## >>> ON RESUME (fresh-cycle pickup order) <<<
**#12442 → pending-test (PR #12444)** — SHIPPED TO QA. EAD re-emits `assigned-to` for stuck handoff statuses on a 600s cadence (bypasses updatedAt filter); fixed single-emit + startup-blindness starvation. DS NO_FINDINGS (doc warn addressed). **Routing landed EAD-assigned-to-only (NO /work/assign endpoint)** — told PM to doc-sync HARNESS-ARCH §3/§4.3 + AGENT-RUNTIME §8.3/§5.2 to remove /work/assign.
Next pickup order: **#12443** (new approved, likely #12271 slice 2 — read it first) → **#12363** (/T teardown + killpg, design posted) → #12409 ask-1 → #12408 → #12397 → installer batch (#11613/#12419/#12420 serial) → #10690/#10686.
Operator directive (06-15, on #12418) stands: **proceed WIP-safe (commit incrementally + checkpoint every step), DS-review-per-change.**

## Shipped to QA / SHIPPED
- **#12418** → **SHIPPED** (PR #12441 merged) — SessionEnd-reason hook (#12271 liveness slice 1). 3 DS-reviewed components; C review caught a None-TypeError + breaker-bypass (fixed). Vault: [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]].
- **#12442** (NEW, open, medium, mine) — #12342 EAD gap: pending-ship→dm single-emit; if DM misses the one nudge there's no re-emit (same single-delivery limit as back-transitions). #12380 shipped fine (routing works), so likely emitted-but-missed → fix = delivery-robustness (re-emit cadence for unhandled pending-* / DM idle-rescan). **Fresh-cycle pickup** (don't debug EAD at 79% ctx).
- (orig) **#12418** → pending-test (PR #12441). SessionEnd-reason hook (#12271 slice 1). 3 components, each DS-reviewed: A (compose+settings.json native type:http hook, role via X-Agent-Role header from $SQUIDSQUAD_ROLE), B (harness ingest — NO_FINDINGS), C (reboot decision graceful-vs-crash; **DS caught a None-TypeError ERROR + a crash-loop-breaker bypass** → graceful no longer resets the streak, last_session_end cleared on all spawn paths). ~30 tests; full suite green (pytest exit codes). Endpoint header-based /hooks/session-end (PM affirmed shape). AC1 verifies by RUNNING compose. Residual deliberate-spam gap → #12271 hardening. DS-REVIEW-12418-{A,B,C}.md on main. Vault: [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]].

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

## APPROVED — top fresh-cycle pickups (operator batch-approved 2026-06-15; build at LOW context, not marathon-tail)
- **#12418** (task, approved, HIGH) — **#12271 slice 1: SessionEnd-reason hook.** TOP PICKUP. Add a `SessionEnd` hook (deployed per-clone via compose/installer `settings.json`) reporting exit reason+code → harness records on AgentState → reboot decision (§7.4) consumes it. Augments PID-poll (doesn't retire it). Design on main: HARNESS-ARCH §15.4 + §16. Multi-file (compose + harness + settings.json) → front-loaded plan + tests + DS review. De-risks the #12244 reboot-decision root.
- **#12271** (task, approved, high) — parent: progress-based liveness redesign (hooks + heartbeat, demote PID to teardown). Being delivered in SLICES; #12418 is slice 1. Subsumes #10855 + #12409-ask2.

## Pending-approval (not buildable yet)
- **#10025** (task, pending, low) — FULL capability-check framework retirement (absorbed #11505's scope). Mine once approved.
- **#12416** (task, pending, low) — delete thin_launcher.py / direct spawn (HARNESS-ARCH §14).

## Installer tasks (approved 2026-06-15, medium — fresh-cycle)
- **#11613** — installer dependency auto-provisioning (gather-all → …).
- **#12419** — installer migration-walk in wizard.py (INSTALLER-ARCH).
- **#12420** — installer post-commit harness restart (INSTALLER-ARCH).

## Budget note (this session)
Context ~56% at last check (threshold 70%) — ~14% headroom, insufficient to COMPLETE a high-blast-radius implementation (tests + DS review) cleanly. Deferring new implementation to a fresh cycle is the budget+quality call, NOT avoidance — all deferred items carry pinned RCAs + fix designs on their issues. **Operator/pressure-restart gives a clean fresh cycle** (better than marathon-tail partials).

**Fresh-cycle priority order:**
1. **#12418** (slice 1, HIGH) — SessionEnd-reason hook (de-risks reboot decision).
2. Reboot-churn hardening (open, high): #12409 ask-1 (freq breaker), #12408 (run_tests gate masking — fix EARLY, it hid my #12380 regression), #12397 (no-op recompose), #12363 (orphan kill-tree, design posted).
3. #12271 further slices (#12419/#12420 are installer, not liveness — #12271 has more liveness slices coming).
4. Installer batch: #11613, #12419, #12420 (medium).
5. Features: #10690 (sub-skill — CQ+DS+compose), #10686 (V2 migration smoke, manual).
6. Housekeeping: #10855 stale PR #10952 (close-as-superseded vs salvage — assess vs shipped #12342/#12380), #12294 (.claude-pid authority), #11716 (low).

## Process learnings this session
- DS per-change review caught real regressions in BOTH #12342 (back-transition dedup) and #12380 (duplicate alias) that forward-only tests missed. Hold pending-test for DS on high-blast-radius.
- #12380 regression: a test asserted the inverted invariant (qa absent = the bug). Tests must control config state, not depend on live `.local-config`. (QA vault: pattern-resolve-config-against-live-install-not-test-fixture.)
- Verify with pytest exit codes, NOT run_tests.py gate (#12408 masks failures).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
