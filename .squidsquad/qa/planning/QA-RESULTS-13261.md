# QA-RESULTS-13261 — git_ops.pull merge-abort on a genuine-conflict retry

**Verdict: PASS — zero gaps.** PR #13266 merged (squash). (skill-filed during #13215 DS-review; the every-agent cwd pull path sibling of the deploy-path #13215 fix.)

## AC walk (independent — derived from issue body)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | retry pull that conflicts → `git merge --abort` runs BEFORE `_safe_stash_pop` | PASS |
| AC2 | clone NOT left MERGING (no MERGE_HEAD) | PASS |
| AC3 | stashed local change PRESERVED, not silently dropped | PASS |
| AC4 | no conflict markers leaked into the tree | PASS |
| AC5 | pull reports failure (returns False) → caller recovery | PASS |

## Evidence
- Code (git_ops.py:291-307): `_run("git merge --abort", check=False)` added before the `_safe_stash_pop()` on the retry-failure branch (mirrors #13215's deploy-path fix). **Bonus correctness:** the retry pull is pinned to `git pull --no-rebase` so the abort verb (`merge --abort`) matches what a failed retry leaves — guards against a clone-local `pull.rebase=true` leaving a REBASE state the abort can't clear, and matches the project always-merge rule.
- skill test (test_git_ops.py `TestPull::test_pull_retry_fail_aborts_merge_before_pop`): asserts abort called, abort precedes stash pop, retry is a merge pull. PASS.
- **QA independent REAL-git test** (`tests/test_feat_13261_pull_merge_abort.py`): builds origin+clone with a dirty file (B touches it → first pull aborts) AND a committed divergence (conflicts on the retry merge), then calls `git_ops.pull()`. Proves: pull returns False, **clone NOT left MERGING**, no markers leaked, and the **stashed dirty change is PRESERVED** (a.txt = `local-a-dirty-uncommitted`, NOT dropped). Without the fix `_safe_stash_pop` would misread the merge's unmerged paths and drop the stash. ALL PASS.
  - *Test-craft note*: `git_ops._run` pins `cwd=str(REPO_ROOT)` (a module global), so the function always operates on REPO_ROOT — an `os.chdir` into a temp clone has **no effect** (caught this during verification: an initial chdir-based draft silently ran against the real repo). The correct way to point a real-git test at a clone is `patch.object(git_ops, "REPO_ROOT", clone)`. (Unlike #13215's `_safe_pull_in_clone(clone_path)`, which is genuinely clone-aware via a parameter.)
- No-regression: full `tests/test_git_ops.py` = 167 passed, 0 failures.

## Non-blocking observation (flagged for triage, NOT a reblock)
The **first** `git pull` (git_ops.py:267) is still bare (not `--no-rebase`) while the retry is now pinned. Under a misconfigured clone-local `pull.rebase=true`, a first-pull rebase-conflict would leave a REBASE state and `git stash` would then fail (→ pull returns False mid-rebase). Out of #13261's AC scope; requires a config that contradicts the project always-merge rule; pre-existing. Worth a one-line follow-up to pin the first pull to `--no-rebase` too for consistency — does NOT block this ship.

Status: pending-test → pending-ship.
