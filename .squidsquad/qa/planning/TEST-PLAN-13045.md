# TEST-PLAN-13045 — Conflict-safe stash pop (clone-sync no longer leaves config.md markers)

- **Issue**: #13045 (type:issue, severity:high, role:skill) — Harness clone-sync leaves git-stash conflict markers in config.md → breaks compose for the whole fleet (compose-failed loop).
- **PR**: #13095, branch `squidsquad/task/13045`, HEAD `7cab0641a`. Files: `references/scripts/git_ops.py` (+56/-14), `tests/test_git_ops.py` (+115/-17). `Fixes #13045` (closing keyword), ready, no `review:human-required`.
- **Derived**: 2026-06-21 00:00. Bug (no explicit AC list); ACs derived from observed behavior + RCA. **Deterministic git plumbing → NO CQ.**
- **RCA confirmed (mine)**: `git stash pop` on conflict writes `<<<<<<< / ======= / >>>>>>>` markers into unmerged files and KEEPS the stash. The old `pull()` recovery ran only `git stash drop` (#4829 leak-prevention) — removes the stash entry but NOT the markers already written → config.md left corrupt → `compose.py` fails every recompose → fleet-wide compose-failed loop (only PM sees the events).
- **Method**: isolated worktree on branch HEAD; git_ops unit suite; full static gate; **independent raw-git smoke** reproducing the exact config.md stale-counter conflict.

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | On a stash-pop conflict, conflicted (unmerged) paths are restored to the pulled HEAD so **no `<<<<<<<` markers remain** → config.md parses → compose succeeds. | Raw-git smoke: markers=False, config.md = pulled value (50). |
| AC2 | The retained stash is dropped after force-resolution → no stash leak (#4829 preserved). | Raw-git smoke: stash list empty=True after resolve. |
| AC3 | Only the **conflicting** paths are reset to HEAD; non-conflicting stashed work is preserved (the rest of the popped stash stays applied). | Raw-git smoke: `keep.txt` retained `LOCAL-EDIT` while config.md was reset. |
| AC4 | `_safe_stash_pop()` is wired into BOTH `pull()` and the branch-switch helper `_safe_checkout` (`:657` both the checkout-fail restore and the checkout-success pop) — the latter previously used a bare `git stash pop -q` that didn't handle conflicts at all. | Diff: both call sites replaced. |
| AC5 | **DS Finding 1**: the drop is gated on *actual conflicts* (`--diff-filter=U` non-empty). A non-conflict pop failure (no stash entry / unrelated git error) returns False WITHOUT dropping → an un-applied stash is never discarded. | Code: `if not unmerged: return False` precedes any drop. |
| AC6 | Regression coverage: git_ops unit suite + real-git conflict test. | `test_git_ops.py` 151/151. |
| AC7 | No regression across the suite. | `run_tests.py static`. |

## Verification-harness note (transparency)
A first smoke attempt drove `git_ops._safe_stash_pop()` directly — but `git_ops._run` pins `cwd=REPO_ROOT` (it ignores `os.chdir`), so those calls executed against the **worktree's shared stash stack** rather than the temp repo, producing a false reading and dropping a few of the qa clone's ancient leaked stashes (cycles 78–691 cruft — themselves artifacts of the very bug being fixed). Working tree remained clean (no commits/source touched). The valid verification replicates the `_safe_stash_pop` algorithm with **raw git** in an isolated temp repo. Lesson: never drive `git_ops._run`-based helpers against a temp repo via chdir; replicate the algorithm or repoint REPO_ROOT.
