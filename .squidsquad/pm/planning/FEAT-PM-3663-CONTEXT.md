# FEAT-PM-3663 Context — Dev agent PR conflict resolution each cycle

## Scope

Add a cycle step for dev agents to check their open PRs for merge conflicts and rebase automatically when PR Flow is enabled.

## Locked Decisions

- **Where**: Add to git-commit sub-skill (common/git-commit.md) as a pre-commit step, or as a new step in the cycle runner. Runs before implementing new work — stale PRs get fixed first.
- **Only own PRs**: Agent only checks branches matching `squidsquad/<own-role>/*`. Never touches other agents' branches.
- **Only when PR Flow on**: Check `python references/scripts/config.py get pr-flow` first. Skip entirely if off.
- **Rebase + force-push**: `git fetch origin main && git rebase origin/main && git push --force-with-lease`. Not merge — rebase keeps history clean.
- **Log it**: Note in iteration summary: "Rebased PR #NNNN (squidsquad/role/NNN) — conflict resolved."

## Dev Discretion

- Exact placement in the cycle (before implement-tasks vs inside git-commit)
- How to handle rebase failures (e.g., code conflict that needs manual resolution — comment on PR and skip)
- Whether to use `gh pr list` or `git branch -r` to find own PRs

## Out of Scope

- Rebasing other agents' PRs (PM does this via pipeline sentinel if needed)
- Creating PRs (already handled by git-commit sub-skill)
- Auto-merge logic (that's #3645)
