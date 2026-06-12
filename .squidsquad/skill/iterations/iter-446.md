# Iteration 446 (cycle 1636)

**Time**: 2026-06-12 17:44
**Type**: unblock (PR mergeability)

## Summary
PR #11504 (#11394: auto-discover static-gate tests) showed CONFLICTING/DIRTY on GitHub, but local `git merge-tree --write-tree` exited 0 in BOTH directions against the exact head/base SHAs — no real content conflict. Diagnosed as stale GitHub mergeability: base `main` advanced via transient-state commits (cycle 1635 post-wrapper landed 6cb28bc07 on main) after the branch's last merge, and GitHub cached the pre-recompute CONFLICTING.

## Action
- Merged origin/main into squidsquad/task/11394 (always merge, never rebase) — ort auto-resolved working-state.md, added iter-445; zero code change.
- Static gate green: `run_tests.py --static` → 54 tests OK (2 skipped).
- Pushed 76d59f6b0 → GitHub recomputed → MERGEABLE/CLEAN.
- Commented unblock on #11394; returned to main.

## Outcome
PR #11504 unblocked for QA merge. Downstream #11503 fixes + #11505 remain gated until merge.

## Note
Recorded in working-state: distinguish real content conflict (merge-tree non-zero → .gitattributes) vs stale GitHub mergeability (merge-tree zero → force recompute). Root cause of recurrence: cycle_post commits transient state to main, advancing base.
