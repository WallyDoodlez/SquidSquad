# QA-RESULTS #13569 — boot-drain deploy-signal deferred until boot completes (agent-side)

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps)
**PR**: #13573 (squidsquad/task/13569)
**Branch verified on**: squidsquad/task/13569 (2 commits, built directly on current main — no staleness)

## AC walk

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | boot-drain signal not honored on-reach | Case E prose: "Hold it — do NOT ack-stop and do NOT ack-cursor it" | **PASS** |
| AC2 | drain stops at the signal, no loss | "Stop the boot drain here... Events after it stay in the deque behind your held cursor and re-deliver to your respawned session" | **PASS** |
| AC3 | boot completes before honoring | "Finish your boot. Reach the post-drain boundary..." | **PASS** |
| AC4 | honor at post-drain boundary, before idle/new work | "before entering the idle/improvement-scan cool-down loop and before picking up any new work_queue() item" | **PASS** |
| AC5 | finish-first + Case C gate for boot-resumed task | Case E bullet + Case C step 3 exception, cross-consistent | **PASS** |
| AC6 | steady-state unchanged | "Steady-state (post-boot): honor it only at a between-task boundary..." — unchanged from pre-fix text | **PASS** |
| AC7 | no loss on crash/restart during deferral | "your cursor never advanced past the signal... re-delivers in your next boot drain and is deferred-then-honored again" | **PASS** |
| AC8 | regression test + static gate | `TestBootDrainDeploySignalDeferral` 4/4; full static gate 5476/0 | **PASS** |
| AC9 | comprehension gate (QA-owned) | fresh sonnet agent, file-only, 4/4 correct, 0 must_not violations | **PASS** |

## Comprehension gate (#9184)

LLM-consumed instruction change (`event-mode-contract.md`, runtime-loaded by every role at boot — I loaded this exact fragment at my own boot this session, pre-fix version, since this PR is not yet merged to main). Spawned a fresh `general-purpose` (sonnet) agent, given **only** the modified file, explicitly instructed to use no other file, tool, or prior knowledge. 4/4 questions answered correctly with accurate supporting quotes, covering AC1–AC7 (hold-on-reach, honor timing, finish-first + Case C gate, steady-state contrast, crash-safety). Spec + evidence: `tests/comprehension/13569_spec.json`.

## Corroborating the worker's DeepSeek review claim

Worker's Discussion comment claims a DeepSeek pass found 3 gaps, all fixed in commit `4795807d3` (F1 stop-the-drain, F2 Case C gate + finish-first, F3 context-loss re-delivery). I didn't take this on faith — independently confirmed all three fixes are actually present, verbatim, in the merged diff I reviewed (not just asserted in the PR description). See TEST-PLAN TC3.

## Test runs

- Worker's own regression: `TestBootDrainDeploySignalDeferral` — 4/4 PASS
- Full static gate: 5476 gated, 0 failures, 0 errors
- Comprehension: 1 fresh-agent CQ run, 4/4 correct

## Housekeeping finding (self-resolved, not routed to worker)

While verifying, found `tests/comprehension/13175_spec.json` — the CQ spec for the issue this PR explicitly supersedes ("supersedes #13175's boot-drain 'honor on reach' for the boot-drain case") — still asserts the now-superseded answer (HONOR on-reach) as its recorded "PASS" expected behavior. Left unannotated, this is a live hazard: a future agent or audit consulting that file would be told the *old, buggy* behavior is correct, risking a regression back to the #13569 bug. This is a QA-owned artifact (I author comprehension specs, not the worker) and not a defect in the PR's own scope, so I did not route it back to skill — I annotated `13175_spec.json` in place with a `superseded_by: 13569` field and an explanatory note pointing to the current spec, per the "preserved tests are permanent, never deleted" rule (annotate, don't delete). No production code or PR-owned artifact was touched.

## Notes

- `type:issue`, severity:**high** — auto-approved, zero-gap standard applied without exception.
- Out-of-scope confirmed correctly excluded: the #13175 residual-vs-live deploy-signal ambiguity is a distinct surface (deploy-failure, not boot-drain honor-timing) and remains untouched — the new text still forbids self-assessing drift.
- No harness.py change needed or made; `common-events/` fragments are runtime-Read (not compose-inlined) per `docs/sub-skill-catalog.md`, so no recompose is required for this to take effect at next boot — confirmed against the PR's own "no recompose needed" claim.
- No new production regression test to promote beyond the worker's own (already in `tests/`); my own regression artifact for this task is the comprehension spec, which lives permanently under `tests/comprehension/`.
