# FEAT-PM-5040 Test Plan — Unified Branch Model

## Test Cases

---

### TC-1: Config field present — factory reads correct pattern
- **Precondition**: `config.md` has `## Git Branches` section with `- **Branch Pattern**: squidsquad/task/{number}`
- **Steps**: Call `python references/scripts/config.py get branch-pattern`
- **Expected**: Returns `squidsquad/task/{number}`
- **Verification**: `python references/scripts/config.py get branch-pattern` prints `squidsquad/task/{number}` and exits 0

---

### TC-2: Config field absent — factory falls back to default
- **Precondition**: `config.md` does NOT contain a `Branch Pattern` entry under `## Git Branches`
- **Steps**: Call `python references/scripts/config.py get branch-pattern`
- **Expected**: Returns default `squidsquad/{role}/{number}` (backward-compatible fallback)
- **Verification**: Script exits 0; returned value matches the default pattern; no crash or empty string

---

### TC-3: `_get_branch_name` factory produces correct branch name with task pattern
- **Precondition**: `config.md` has `Branch Pattern: squidsquad/task/{number}`
- **Steps**: Invoke the factory function internally (or via a test that calls it) with `role="skill"`, `number=100`
- **Expected**: Returns `squidsquad/task/100`
- **Verification**: `tests/test_git_ops.py` — assert `_get_branch_name("skill", 100) == "squidsquad/task/100"`

---

### TC-4: `_get_branch_name` factory produces correct branch name with legacy pattern
- **Precondition**: `config.md` has `Branch Pattern: squidsquad/{role}/{number}` (default)
- **Steps**: Invoke factory with `role="skill"`, `number=100`
- **Expected**: Returns `squidsquad/skill/100`
- **Verification**: `tests/test_git_ops.py` — assert `_get_branch_name("skill", 100) == "squidsquad/skill/100"`

---

### TC-5: `task-begin` creates branch and prints branch name to stdout
- **Precondition**: Clean repo, `config.md` has `Branch Pattern: squidsquad/task/{number}`, issue `#200` exists
- **Steps**: Run `python references/scripts/git_ops.py task-begin skill 200`
- **Expected**: Branch `squidsquad/task/200` is created and checked out; the branch name is printed on stdout (e.g., `squidsquad/task/200`)
- **Verification**: `git branch --show-current` returns `squidsquad/task/200`; captured stdout contains `squidsquad/task/200`

---

### TC-6: Agent captures `task-begin` output and uses it for `commit-code`
- **Precondition**: `task-begin` prints branch name to stdout; agent template instructs capturing the output
- **Steps**: Simulate agent flow — capture `task-begin` output, pass it as `BRANCH` to `commit-code`
- **Expected**: `commit-code` receives `squidsquad/task/200`; commit lands on correct branch
- **Verification**: `git log squidsquad/task/200 --oneline -1` shows the agent commit; no commit on an old-pattern branch

---

### TC-7: `task-begin` checks out existing shared branch (second agent)
- **Precondition**: `squidsquad/task/200` already exists (PM created it); QA now calls `task-begin qa 200`
- **Steps**: Run `python references/scripts/git_ops.py task-begin qa 200`
- **Expected**: Existing branch is checked out (not re-created); no error; stdout prints `squidsquad/task/200`
- **Verification**: `git branch --show-current` returns `squidsquad/task/200`; branch history preserved from PM's earlier commit

---

### TC-8: All 4 construction sites use the factory — no hardcoded strings remain
- **Precondition**: Feature is implemented
- **Steps**: Search codebase for hardcoded branch construction patterns
- **Expected**: No raw `f"squidsquad/{role}/{number}"` string literals in `git_ops.py`, `cycle_pre.py` construction sites
- **Verification**: `grep -rn 'squidsquad.*{role}' references/scripts/` returns 0 results in construction contexts; all 4 sites call `_get_branch_name()`

---

### TC-9: `cycle_pre.py` QA input constructs branch via factory (lines 609/632)
- **Precondition**: `config.md` has `Branch Pattern: squidsquad/task/{number}`; pending-test items exist for issue `#300`
- **Steps**: Run `cycle_pre.py qa`; inspect `cycle-input.json` for the branch field of the pending-test item
- **Expected**: Branch field reads `squidsquad/task/300`, not `squidsquad/qa/300`
- **Verification**: `cat .squidsquad/qa/cycle-input.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['verification_queue'][0]['branch'])"` returns `squidsquad/task/300`

---

