Now I have all the context I need. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/git_ops.py`
- **Line**: 1060 (docstring, unchanged in diff)
- **Severity**: warning
- **Issue**: The `guard_staged_state` docstring at line 1060 still claims state files are classified by `_is_state_file` ("the SAME classifier `commit_code` uses, so routing stays single-source"). After this change, the guard uses `_is_state_file(p) and not _is_plan_body(p)` — an additional exemption that diverges from what `commit_code` uses. The docstring is now out of date and misleading about single-source routing.
- **Evidence**: The diff adds the exemption at line 53 of the diff (`if _is_state_file(p) and not _is_plan_body(p)`) but makes no corresponding update to the docstring block spanning lines 1044–1070. A reader of the docstring would believe the guard still strips every `_is_state_file` match, missing the plan-body carve-out.
- **Suggested fix**: Add a sentence to the docstring noting the plan-body exemption, e.g. after line 1061: `With one narrow carve-out for plan bodies (#12750):``_is_plan_body`` paths are exempted so committed task plans ride the feature branch into the PR.`

---

### Finding 2

- **File**: `references/sub-skills/common/task-pickup.md`
- **Line**: 35 (new step 10 in the diff)
- **Severity**: warning
- **Issue**: Step 10 instructs the worker to flip the draft PR to ready using bare `gh pr ready [PR_NUMBER]` instead of the canonical `git_ops.py pr-ready`. This bypasses the forge-adapter layer (`pr_ready` in git_ops.py line 383–404 handles non-GitHub backends via `forge_adapter`) and the project's stated principle that direct `gh` CLI calls are non-canonical.
- **Evidence**: The same task-intake.md Phase 3B step 4 explicitly states: "`git_ops.py pr-create` is canonical; bare `gh pr create` is non-canonical and skips base-branch and body-shape coordination." The same reasoning applies to `pr-ready`. The `git_ops.py pr-ready` CLI command exists at line 1251 and wraps `gh pr ready` with forge-adapter fallback. Bare `gh pr ready` would fail silently on non-GitHub forges.
- **Suggested fix**: Change `gh pr ready [PR_NUMBER]` to `python references/scripts/git_ops.py pr-ready [PR_NUMBER]`.

---

### Finding 3

- **File**: `references/sub-skills/common/task-pickup.md`
- **Line**: 24 (new step 5 in the diff)
- **Severity**: warning
- **Issue**: Step 5 says "RESEARCH.md / CONTEXT.md inform it" — which is ambiguous about whether the worker should *read* those files. But under the plan-in-PR flow, RESEARCH.md and CONTEXT.md are NOT committed to the task branch (only the plan body is). A worker who interprets this as "I should read these files" will search for them on the task branch and not find them, causing confusion or wasted cycles.
- **Evidence**: The new task-intake.md Phase 3B commits only `.squidsquad/[PM_ALIAS]/planning/[NUMBER]-body.md` (step 3, lines 114–121 of the diff). RESEARCH.md / CONTEXT.md remain planning inputs on the working branch, not the task branch. The worker is on the task branch after `task-begin` and cannot access those files without switching branches. The old step 5 ("Read planning artifacts if available") was conditional and pointed to the planning directory broadly; the new step 5 tightens to a specific committed file but retains the ambiguous dangling reference.
- **Suggested fix**: Either drop the "RESEARCH.md / CONTEXT.md inform it" clause entirely (the plan body stands alone) or make it explicit that those are background/input artifacts and not needed by the worker, e.g.: "…is the source of truth for the spec. (RESEARCH.md / CONTEXT.md were planning inputs that informed this plan; you do not need to locate them.)"

---

### Finding 4

- **File**: `tests/test_12750_plan_in_pr_guard.py`
- **Line**: 277–278
- **Severity**: warning
- **Issue**: The `test_on_working_branch_is_noop` test patches `_run` with `fake_run` that unconditionally returns `"main\n"` for ANY `_run` call without inspecting `cmd`. If `guard_staged_state` ever called `_run` for a different command (e.g., a diagnostic or future refactor), the test would silently pass with wrong data rather than failing. The test relies on implicit knowledge that only one `_run` call exists in the guard.
- **Evidence**: `fake_run(cmd, check=True)` at line 277 completely ignores `cmd` and always returns `_mock_result(stdout="main\n")`. The test's correctness depends on `guard_staged_state` calling `_run` exactly once with `"git branch --show-current"`. If another `_run` call were added (or the existing one changed command), the test would not catch the divergence — it would either still pass by coincidence or fail confusingly.
- **Suggested fix**: Make `fake_run` inspect `cmd` and only return `"main\n"` when `cmd == "git branch --show-current"`, raising an error or returning a distinguishable failure value otherwise. This makes the mock self-documenting about what `_run` calls are expected.

---

### Finding 5

- **File**: `references/sub-skills/roles/pm/task-intake.md`
- **Line**: 100–101 (new Phase 3B steps 1–2 in the diff)
- **Severity**: error
- **Issue**: The instruction order is **write plan file → create task branch → commit**. But the plan file is written while on the working branch (step 1), then `task-begin` creates the task branch from `origin/main` (step 2). The plan file survives as an untracked file carried through the checkout. However, if the plan file path already exists as a *tracked* file on `origin/main` (e.g., from a previously merged PR for the same issue number), `git checkout -b squidsquad/task/12750 origin/main` would overwrite the locally-written plan file with the version from `origin/main` — silently discarding the PM's newly-authored content before it can be committed.
- **Evidence**: `task_begin` at line 931–932 creates the branch from `origin/<working>` (`git checkout -b <branch> origin/<working>`). If `.squidsquad/pm/planning/12750-body.md` is tracked on `origin/main` (because a prior PR with the same issue number was merged), the checkout replaces the working-tree file with the tracked version. The PM's newly-written plan is lost before `git add` + `git commit` in step 3. The old Phase 3B didn't have this problem because it created the branch first, then wrote files on the branch.
- **Suggested fix**: Swap steps 1 and 2: create the task branch FIRST, then write the plan file on the task branch. Alternatively, add a safety note: "If the branch already exists or the file is tracked on main, verify the file content after checkout before committing."