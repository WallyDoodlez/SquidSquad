# Working State

- **Task**: #11641 — stale scheduled_tasks.lock reclaim (COMPLETE, PR #11715) + #11640 (PR #11709)
- **Status**: in-progress (BOTH) — HELD pre-pending-test, gated on #11683 shipping (full-suite green)
- **Updated**: 2026-06-13 07:13
- **Branch**: squidsquad/task/11641 (current); #11640 work on squidsquad/task/11640
- **Quiet Cycle Counter**: 0 (iter-456: did real #11586 triage — not a quiet cycle)

## ⚠️ Session note
Harness DOWN (port 59999, curl exit 7) — loop-mode (skill pinned stable per #11586). `/loop 30m` cron c8644353. cycle_pre/post wrappers DON'T fire — commit/push/PR MANUALLY. NOTE: working-state.md is per-branch in git — switching branches swaps it; this file on task/11640 vs task/11641 will differ. Git tree + issue status is truth (see [[learning-resume-git-tree-is-truth]]).

## TWO durable reboot-loop fixes — both DONE, both gated on #11683
| Issue | Fix | Branch | PR | Tests | State |
|---|---|---|---|---|---|
| #11640 | _get_clone_path raises (no REPO_ROOT fallback); all spawn paths refuse | task/11640 | #11709 | 237 pass; DS NO_FINDINGS | in-progress, gated |
| #11641 | thin_launcher reclaims stale scheduled_tasks.lock before Popen | task/11641 | #11715 | 37 pass; DS NO_FINDINGS | in-progress, gated |

Both PR'd this/last cycle from prior-session WIP that was implemented but never committed/pushed (the resume-gap pattern). PM confirmed #11641 = durable #11612 fix.

## ⚠️ The shared gate: #11683 / #11657
Full suite has ONE red on every branch that has current main: `test_event_poll_exits_cleanly_when_harness_unreachable` — stale pre-#11601 contract. Fixed + verified + **pending-ship on PR #11683** (#11657, bundles #11503). NOT mine, NOT a regression in either of my PRs.
- **iter-456 (07:13)**: #11683 still unshipped (4th gated cycle). Stopped re-escalating (noise); pivoted to the #11586 root cause instead. Made the verifier's requested split-decision: the 03:33 qa "Monitor died — harness port not found" symptom (B) is NOT a new issue — it's the event_poll port-discovery failure already fixed by #11601 (live) + #11657's removal of the self-sabotaging test (port_file.unlink on shared .harness-port) in PR #11683. Strengthens #11683 priority: shipping it removes a test that kills live Monitors during any full-suite run (a real #11586 contributor). Posted decision on #11586. Vault: [[learning-tests-must-not-mutate-shared-live-state]]. (A) reboot→loop-mode remains the #11586 core; only diagnosable while harness is up (currently down on 59999) — operator/harness territory.
- **iter-455 (06:44)**: #11683 STILL OPEN/unshipped (3rd consecutive gated cycle). Confirmed systemic: entire pending-ship queue = just the #11683 bundle (#11657+#11503), MERGEABLE, ZERO DM activity ~90+ min → DM-starvation (harness down, DM not waking). ESCALATED to PM on #11586 with cross-cycle data + recommended operator manually ship #11683. ⚠️ NEEDS OPERATOR ACTION: manually ship #11683 (or wake DM) to unblock #11640+#11641. No new improvement finding (SKILL.md is doc/out-of-scope; avoiding backlog noise during firefight — #11716 filed last cycle).
- **iter-454 (06:14) re-check**: #11683 still OPEN (now MERGEABLE, mergedAt null) — both PRs still gated. PR health: #11715 CLEAN, #11709 mergeable UNKNOWN (transient compute, NOT conflicting — recheck). DS both NO_FINDINGS. Nothing to advance; ran quiet-cycle improvement scan → filed #11716.
- **Next cycle**: check #11683 mergedAt. If shipped → for EACH of task/11640 & task/11641: merge origin/main, run `python tests/run_tests.py`, confirm green, transition → pending-test (PR #11709 / #11715). If still open, keep holding; nudge DM again if stale.

## Standing (re-verify next cycle)
- **#11538 / PR #11564**: ✅ SHIPPED (merged 03:49Z, issue closed). Resolved — drop.
- **#11716 (low, NEW this cycle)**: improvement-scan — run_tests.py integration_only target list drifted (4 vs 6); filed, awaiting PM/human triage. Do NOT auto-fix.
- **#11511 (medium)**: PR mergeability flaps from transient-state commits (merge=ours not server-honored). Recommendation posted; awaiting PM/operator. NOT implementing (high blast radius).
- #10690 / #10686: operator/E6-E7 gated (E7=#10686 operator manual smoke, not done → #10690 stays gated). #11586 (high)/#11587 (medium): live harness event-mode investigation, multi-party, partly operator-gated (harness down) — watch, not a clean skill fix. #11505 (low): deadwood removal.

## Untracked scratch (leave; not part of any PR)
.claude/scheduled_tasks.lock.stale-bak (#11641 manual backup); .squidsquad/skill/planning/CODE-REVIEW-11601/11640/11641.md, DIFF-11641.patch.

## ⚠️ Recurring conflict note
PR CONFLICTING-while-locally-clean = merge=ours not honored server-side (#11511). Verify with `git merge-tree --write-tree origin/main origin/<branch>` (exit 0 = cosmetic). See [[learning-pr-conflicting-flag-can-be-cosmetic]].
