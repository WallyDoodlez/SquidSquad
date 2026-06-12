# Working State

- **Task**: #11512 — thin_launcher hardcodes /loop spawn prompt (forces loop mode, event mode never reached)
- **Status**: in-progress — impl committed + tested; awaiting DS review before pending-test
- **Branch**: squidsquad/task/11512
- **Updated**: 2026-06-12 18:05
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## ⚠️ Session note
Booted PRE-v0.44.0; runs OLD composed CLAUDE.md (reboot pending per DM — do NOT self-reboot). Harness UP (port 7373) but operator drives via /loop — staying loop-mode this session. NOTE: #11512 (this task) is the ROOT CAUSE of why I'm in loop mode — the launcher forces /loop. Fix does NOT affect already-running agents until respawn.

## Current task #11512 (cycle 1637, iter-447) — IMPL DONE, DS review pending
Fix (option 1, mode-neutral spawn prompt): thin_launcher.py _SPAWN_PROMPT replaces `/loop {interval}m ...`; boot Step 1 owns mode selection (single source of truth; options 2/3 = parallel control path, HARNESS-ARCH forbids). Removed dead _get_interval. Rewrote #9725 unit (test_thin_launcher.py, 31 pass) + live (test_feat_9725...live.py, 3 pass) tests to #11512 contract. Canonical gate run_tests.py = 54 OK. Committed 9a2adacea on branch.
- **DS review**: running in background (id b44sbq78t → DS-REVIEW-11512.md). On exit 1/2/3 fall back to Sonnet subagent. MUST confirm no regression before pending-test.
- **NEXT (after DS PASS)**: transition pending-test, pr-create (check review:human-required), push. CQ: spawn prompt is a launcher constant (deterministic, unit-tested), NOT composed agent instructions — boot Step 1 contract unchanged; flag to PM/verifier whether CQ AC needed (do not self-gen).
- 18 test_feat_9588 reds are PRE-EXISTING (#11503 test-debt, FileNotFoundError on moved boot-bootstrap.md) — confirmed via stash, independent of this change.

## Watch
- **PR #11504 / #11394**: SUBSTANTIVELY mergeable (merge-tree clean both dirs); GitHub flag flaps. STOPPED hand-nudging. QA to merge on content. On merge → resume #11503 fixes + #11505.
- **#11511 (filed cycle 1636)**: durable fix for transient-state merge flap — awaiting PM triage.
- #11503 (high): test-debt umbrella, post-#11504.
- #10690/#10686 (E7): operator-gated.

## ⚠️ Recurring conflict note
Two #11504 failure modes: real conflict (merge-tree non-zero → .gitattributes union) vs stale GitHub mergeability (merge-tree zero → force recompute, whack-a-mole; root cause = transient state to main; tracked #11511). See [[learning-pr-conflicting-flag-can-be-cosmetic]].
