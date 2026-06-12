# Working State

- **Task**: none active — on main
- **Status**: none (idle)
- **Updated**: 2026-06-12 17:43
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## ⚠️ Session note
Booted PRE-v0.44.0; runs OLD composed CLAUDE.md (reboot pending per DM — do NOT self-reboot). /loop polling (cron 0bdc0ae0, 30m). Harness is UP (port 7373) but operator drives via /loop — staying loop-mode this session.

## Last cycle (1636, iter-446): #11504 re-unblocked (stale GitHub mergeability)
PR #11504 showed CONFLICTING/DIRTY again, but local merge-tree was CLEAN both directions — pure GitHub staleness (base main advanced via transient-state commits after cycle 1635's merge; .gitattributes is NOT the fix since there's no real content conflict). Merged origin/main into branch → ort auto-resolved working-state.md, added iter-445 (zero code). Static gate exit 0 (54 tests OK). Pushed 76d59f6b0. GitHub recomputed → MERGEABLE/CLEAN. Commented on #11394. Unblocked for QA merge.

## Watch
- **PR #11504 / #11394**: MERGEABLE/CLEAN as of cycle 1636. QA to merge + auto-merge. **On merge → resume #11503 fixes + #11505** (statusline cp + dm-manifest orphan + stale-test updates + capabilities deadwood), each removing its KNOWN_FAILURES entry.
- #11503 (high): umbrella; Group C triaged (2 real + 1 mixed + 1 stale). Groups A/B = stale-test/fixture cleanup, post-#11504.
- #11505 (low): capabilities deadwood removal; AC5/AC7 touch run_tests.py KNOWN_FAILURES → gated on #11504.
- #10690 / #10686 (E7, operator-manual): operator-gated, blocked.
- #11329 (approved): runtime per-event ack-cursor, multi-cycle, post-cutover fresh-session.

## ⚠️ Recurring conflict note
Distinguish TWO failure modes on PR #11504:
1. **Real content conflict** (merge-tree exits non-zero) → transient/shared state both sides edit → candidate for .gitattributes merge=union (see [[gitattributes_for_transient_state]]).
2. **Stale GitHub mergeability** (merge-tree exits 0 but GitHub shows CONFLICTING) → base advanced via transient commits, GitHub cached old result → fix is merge-main-into-branch + push to force recompute. THIS is what cycles 1635/1636 hit. .gitattributes does NOT help mode 2.
If mode 2 keeps recurring every cycle, root cause is cycle_post committing transient state (iterations/planning logs/working-state) to MAIN, advancing base. Candidate: stop tracking .squidsquad/<role>/planning logs on shared branches, or .gitignore them.
