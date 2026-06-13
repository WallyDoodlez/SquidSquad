# Working State

- **Task**: #11641 — stale scheduled_tasks.lock reclaim (COMPLETE, PR #11715) + #11640 (PR #11709)
- **Status**: in-progress (BOTH) — HELD pre-pending-test, gated on #11683 shipping (full-suite green)
- **Updated**: 2026-06-13 05:48
- **Branch**: squidsquad/task/11641 (current); #11640 work on squidsquad/task/11640
- **Quiet Cycle Counter**: 0

## ⚠️ Session note
Harness DOWN (port 59999, curl exit 7) — loop-mode (skill pinned stable per #11586). `/loop 30m` cron c8644353. cycle_pre/post wrappers DON'T fire — commit/push/PR MANUALLY. NOTE: working-state.md is per-branch in git — switching branches swaps it; this file on task/11640 vs task/11641 will differ. Git tree + issue status is truth (see [[learning-resume-git-tree-is-truth]]).

## TWO durable reboot-loop fixes — both DONE, both gated on #11683
| Issue | Fix | Branch | PR | Tests | State |
|---|---|---|---|---|---|
| #11640 | _get_clone_path raises (no REPO_ROOT fallback); all spawn paths refuse | task/11640 | #11709 | 237 pass; DS NO_FINDINGS | in-progress, gated |
| #11641 | thin_launcher reclaims stale scheduled_tasks.lock before Popen | task/11641 | #11715 | 37 pass; DS running (bxas30jg8) | in-progress, gated |

Both PR'd this/last cycle from prior-session WIP that was implemented but never committed/pushed (the resume-gap pattern). PM confirmed #11641 = durable #11612 fix.

## ⚠️ The shared gate: #11683 / #11657
Full suite has ONE red on every branch that has current main: `test_event_poll_exits_cleanly_when_harness_unreachable` — stale pre-#11601 contract. Fixed + verified + **pending-ship on PR #11683** (#11657, bundles #11503). NOT mine, NOT a regression in either of my PRs.
- **Next cycle**: check #11683 mergedAt. If shipped → for EACH of task/11640 & task/11641: merge origin/main, run `python tests/run_tests.py`, confirm green, transition → pending-test (PR #11709 / #11715). If still open, keep holding; nudge DM again if stale.
- DS reviews: #11640 = NO_FINDINGS (done). #11641 = bxas30jg8 running — read output, address real findings on PR #11715 before handoff.

## Standing (re-verify next cycle)
- **#11538 / PR #11564**: harness restart fix — was pending-test. Re-check ship/verify status.
- **#11511 (medium)**: PR mergeability flaps from transient-state commits (merge=ours not server-honored). Recommendation posted; awaiting PM/operator. NOT implementing (high blast radius).
- #10690 / #10686: operator/E6-E7 gated. #11586/#11587: harness event-mode bugs (open). #11505 (low): deadwood removal.

## Untracked scratch (leave; not part of any PR)
.claude/scheduled_tasks.lock.stale-bak (#11641 manual backup); .squidsquad/skill/planning/CODE-REVIEW-11601/11640/11641.md, DIFF-11641.patch.

## ⚠️ Recurring conflict note
PR CONFLICTING-while-locally-clean = merge=ours not honored server-side (#11511). Verify with `git merge-tree --write-tree origin/main origin/<branch>` (exit 0 = cosmetic). See [[learning-pr-conflicting-flag-can-be-cosmetic]].
