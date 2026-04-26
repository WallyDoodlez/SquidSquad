# FEAT-PM-3296 Test Plan — Task-Level Branch Boundaries

## Test Cases

### TC-1: task-begin checks out existing branch
- **Precondition**: Branch `squidsquad/skill/9999` exists on origin
- **Steps**: Run `python references/scripts/git_ops.py task-begin skill 9999`
- **Expected**: Agent is on branch `squidsquad/skill/9999`
- **Verification**: `git branch --show-current` returns `squidsquad/skill/9999`

### TC-2: task-end returns to main
- **Precondition**: Agent is on branch `squidsquad/skill/9999`
- **Steps**: Run `python references/scripts/git_ops.py task-end skill 9999`
- **Expected**: Agent is back on main
- **Verification**: `git branch --show-current` returns `main`

### TC-3: task-begin with missing branch pushes back
- **Precondition**: No branch `squidsquad/skill/8888` exists locally or on origin
- **Steps**: Run `python references/scripts/git_ops.py task-begin skill 8888`
- **Expected**: Non-zero exit code, clear error message about missing branch, stays on current branch
- **Verification**: Exit code != 0, agent still on main

### TC-4: task-begin is no-op when branch-workflow disabled
- **Precondition**: `branch-workflow: no` in config.md
- **Steps**: Run `python references/scripts/git_ops.py task-begin skill 9999`
- **Expected**: No branch switch, exits 0 silently
- **Verification**: Agent stays on main, exit code 0

### TC-5: Multiple tasks in one cycle (sequential boundaries)
- **Precondition**: Branches exist for items A, B, C
- **Steps**: task-begin A → work → task-end A → task-begin B → work → task-end B → task-begin C → work → task-end C
- **Expected**: Each task runs on its own branch, returns to main between tasks
- **Verification**: Verify branch at each step

### TC-6: QA verification.md uses task-begin/task-end
- **Precondition**: Updated verification.md template
- **Steps**: grep for `task-begin` and `task-end` in verification.md
- **Expected**: Per-item task-begin/task-end calls in Steps 4 and 5
- **Verification**: Pattern exists, no residual `branch-switch` calls

### TC-7: cycle_pre.py first-item hack removed
- **Precondition**: Updated cycle_pre.py
- **Steps**: grep for first-item branch checkout in _build_qa_input
- **Expected**: No pre-checkout of first queue item's branch
- **Verification**: No branch-switch calls in _build_qa_input

### TC-8: Skill uses task-begin/task-end (symmetry)
- **Precondition**: Updated skill templates
- **Steps**: Check skill's branch management uses task-begin/task-end
- **Expected**: _setup_skill_branch replaced or augmented with task-begin
- **Verification**: Skill template references task-begin

### TC-9: DM uses task-begin/task-end for doc updates
- **Precondition**: Updated DM templates with coding preset
- **Steps**: Check DM delivery sub-skill for task-begin/task-end
- **Expected**: DM checks out branch before inspecting code for doc updates
- **Verification**: DM template references task-begin

### TC-10: Full test suite passes
- **Steps**: `python tests/run_tests.py`
- **Expected**: No regressions
- **Verification**: Same or better pass rate

## Smoke Tests
- [ ] task-begin/task-end work in bash
- [ ] Branch switches correctly between tasks
- [ ] Returns to main after task-end
- [ ] No-op when branch workflow disabled

## Regression Risks
- QA cycle_pre cleanup must ship with verification.md update (atomic)
- Skill _setup_skill_branch removal must ship with task-begin adoption
- Resume-from-working-state must call task-begin for the resumed task

## Comprehension Questions
### CQ-1: When should an agent call task-begin?
- **Files**: verification.md, delivery-packaging.md
- **Expected**: Before starting work on any specific task/issue item

### CQ-2: What happens if task-begin can't find the branch?
- **Files**: git_ops.py
- **Expected**: Non-zero exit, push back to submitting agent, don't test without the branch
