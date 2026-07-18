# TEST-PLAN-13557 — .claude/worktrees/agent-a6c409b5 tracked-but-missing

**Source**: GitHub issue #13557 body (Observed / Impact / Suggested fix — "any one closes it"). No formal AC list; issue is an improvement-scan finding, not a #9184-gated feature.
**Derived without reading the diff.**

## Test Cases

### TC-1 (untrack): stale worktree gitlinks removed from git index
- **Precondition**: repo at combined state (branch + fresh origin/main merged)
- **Steps**: `git ls-tree HEAD .claude/`
- **Expected**: only `.claude/settings.json` tracked; no `.claude/worktrees/*` entries
- **Verification command**: `git ls-tree HEAD .claude/`

### TC-2 (no status noise): git status clean for the class
- **Steps**: `git status --short | grep -i worktree`
- **Expected**: no output
- **Verification command**: as above

### TC-3 (recurrence prevention — the issue's own explicit concern): new worktree files are git-ignored
- **Steps**: create a probe file under `.claude/worktrees/`, run `git status --short` and `git check-ignore -v` against it
- **Expected**: probe does not appear in git status; check-ignore confirms it matches `.gitignore:70:.claude/worktrees/`
- **Verification command**: live shell probe (see QA-RESULTS)

### TC-4 (safety — no resurrection via #13556's restore guard): gitlinks excluded from the merge-drop restore guard
- **Steps**: run `tests/test_git_ops.py::TestRestoreMergeDroppedState13556::test_blob_sizes_excludes_gitlinks`; read the guard's `_state_blob_sizes` to confirm gitlink entries (ls-tree size `-`) are filtered
- **Expected**: PASS; gitlink deletions are never treated as a "drop" needing restoration (this was an observed-live bug per the test's own docstring, now fixed)
- **Verification command**: `pytest tests/test_git_ops.py -k gitlink`

### TC-5 (regression coverage for the issue's own flagged gap): static-gate coverage
- **Note**: issue explicitly asks "worth checking whether [#4829]'s gate coverage extends to `.claude/worktrees/*`". It does not (`TestGitignoreVolatileFiles.VOLATILE_PATTERNS` has no worktrees entry) — but TC-3 shows the `.gitignore` pattern alone already closes the recurrence vector (git won't track new files there). Non-blocking per the issue's own "any one closes it" framing (untrack + .gitignore fully satisfies option (a)+(b)). QA adds a small dedicated regression test (`tests/test_feat_13557_worktree_gitlinks_untracked_qa.py`) closing this loop explicitly rather than widening the shared #4829 list (different artifact category — gitlinks, not tracked-volatile-files).

## Coverage matrix
- Untrack → TC-1
- No status noise → TC-2
- Recurrence prevention → TC-3
- Restore-guard safety → TC-4
- Static-gate coverage gap (issue's own flagged concern) → TC-5 (closed via dedicated test, non-blocking)

No LLM-consumed instructions touched — no comprehension gate required.
