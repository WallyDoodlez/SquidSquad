# QA-RESULTS-11511 — PR mergeability flaps to CONFLICTING from transient-state commits

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #12223 (squidsquad/task/11511 → main) — PM-committed (operator-delegated unstick; skill was deadlocked on bg-gate-across-reboots #12142)
**Branch verified**: squidsquad/task/11511 @ b2a8b1ba6
**Verdict**: **PASS** (feature) + DM merge-reconciliation flag (config.md ship-counter)

## Delivered scope (Parts 1+2)
- **Part 1 (advisory):** git_ops.py `check_real_conflict(base, head)` — `git merge-tree --write-tree`
  in BOTH directions for deterministic conflict ground-truth; lets agents/DM treat GitHub's
  CONFLICTING flag as ADVISORY (GitHub honors no user .gitattributes merge driver server-side).
- **Part 2:** pre-commit state guard — `guard_staged_state()` + `install_hooks()` + tracked
  `references/git-hooks/pre-commit` shim + `.gitattributes eol=lf`. Unstages transient state
  from feature-branch commits (fail-open).

## AC Walk

### check_real_conflict (Part 1) — deterministic conflict truth
**PASS.** git_ops.py:991. Validates both refs (None/exit 2 if unresolvable), runs merge-tree both
directions, real conflict in either → False/exit 1, else True/exit 0. **Live-verified:**
`git_ops.py check-real-conflict origin/main origin/squidsquad/task/11511` → "CLEAN ... cosmetic",
EXIT=0 (correctly identifies this PR has no real conflict). Tests: TestCheckRealConflict11511 4/4
(clean, real-conflict, either-direction, unresolvable-ref).

### guard_staged_state (Part 2) — keep transient state off feature branches
**PASS.** git_ops.py:1043. Working branch / detached HEAD / branch-lookup-failure → no-op (fail-open);
feature branch → unstages files matching `_is_state_file` (SAME classifier commit_code uses) via
per-path `git reset -q HEAD`; never blocks a commit. Pre-commit shim is fail-open (always exit 0).
Tests: TestGuardStagedState11511 6/6 (working-branch noop, detached-head noop, 2× fail-open,
feature-unstages-state, code-only-noop).

### install_hooks — activation
**PASS.** Sets core.hooksPath to the tracked references/git-hooks (ships via installer-files.txt:53);
idempotent; does NOT clobber a foreign hooksPath; handles config-write / chmod failures.
Tests: TestInstallHooks11511 (7) + TestHookShippedExecutable11511 (hook tracked executable).

## Test Execution
- `pytest tests/test_git_ops.py` → **146 passed**, EXIT=0.
- Live check_real_conflict → CLEAN/EXIT=0.
- `python tests/run_tests.py static` → (see cycle output; green).
- DS re-review2 NO_FINDINGS (per PM); PM-verified full run_tests.py EXIT:0.

## FLAG for DM (merge-time reconciliation — NOT a feature defect, does NOT block ship)
The branch carries a STALE `.squidsquad/config.md`: **Shipped Since Last Bump = 12**, while
origin/main = **13** (DM incremented to 13 on #11745's ship). merge-tree confirms a merge resolves
to **12** → merging this PR as-is REGRESSES main's ship counter 13→12. config.md is `_is_state_file`
=True but is NOT in the `.gitattributes` merge=ours list (only working-state.md/current-state/
cycle-*.json/backlog-cache/BRIEFING.md are), so the merge takes the branch's stale value.
- Root: pre-guard artifact — the counter rode in via the Part-1 commit (82e8d4ba6) BEFORE the
  Part-2 guard existed. Going forward the guard unstages config.md on feature branches, so this
  won't recur.
- DM action: when merging PR #12223, reconcile the counter so main does NOT regress (exclude
  config.md from the merge, or reset Shipped Since Last Bump to the correct current value post-merge).
- Minor follow-up suggestion (PM/skill): consider adding `.squidsquad/config.md merge=ours` to
  .gitattributes for belt-and-suspenders, since it's classified as state yet absent from the
  overwrite list. (Not required — the guard already covers the going-forward path.)

## Verdict
**PASS → pending-ship.** The conflict-fix feature is correct, fully tested, and live-verified.
DM ships PR #12223 with the config.md counter reconciled at merge.
