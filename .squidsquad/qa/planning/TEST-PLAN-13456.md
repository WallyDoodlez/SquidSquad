# TEST-PLAN-13456 — harness deploy-pull survives untracked-file collision

**Source**: GitHub issue #13456 (PM bug report — observed behavior + scope). No formal AC list in body; ACs derived from the described defect + fix contract.
**Derived without reading the worker's test file (tests/test_feat_13456_deploy_pull_untracked_collision.py).**

## Acceptance Criteria (derived)

- **AC1** — A clone with an UNTRACKED local file at a path origin/main now TRACKS: `_safe_pull_in_clone` survives (returns ok=True), the merge lands, clone HEAD == origin/main, and the pulled/tracked content wins over the local untracked file.
- **AC2** — Regression (#13215): a DIRTY TRACKED file colliding with an incoming change still survives (ok=True, pulled wins). The untracked fix must not break the tracked-dirty path.
- **AC3** — A GENUINE merge conflict (committed divergence) fails the retry (ok=False, "pull-failed") and does NOT leave the clone in MERGING state (no .git/MERGE_HEAD), so the next deploy's `checkout main` is not wedged.
- **AC4** — A real-git regression test ships covering the untracked-collision case + the #13215 tracked case.

## Test Cases (real git repos; call the REAL harness._safe_pull_in_clone against a temp clone)

Harness: `_git_in_clone(clone_path, ...)` runs git with cwd=clone_path (harness.py:4971), so the helpers operate on any passed clone. Import harness in-process and call `_safe_pull_in_clone(clone)` directly.

### TC-1 (covers AC1): untracked local file at now-tracked path -> survives, pulled wins
- **Precondition**: origin/main advanced with a tracked file P=squad.txt="ORIGIN"; agent clone at base (no P committed) with an UNTRACKED P="LOCAL-UNTRACKED".
- **Steps**: call `_safe_pull_in_clone(agent_clone)`.
- **Expected**: returns (True, ...); agent HEAD == origin/main head; P content == "ORIGIN"; no .git/MERGE_HEAD.

### TC-2 (covers AC2, #13215 regression): dirty tracked file -> survives, pulled wins
- **Precondition**: base commits + pushes P="BASE"; origin advances P="ORIGIN2"; agent clone modifies P="LOCAL-DIRTY" (uncommitted, tracked).
- **Steps**: call `_safe_pull_in_clone(agent_clone)`.
- **Expected**: returns (True, ...); HEAD == origin head; P content == "ORIGIN2" (pulled wins); not MERGING.

### TC-3 (covers AC3): genuine committed conflict -> fail, not left MERGING
- **Precondition**: base P="BASE" pushed; origin commits P="ORIGIN-COMMIT"; agent clone COMMITS a divergent P="LOCAL-COMMIT".
- **Steps**: call `_safe_pull_in_clone(agent_clone)`.
- **Expected**: returns (False, "pull-failed..."); NO .git/MERGE_HEAD (merge --abort ran); agent HEAD still its local commit (origin not synced).

### TC-4 (covers AC4): regression test present
- **Steps**: assert tests/test_feat_13456_deploy_pull_untracked_collision.py exists; references untracked + #13215 coverage.

### TC-5 (guard): clean/up-to-date pull is a safe no-op
- **Precondition**: agent clone already at origin head, clean tree.
- **Steps**: call `_safe_pull_in_clone(agent_clone)`.
- **Expected**: returns (True, ...); HEAD unchanged; no stash left behind (git stash list empty).

## Coverage matrix
- AC1 -> TC-1
- AC2 -> TC-2
- AC3 -> TC-3
- AC4 -> TC-4
- (guard) -> TC-5

## Comprehension Questions
N/A — changes executable Python (harness.py), not LLM-consumed instructions.
