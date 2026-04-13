# FEAT-SKILL-375 Context — Branch-Per-Feature Workflow

## Scope

Dev agents (skill, designer) work on feature branches for code changes. Communication files (.squidsquad/) stay on main. QA checks out branches to verify. PM auto-recomposes after merge. Enabled for software dev presets, not all project types.

## Locked Decisions (human decided)

- **Branching scope**: Software dev presets only. Non-dev presets (design, content, etc.) stay on main-only.
- **Who branches**: Dev roles (skill, designer) create feature branches. PM/DM/QA stay on main.
- **Branch naming**: `squidsquad/<role>/<issue-number>` (e.g., `squidsquad/skill/195`)
- **Commit split**: Code changes go on branch, .squidsquad/ state changes go on main. Agent makes two commits per cycle if needed.
- **QA verification**: QA checks out the feature branch to run tests and verify acceptance criteria.
- **Post-merge recompose**: PM detects merged branches and runs compose.py deploy for affected roles.
- **CLAUDE.md/SOUL.md**: Stay on main (state, not code). Recomposed after branch merge if templates changed.
- **Mandatory for dev presets**: No opt-in toggle. All software dev presets get branching.

## Dev Discretion (dev agent can choose)

- git_ops.py internal implementation (stash strategy, branch switch mechanics)
- Whether to use `git worktree` or `git checkout` for branch management
- How to handle merge conflicts between branch and main
- Order of git_ops.py command implementation

## Side Effect Mitigations (required)

- Test commit split thoroughly — wrong file on wrong branch = broken workflow
- QA branch checkout must not leave dirty working tree on main
- PM recompose must only run when merged branch touched references/
- Upgrade path: existing direct-to-main installs transition cleanly
- All agents must pull main before starting cycles (coordination files on main)

## Upgrade Path (required)

- New config: `Branch Workflow: yes` auto-set for software dev presets
- git_ops.py gains new commands (branch-create, commit-code, commit-state)
- Dev role git-commit sub-skill rewritten for branch workflow
- QA verification sub-skill updated for branch checkout
- PM gains post-merge recompose step
- Existing installs: upgrade sets Branch Workflow based on preset type

## Out of Scope

- PR-based review (#246) — branches can exist without PRs initially
- CI/GitHub Actions integration
- Non-dev role branching
- Branch protection rules