### TC-10: Parsing sites use `parts[-1]` for issue number — old-pattern branches still parse
- **Precondition**: Old-pattern branch `squidsquad/skill/100` exists in the repo (open PR, unmerged)
- **Steps**: Run tracker operations that parse branch names (e.g., `tracker.py` `_check_unmerged_branch`, `_check_unmerged_pr`, `_convert_draft_pr_to_ready`)
- **Expected**: Issue number `100` is correctly extracted from `squidsquad/skill/100` using `parts[-1]`; no KeyError or wrong-number extraction
- **Verification**: `python references/scripts/tracker.py get-state 100` returns correct state without crash; unit tests in `tests/test_feat_1074_auto_merge.py` pass with both branch patterns

---

### TC-11: Parsing sites use `parts[-1]` for issue number — new-pattern branches parse correctly
- **Precondition**: New-pattern branch `squidsquad/task/100` exists
- **Steps**: Run tracker parsing operations against `squidsquad/task/100`
- **Expected**: Issue number `100` correctly extracted; no regression vs. old pattern
- **Verification**: Unit tests assert `parts[-1] == "100"` for both `squidsquad/skill/100` and `squidsquad/task/100`

---

### TC-12: PR search wildcard matches new branch pattern
- **Precondition**: PR exists on `squidsquad/task/400`; `tracker.py` searches with `squidsquad/*/400`
- **Steps**: Call PR search functions in `tracker.py` for issue `#400`
- **Expected**: PR is found; no "PR not found" error
- **Verification**: `gh pr list --search "squidsquad/" --state open --json headRefName` shows `squidsquad/task/400`; tracker functions return the PR number

---

### TC-13: PR search wildcard also matches old-pattern branches during cutover
- **Precondition**: Pre-existing PR on `squidsquad/skill/400` (filed before cutover)
- **Steps**: Run tracker PR search for issue `#400`
- **Expected**: Old-pattern PR is still found (wildcard `squidsquad/*/400` matches both)
- **Verification**: `gh pr list --search "squidsquad/" --json headRefName` includes `squidsquad/skill/400`; tracker functions return correct PR number

---

### TC-14: `commit-code` with explicit branch argument uses the captured branch name
- **Precondition**: `task-begin` printed `squidsquad/task/500`; agent stored it; now calls `commit-code`
- **Steps**: Run `python references/scripts/git_ops.py commit-code skill squidsquad/task/500 "skill: #500 — implement feature"`
- **Expected**: Commit lands on `squidsquad/task/500`; no error; commit message correct
- **Verification**: `git log squidsquad/task/500 --oneline -1` shows the commit message

---

### TC-15: `cycle_post.py` PR creation uses branch from cycle-output `code_commit.branch`
- **Precondition**: `cycle-output.json` has `code_commit.branch = "squidsquad/task/500"`; branch exists and has commits
- **Steps**: Run `python references/scripts/cycle_post.py skill`
- **Expected**: PR created targeting `squidsquad/task/500`; PR URL returned; no error about wrong branch
- **Verification**: `gh pr list --head squidsquad/task/500 --json number` returns a PR number

---

### TC-16: Status bar shows current branch for PM role (L2 instruction)
- **Precondition**: PM agent running; currently on branch `squidsquad/task/600`
- **Steps**: Observe PM status bar or `current-state` file during an active cycle
- **Expected**: Status bar displays the current branch name (e.g., `squidsquad/task/600`)
- **Verification**: `cat .squidsquad/pm/current-state` contains `squidsquad/task/600` or equivalent branch display

---

### TC-17: Status bar shows current branch for QA and dev roles (L2 instruction)
- **Precondition**: QA and dev (skill) agents running; each on `squidsquad/task/600`
- **Steps**: Observe each role's `current-state` file
- **Expected**: All agents' status bars display the branch
- **Verification**: `cat .squidsquad/qa/current-state` and `cat .squidsquad/skill/current-state` each contain branch info

---

### TC-18: PM creates branch with PRD; dev continues on the same branch
- **Precondition**: `config.md` has `Branch Pattern: squidsquad/task/{number}`; issue `#700` exists
- **Steps**:
  1. PM calls `task-begin pm 700` → branch `squidsquad/task/700` created; PM commits PRD/planning artifacts
  2. Dev (skill) calls `task-begin skill 700` → should check out existing `squidsquad/task/700`
  3. Dev makes code commit on the same branch
- **Expected**: Both commits (PM's PRD, dev's code) appear on `squidsquad/task/700`; single branch, single PR
- **Verification**: `git log squidsquad/task/700 --oneline` shows both PM and dev commits

