# TEST-PLAN-10820 — Surface silent commit-role-scoped failures

**Source**: GitHub issue #10820 (symptom + likely-contributing-factors) and PR #10953 stated scope.
**Derived without reading the diff except where ACs are absent from the issue body and must be inferred from the "Suggested fixes" + skill-lead's cycle-1568 scope split.**

## ACs (derived)

The issue body lists "Suggested fixes" rather than numbered ACs. Skill-lead's cycle-1568 comment commits to two of them. Derived ACs:

- **AC-1**: DM/PM/other arm in `cycle_post._do_commit_push` pre-checks-out the working branch before calling `commit-role-scoped`, mirroring the QA arm's existing behavior at L548-549.
- **AC-2**: A post-call check re-reads `git status --porcelain` after `commit-role-scoped` and emits a loud stderr WARNING listing any role-owned files (per `git_ops._role_owned_patterns`) that remain `M`. Both arms (QA arm and DM/PM/other arm) carry the post-check.
- **AC-3**: Existing tests asserting `commit_role_scoped` returns `False` for empty-status / no-own-files cases still pass — the fix must not change the return-value contract.
- **AC-4 (regression test for AC-1)**: Test exercises the DM/PM/other arm starting on a task-branch with `working == main`, and asserts a `git checkout main` was invoked before `commit-role-scoped` runs.
- **AC-5 (regression test for AC-2)**: Test exercises `_warn_if_role_files_uncommitted` with three cases — (a) role-owned file still `M` → WARNING with that file name on stderr; (b) clean working tree → no WARNING; (c) `M` file that does NOT match the role's `_role_owned_patterns` → no WARNING.

Out-of-scope per skill-lead's cycle-1568 split (not part of this PR; not part of QA's gate for this PR):
- `commit_role_scoped` return-value contract refactor.
- `.claude/scheduled_tasks.lock` gitignore.
- `cycle_pre.py` pre-flight merge-state check.
- One-shot manual resolution of the stranded SKILL.md in operator's DM clone (HUMAN-REQUIRED, separate from code AC).

## Test Cases

### TC-1 (covers AC-1): DM/PM/other arm has the pre-checkout block
- **Steps**: grep for the pre-checkout block in the DM/PM/other arm and confirm it precedes the `commit-role-scoped` call.
- **Verification command**: `grep -n "current_branch != working\|git checkout.*working\|_get_working_branch" references/scripts/cycle_post.py`
- **Expected**: pre-checkout block exists in the `else` arm (DM/PM/other) of `_do_commit_push`, structurally mirroring QA arm.

### TC-2 (covers AC-2): `_warn_if_role_files_uncommitted` exists and is wired in both arms
- **Verification command**: `grep -n "_warn_if_role_files_uncommitted\|WARNING.*#10820" references/scripts/cycle_post.py`
- **Expected**: helper defined once, called once in QA arm, once in DM/PM/other arm; emits the WARNING (#10820) loud stderr line.

### TC-3 (covers AC-3): Existing combined suite passes
- **Verification command**: `python -m pytest tests/test_cycle_post.py tests/test_git_ops.py`
- **Expected**: 224 pass; the single failure is `.squidsquad/.backlog-cache` gitignore noise pre-existing on `main`.

### TC-4 (covers AC-4 — MISSING): Pre-checkout regression test
- **Verification command**: `grep -rn "test.*pre_checkout\|test.*dm.*checkout\|test.*working_branch.*checkout" tests/test_cycle_post.py`
- **Expected**: at least one test asserting the DM/PM/other arm checks out `working` when the current branch is a task branch.

### TC-5 (covers AC-5 — MISSING): WARNING helper regression tests
- **Verification command**: `grep -rn "_warn_if_role_files_uncommitted\|test.*warn.*role.*uncommitted\|test.*stranded.*files" tests/test_cycle_post.py`
- **Expected**: at least one test per scenario (a/b/c) covering the WARNING helper.

## Coverage matrix

- AC-1 → TC-1
- AC-2 → TC-2
- AC-3 → TC-3
- AC-4 → TC-4
- AC-5 → TC-5

## Comprehension Questions

Skipped — no LLM-consumed instructions touched. Pure-Python change to `cycle_post.py`.
