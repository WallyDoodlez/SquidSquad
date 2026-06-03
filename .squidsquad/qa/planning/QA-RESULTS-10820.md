# QA-RESULTS-10820

**Run**: 2026-06-03 13:47 (qa cycle 623)
**Branch**: `squidsquad/task/10820`
**PR**: #10953
**Verdict**: **FAIL** — code AC-1 and AC-2 PASS but no regression tests cover the new behavior (AC-4 + AC-5 fail). Routing back to in-progress.

## AC walk

| AC | Statement | TC | Result |
|----|-----------|----|--------|
| 1 | DM/PM/other arm pre-checks-out the working branch before `commit-role-scoped`. | TC-1 | PASS — block at `cycle_post.py:610-614` reads current branch, compares to `working = _get_working_branch()`, and `git checkout working` if mismatched. Structurally mirrors QA arm. |
| 2 | `_warn_if_role_files_uncommitted` re-checks `git status --porcelain` post-commit and emits a loud stderr WARNING for stranded role-owned files. Both arms call it. | TC-2 | PASS — helper defined at `cycle_post.py:452-499`; QA arm calls it at L606, DM/PM/other arm calls it at L621; WARNING (#10820) tag on stderr; truncates the file list at 20 with overflow note. |
| 3 | Existing `commit_role_scoped` return-value contract preserved (5+ tests still assert `result is False` for noop). | TC-3 | PASS — `pytest tests/test_cycle_post.py tests/test_git_ops.py`: 224 passed / 1 failed. The single failure is `.squidsquad/.backlog-cache` gitignore noise — confirmed pre-existing on `main` (`.backlog-cache` is tracked from commits `9e867192` and `7fee9b39`, unrelated to this PR). |
| 4 | Regression test for the DM/PM/other arm pre-checkout. | TC-4 | **FAIL** — no test in `tests/test_cycle_post.py` exercises the pre-checkout block. `grep "pre_checkout\|working_branch.*checkout"` returns nothing. |
| 5 | Regression tests for the `_warn_if_role_files_uncommitted` helper (stranded → WARNING / clean → silent / non-role-owned M → silent). | TC-5 | **FAIL** — no test references `_warn_if_role_files_uncommitted`, and no fixture exercises the stranded-files WARNING path. `grep` for the helper name across `tests/` returns zero matches. |

## Test runs

### TC-1 (pre-checkout grep)

```
$ grep -n "current_branch != working\|git checkout.*working\|_get_working_branch" references/scripts/cycle_post.py
…
610:        working = _get_working_branch()
611:        current = _run(["git", "branch", "--show-current"], check=False)
612:        current_branch = current.stdout.strip() if current.returncode == 0 else ""
613:        if current_branch != working:
614:            _run(["git", "checkout", working], check=False)
```

### TC-2 (helper grep)

```
$ grep -n "_warn_if_role_files_uncommitted\|WARNING.*#10820" references/scripts/cycle_post.py
452:def _warn_if_role_files_uncommitted(role, target_label):
473:        from git_ops import _role_owned_patterns, _path_matches
479:    patterns = _role_owned_patterns(role)
491:            f"WARNING (#10820): commit-role-scoped left {len(stranded)} role-owned "
606:        _warn_if_role_files_uncommitted(role, "QA → main")
621:        _warn_if_role_files_uncommitted(role, working)
```

### TC-3 (existing suite)

```
$ python -m pytest tests/test_cycle_post.py tests/test_git_ops.py
…
1 failed, 224 passed in 26.22s
FAILED tests/test_git_ops.py::TestGitignoreVolatileFiles::test_volatile_files_not_tracked
  AssertionError: Volatile file(s) still tracked in git index: ['.squidsquad/.backlog-cache']
```

Pre-existing on main — `.squidsquad/.backlog-cache` is tracked from commits `9e867192` + `7fee9b39`, neither part of this PR.

### TC-4 (FAIL — missing pre-checkout regression test)

```
$ grep -rn "pre_checkout\|test.*dm.*checkout\|test.*working_branch.*checkout" tests/test_cycle_post.py
(no matches)
```

Bug: the original bug (DM commits landing on the wrong branch / failing silently because the DM arm lacked pre-checkout) has no regression test to catch a future drift. Without a test, the next refactor of `_do_commit_push` can re-introduce the silent-failure mode unnoticed.

### TC-5 (FAIL — missing WARNING helper regression tests)

```
$ grep -rn "_warn_if_role_files_uncommitted" tests/
(no matches)
```

The helper has three observable behaviors that need coverage:
- (a) role-owned `M` files present → WARNING with file list on stderr.
- (b) clean working tree → no WARNING.
- (c) `M` file that does NOT match the role's `_role_owned_patterns` → no WARNING.

None of these are tested. The fix is purely additive (new file in stderr stream), and `tests/test_cycle_post.py` already has patterns for monkeypatching `_run` and `_run_script` — so test infrastructure is in place. No "no testable surface" justification appears in the PR body.

## Decision

Code-side ACs 1–3 PASS. Regression-test ACs 4 and 5 FAIL.

Per `.squidsquad/qa/SOUL.md`:
- "New code has corresponding unit tests — no shipping untested code."
- "Bug fixes include regression tests that would have caught the original bug."
- "Anti-pattern: Marking Pending Ship when new code has no corresponding tests."

Per the issue body's "Suggested fixes" + skill-lead's cycle-1568 scope commitment, both AC-1 and AC-2 are in scope; the missing tests for them are in scope for this PR (not "follow-up").

**Routing back to in-progress with the gap list above.** Skill-lead's next pass should add:
- A test exercising the DM/PM/other arm with the working tree starting on a non-working branch, asserting `git checkout` to `working` is invoked before `commit-role-scoped`.
- Three tests covering `_warn_if_role_files_uncommitted` (stranded → WARNING; clean → silent; non-role-owned M → silent), patterned after the existing `_run`/`_run_script` monkeypatching style in `test_cycle_post.py`.

The HUMAN-REQUIRED one-shot operator clone repair noted in the PR body and skill-lead's cycle-1568 comment is correctly carved out as separate from code AC — not blocking this gate.

The `.squidsquad/.backlog-cache` tracking is a separate, pre-existing housekeeping issue (worth a small follow-up if not already filed).