---

### TC-19: QA verifies on same shared branch (reads dev's code from the branch)
- **Precondition**: `squidsquad/task/700` has PM's PRD commit and dev's code commit
- **Steps**: QA calls `task-begin qa 700` → checks out `squidsquad/task/700`; runs verification
- **Expected**: QA is on `squidsquad/task/700` and sees all prior commits; QA does NOT make code commits; verification succeeds
- **Verification**: `git branch --show-current` in QA clone returns `squidsquad/task/700`; `git log` shows all prior commits

---

### TC-20: Single PR merges the unified branch — cleanup works correctly
- **Precondition**: `squidsquad/task/700` PR open; PM, dev, QA all committed there
- **Steps**: Run `python references/scripts/git_ops.py pr-merge [PR_NUMBER]` (with `--delete-branch`)
- **Expected**: Branch merged to main; branch deleted; all commits (PM + dev) land on main; tracker item transitions correctly
- **Verification**: `git branch -r | grep squidsquad/task/700` returns nothing after merge; `git log main --oneline -5` shows PRD and code commits

---

### TC-21: Multi-agent same branch — no commit conflicts
- **Precondition**: PM and skill agents both have `squidsquad/task/800` checked out in their respective clones
- **Steps**: PM commits planning artifact; skill pulls, then commits code change
- **Expected**: No merge conflict; skill's `git pull --rebase` succeeds; sequential commits both present
- **Verification**: `git log squidsquad/task/800 --oneline` shows both commits in order

---

### TC-22: `task-end` works correctly with unified branch
- **Precondition**: Agent on `squidsquad/task/900` after completing work
- **Steps**: Run `python references/scripts/git_ops.py task-end skill 900`
- **Expected**: Agent returns to `main` (or configured base branch); no error
- **Verification**: `git branch --show-current` returns `main`

---

### TC-23: Agent instructions contain no hardcoded `squidsquad/<role>/<number>` patterns
- **Precondition**: Feature implemented and templates recomposed
- **Steps**: Search template and instruction files for hardcoded branch patterns
- **Expected**: No literal `squidsquad/skill/`, `squidsquad/qa/`, `squidsquad/pm/` in sub-skill or agent-instructions templates; references instead say "use task-begin output" or "configured branch pattern"
- **Verification**: `grep -rn 'squidsquad/skill/\|squidsquad/qa/\|squidsquad/pm/' references/` returns 0 results; `grep -rn 'squidsquad/skill/\|squidsquad/qa/\|squidsquad/pm/' .squidsquad/*/CLAUDE.md` returns 0 results

---

### TC-24: L4 project override sets pattern to `squidsquad/task/{number}`
- **Precondition**: `.squidsquad/config.md` has the `branch-pattern` field set to `squidsquad/task/{number}` at the project level
- **Steps**: Run `python references/scripts/config.py get branch-pattern` from the project directory
- **Expected**: Returns `squidsquad/task/{number}` (L4 override active)
- **Verification**: Output matches `squidsquad/task/{number}`; not the default `squidsquad/{role}/{number}`

---

### TC-25: `tracker.py` `_check_unmerged_branch` wildcard glob matches new pattern
- **Precondition**: Branch `squidsquad/task/1000` exists and is unmerged
- **Steps**: Invoke the unmerged-branch check in `tracker.py` for issue `#1000`
- **Expected**: Branch detected as unmerged; no "branch not found" false negative
- **Verification**: Unit test asserts `_check_unmerged_branch(1000)` returns truthy when `squidsquad/task/1000` exists unmerged

---

### TC-26: `agent-instructions.md` PR conflict rebase section uses config-driven pattern
- **Precondition**: Templates recomposed after feature implemented
- **Steps**: Read deployed `.squidsquad/skill/CLAUDE.md` (or `agent-instructions.md`); find PR conflict rebase instructions
- **Expected**: Rebase section instructs agents to find own PRs by author, not by role-encoded branch prefix
- **Verification**: `grep -A5 "rebase" .squidsquad/skill/CLAUDE.md` shows author-based PR ownership check, not `squidsquad/[ROLE]/` hardcoded prefix

---

### TC-27: All 5 test files pass after update
- **Precondition**: Implementation complete
- **Steps**: Run `python tests/run_tests.py`
- **Expected**: All tests pass; no failures in `test_git_ops.py`, `test_cycle_post.py`, `test_cycle_pre.py`, `test_feat_3296_task_boundary.py`, `test_feat_1074_auto_merge.py`
- **Verification**: Exit code 0; test output shows all tests passing

