# Working State

- **Task**: #9965 catch-up nearly done ((3a)+(3b) landed, (3c) pending). #9967 SHIPPED. #9999 filed (skill-owned). #9998 Q1-Q5 locked in conversation thread — significant scope add.
- **Status**: pipeline healthy, no PM action needed
- **Last Processed Event ID**: df9f33751a6a (still stale; #9967 fix is shipped but our session is mid-flight — harness cursor should advance on next agent restart)

## Pipeline snapshot (2026-05-24 00:43, cycle 1625)
- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external untriaged
- 1 approved (long-running, DM lane): #3 (going-public)
- 2 in-progress:
  - #9965 (skill, 6274.2 / AC2.8) — (3a)+(3b) DONE (commits 2afacb77 + cycle 1333 commit). Remaining: (3c) WIZARD.md prose + 1 test_wizard_runbook test. Suite trajectory: 14 → ~6 after 3a → ~4 after 3b → ~3 after 3c. The 5 test_wizard.py tests stay red (couple to wizard.py D4, still frozen by STOP).
  - #9968 (PM, EPIC L1-L4 doc) — no PM work this cycle; effectively superseded in conversation by #9998 Q1-Q5 lock-in (which IS #9968 doc rewrite work; needs reconciliation when #9998 is picked up).
- 1 pending-ship: (none — #9967 just shipped)
- 2 pending tasks (PM): #9996 (preset catalog), #9998 (multi-worker doc + Q1-Q5 lock) — both awaiting discussion-phase pickup; coupled
- 1 pending (gated): #9966
- 2 planning (skill, stale): #9874, #9875
- 1 planned (skill, stale): #9845
- 2 issues at status:open: #9969 (manifest naming), #9970 (composed-md drift), and #9999 (ship-gate false-positive, severity:low, role:skill, auto-routed)
- shipped_since_bump: should now be 7 of 10 (after #9967 ship)

## #9967 — SHIPPED this interval
DM closed at Z 04:21. Fix: event_bus_reader.query() honors harness eviction signal. Live fix means once any agent restarts, the cursor-stuck symptom we've seen all session ends. Our current session predates the deploy — the eviction message at top of cycle_pre output this cycle is the OLD behavior printing the warning before exiting; expected.

## #9999 — filed by DM, routed to skill
Ship-gate falsely blocks squash-merged PRs (ancestry check fails because squash creates new SHA on main). DM provided RCA + workaround + suggested fix in body (more than behavior-only — DM's call, not PM's to police). Severity:low, role:skill, status:open. Per auto-approve-bugs memory: no PM gate needed; skill picks up on next dev cycle. DM workaround (branch-delete + fetch + retry) costs 3-5 commands per ship but unblocks deliveries in the meantime.

## #9965 — (3a)+(3b) landed, (3c) is the last piece
Next expected: skill cycle 1334+ lands (3c) WIZARD.md prose. After that, curated suite should be at ~3 failures, all in test_wizard.py / test_manifest_registry.py that couple to wizard.py D4 — those stay red until human lifts AC2.4-2.7 freeze.

## In-session #9998 Q1-Q5 lock-in (captured as tracker comment cycle 1624)
Architectural decisions landed:
- Same-class agents = scaling, not specialization (identical replicas)
- Composed-output uniformity guarantee (compose.py verify-class-uniformity)
- Routing by class, instance-pick post-routing
- EAD adds human-comment → pm rule (event_context=human-message; PM patches missing role labels)
- Subloop runner declared in roster
Scope add: preset manifest schema gains count/instance_names/subloop_runner; PM L2 gets human-message triage section; INSTALLER-ARCH §1.1 clarifies scaling-not-specialization.

## #9968 / #9996 / #9998 — convergence note
#9998 Q1-Q5 decisions ARE substantive #9968 doc-rewrite content. When #9998 is picked up, need to decide: (a) fold #9998 doc-edits into #9968 EPIC and close #9998 as covered, or (b) close #9968 doc-only scope as superseded by #9998. Suggest the latter — #9998 has the locked contract, #9968 was the EPIC umbrella that's now narrower than #9998 + #9996.

## #9966 — unchanged (gated)
