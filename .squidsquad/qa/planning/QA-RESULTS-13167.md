# QA-RESULTS-13167

**Issue**: #13167 (P0) — git_ops stash+pull+pop pops a PRE-EXISTING stash on clean tree → tree-wide conflict markers break compose
**PR**: #13168 (branch squidsquad/task/13167 @ 105f33f8f, base main; git_ops.py + tests/test_git_ops.py, +131/-14)
**Verdict**: ✅ **PASS — zero gaps**
**Verified by**: verifier (qa), 2026-06-21 18:55 — verified on a clean worktree with a revert-the-fix proof.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 guard clean-tree no-op pop | ✅ PASS | New `_stash_top_ref()` (SHA of refs/stash or ""); `pull()` captures pre_stash_ref, computes `stashed = post != pre`, only pops when `stashed`. Clean tree → "Pulled (no local changes to stash)", NO pop. Same guard added to `_safe_checkout()`. Pull-fail branch's raw `git stash pop` replaced with `if stashed: _safe_stash_pop()` |
| AC2 regression catches P0 | ✅ PASS | test_pull_clean_tree_does_not_pop_preexisting_stash (pre/post refs/stash unchanged → asserts no "git stash pop") + test_pull_clean_tree_pull_fail_does_not_pop_preexisting. **Revert-proof**: reverted ONLY git_ops.py → BOTH tests FAIL ("Pulled (stashed and popped)" — old code pops regardless). Restored → pass |
| AC3 no regression | ✅ PASS | test_git_ops.py: 160 passed on fixed branch; static gate 4896/0/0 |

## Findings

Correct, root-cause-targeted P0 fix. The core defect — `git stash` exits 0 on a clean tree without creating a stash, so the subsequent pop applies a pre-existing (ancient) stash — is fixed by comparing refs/stash before/after and popping only what we created. Applied to BOTH stash+pop sites (pull + _safe_checkout) and the previously-raw pull-fail pop now uses the marker-safe _safe_stash_pop. This neutralizes the fleet-wide landmine: accumulated ancient stashes in any clone will no longer be popped by a clean-tree pull.

Scope note: the fix targets direction (a) (guard) thoroughly. It does not clear accumulated stashes (direction c — that was PM's manual recovery) nor expand _safe_stash_pop marker-stripping (b) — both are moot now: the guard prevents the ancient-stash pop scenario entirely, and _safe_stash_pop is now used on every pop branch. Complete for the P0.

**Health follow-up (separate from this verdict):** the issue notes other clones (incl. qa) may carry their own ancient stash piles — harmless once this fix deploys, but a latent hazard while a clone still runs the old git_ops. Checking my own clone's stash pile separately.

## Disposition

Verdict PASS → transition pending-test → pending-ship. Regression tests committed in PR (tests/). Merge + ship deferred to DM. QA-RESULTS-13167 on qa planning.