---

## Smoke Tests

- [ ] `python references/scripts/config.py get branch-pattern` returns a non-empty string
- [ ] `python references/scripts/git_ops.py task-begin skill 9999` creates branch `squidsquad/task/9999` and prints it (with task pattern active); cleanup: delete the branch
- [ ] `git branch --show-current` after `task-begin` returns the expected pattern-driven name
- [ ] `python tests/run_tests.py` exits 0 with no failures
- [ ] `grep -rn 'squidsquad/{role}' references/scripts/git_ops.py` returns 0 results (factory used everywhere)
- [ ] `cat .squidsquad/pm/current-state` contains a branch name during an active PM cycle

---

## Regression Risks

- **PR search false negatives**: Any site that constructs a branch search string using the hardcoded role name (rather than `squidsquad/*/NUMBER`) will fail to find new-pattern branches. All PR/branch searches must use the wildcard form.
- **`cycle_post.py` PR creation**: If `code_commit.branch` in `cycle-output.json` is constructed by an agent using old template instructions (not from `task-begin` output), the PR will target a non-existent branch. Templates must be fully recomposed before any agent runs post-cutover.
- **QA clone branch discovery**: QA's clone must `git fetch` before `task-begin` to see branches created in other clones. If `cycle_pre.py` skips the fetch, QA will not find the shared branch.
- **`commit-code` branch mismatch**: If an agent constructs the branch name independently (ignoring `task-begin` output) while the factory returns a different name, commits land on a wrong or non-existent branch. All agent instructions must be updated to capture `task-begin` stdout.
- **Old PRs during cutover**: PRs on `squidsquad/<role>/<number>` branches must be merged or closed before the project pattern is changed, otherwise the branch name in `code_commit.branch` will diverge from what the PR tracks.
- **`parts[2]` regressions**: Any code that was not migrated from `parts[2]` to `parts[-1]` will silently return the wrong segment for new-pattern branches (since `parts[2]` is the issue number for both 3-segment patterns, this may not immediately break — but it will break if the pattern ever gains more segments). Verify all 21 parsing sites.

---

## Comprehension Questions

These questions must be answerable by a fresh agent given only the modified files (`git_ops.py`, `config.md`, `config.py`, `cycle_pre.py`, `agent-instructions.md`, sub-skill templates). The agent may not use prior knowledge of the old pattern.

### CQ-1: What is the branch name for issue #42 with the default config?
- **Files**: `references/scripts/config.py`, `references/scripts/git_ops.py`, `.squidsquad/config.md`
- **Expected**: Agent reads `config.md`, finds `Branch Pattern: squidsquad/{role}/{number}` (default), substitutes `role` and `number`, and answers `squidsquad/<role>/42` (where role is the calling agent's role). If this project's config overrides to `squidsquad/task/{number}`, answer is `squidsquad/task/42`.

### CQ-2: How does an agent find out the branch name it should use for a task?
- **Files**: updated `agent-instructions.md` or relevant sub-skill template
- **Expected**: Agent answers "call `task-begin <role> <number>` and capture the branch name from its stdout output; do not construct the branch name manually."

### CQ-3: How is the issue number extracted from a branch name?
- **Files**: `references/scripts/git_ops.py`, `references/scripts/tracker.py`
- **Expected**: Agent answers "split the branch name by `/` and take the last segment (`parts[-1]`); this is the issue number regardless of whether the branch follows the old pattern (`squidsquad/role/number`) or the new pattern (`squidsquad/task/number`)."

### CQ-4: What happens when a second agent calls `task-begin` for an issue that already has a branch?
- **Files**: `references/scripts/git_ops.py`
- **Expected**: Agent answers "the existing branch is checked out (not re-created); `task-begin` is idempotent for shared branches; the branch name is still printed to stdout."

### CQ-5: Where is the `branch-pattern` config field defined and how is it read by scripts?
- **Files**: `references/scripts/config.py`, `.squidsquad/config.md`
- **Expected**: Agent identifies the `FIELD_MAP` entry `"branch-pattern": ("Git Branches", "Branch Pattern")` in `config.py` and the corresponding markdown field in `config.md`; explains that `config.py get branch-pattern` reads and returns it.

### CQ-6: Should agent instruction templates reference the raw branch pattern string (e.g., `squidsquad/task/{number}`)?
- **Files**: updated `agent-instructions.md`, sub-skill templates
- **Expected**: Agent answers "no — templates must not hardcode the branch pattern; they must instruct agents to call `task-begin` and use its output, so that pattern changes require no template updates."
