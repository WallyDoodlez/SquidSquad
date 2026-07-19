# TEST-PLAN-13728 (bundled with #13729/#13730, shared branch `squidsquad/task/13728`, PR #13734)

Derived independently from all three issue bodies (`type:issue` bug reports). Not read from the PR diff before writing this plan.

## ACs (from issue bodies)

### #13728 (git_ops.py harden_stdio wiring)
- **AC1**: `git_ops.py`'s `main()` calls `harden_stdio()`, matching the other 9 wired scripts' pattern.
- **AC2**: The 4 named live print() literals (lines ~1314, ~1938, ~2149, ~2501) no longer contain a raw non-ASCII decorative character that would crash `UnicodeEncodeError` on a cp1252 console — either via ASCII-sweep or `harden_stdio()`'s own escaping (issue accepts either as sufficient).
- **AC3**: `git_ops` is added to `test_cli_stdio_13198.py`'s `TestFleetWiring13198.WIRED` list, so the sweep guard locks this in going forward.

### #13729 (scan_index.py role-aware filtering)
- **AC4**: `suggest_targets()` for `role=pm` excludes `references/scripts/` and `tests/` from its results.
- **AC5**: The scope boundary (the deeper `.squidsquad/`-exclusion gap, not fixed here) is explicitly disclosed, not silently left as an undocumented gap.
- **AC6**: Other roles' `suggest_targets()` behavior is unaffected (this is a pm-specific filter, not a global behavior change).

### #13730 (commit_code branch-flip visibility)
- **AC7**: A prominent stderr/stdout line makes the working-tree switch back to main explicit in the transcript when `commit_code()` runs.
- **AC8**: `git-commit.md` sub-skill documents the branch-flip-back behavior for multi-step branch workflows.
- **AC9**: The underlying behavior (switching back to main) is UNCHANGED — this issue is explicitly a visibility fix, not a behavior fix (skill's own investigation confirmed the flip is deliberate/load-bearing per #13613, commit_state() requires being on the working branch).

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | `grep -n "harden_stdio" references/scripts/git_ops.py` — confirm import + call in `main()`. |
| TC2 | AC2 (live) | Independently re-run the same AST-based non-ASCII print scan the issue's own repro used, against the branch's git_ops.py — confirm 0 matches, or confirm harden_stdio() wraps stdout before any of the 4 lines can fire raw. |
| TC3 | AC3 (live) | `python -m pytest tests/test_cli_stdio_13198.py -v` — confirm git_ops is in WIRED/SWEPT and the fleet-wide sweep test passes with git_ops included. |
| TC4 | AC4/AC6 (live) | Call `scan_index.suggest_targets("pm", count=5)` directly — confirm no `references/scripts/` or `tests/` paths in results. Call for a non-pm role (e.g. `skill`) — confirm unaffected (still returns code files as before). |
| TC5 | AC5 | Read the PR body / regression test for the explicit scope-boundary disclosure. |
| TC6 | AC7 (live) | Run a real `commit_code()` call in a disposable branch, capture output — confirm an explicit "switched to main" (or equivalent) line appears. |
| TC8 | AC8 | Read `references/sub-skills/common/git-commit.md` for the new documentation. |
| TC9 | AC9 (live) | Confirm `git branch --show-current` after a real `commit_code()` call is still `main` — behavior unchanged, only visibility added. |
| TC10 | (regression) | Skill's own regression tests for all 3 fixes + full test suite / static gate. |

## Note

Three issues, one branch, one PR — verifying all three together since they share test-execution context (same branch, same suite run), but each AC set is independently derived from its own issue body.
