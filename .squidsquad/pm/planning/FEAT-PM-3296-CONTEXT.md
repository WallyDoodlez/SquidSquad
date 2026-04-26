# FEAT-PM-3296 Context — Task-Level Branch Boundaries

## Scope
Add `task-begin` / `task-end` commands to `git_ops.py` as a mechanical task-level boundary for branch checkout. All agents use these per-task, not per-cycle.

## Locked Decisions (human decided)
- **All agents** use task-begin/task-end — full symmetry (skill, QA, DM, PM if applicable)
- **DM uses task-begin/task-end** — DM proactively updates documentation for every change. When technical docs exist, DM needs branch code to understand what changed. DM is a coding role for documentation purposes. Make this clear in DM instructions.
- **Missing branch = push back** — if task-begin can't find the branch, push back to the submitting agent (comment on issue). Don't test/ship without the branch. The agent that submitted work must push before transitioning to pending-test.
- **Task-level, not cycle-level** — a cycle may involve multiple tasks on different branches. Each task gets its own begin/end boundary.

## Dev Discretion (dev agent can choose)
- Exact error message wording for missing branch
- Whether to use exit code 1 or 2 for missing branch
- Implementation details of the push-back mechanism (comment on issue? transition back?)
- How to handle the resume-from-working-state path

## Side Effect Mitigations (required)
- Remove QA's first-item branch checkout hack from cycle_pre.py — must ship together with verification.md update
- Remove skill's cycle-level _setup_skill_branch from cycle_pre.py — replaced by per-task task-begin
- Keep cycle_post.py's "return to main" safety guard as belt-and-suspenders
- compose.py deploy-all after template changes

## Upgrade Path (required)
- Existing installs with branch-workflow: yes — gain correct per-task switching (improvement)
- Existing installs with branch-workflow: no — task-begin/task-end are no-ops, zero behavior change
- Recompose required after shipping

## Out of Scope
- Changes to branch naming convention (already correct: squidsquad/role/number)
- PR Flow changes
- Multi-repo coordination
