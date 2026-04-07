# Feature Branches — Current State & Gaps

**For human review on return**

## What Exists Today

PR Flow is partially implemented but **never enabled** (`PR Flow: no` in config.md):

### Code that exists:
- `git_ops.py`: `branch_create()`, `branch_switch()`, `pr_create()` — all functional
- `git-commit.md` sub-skill: has PR Flow branch with branch create → commit → PR → switch back to main
- `pm-specific/pr-flow.md`: PM monitors open PRs, detects merged/closed/comments
- `qa-specific/verification.md`: QA checks PR state
- Branch naming: `squidsquad/[type]-[role]-[issue#]` (e.g., `squidsquad/feat-skill-17`)

### What's missing / untested:
1. **Never been enabled** — the code exists but has 0 real-world testing
2. **Multi-agent branch conflicts** — if skill-lead and DM both work on branches, how do they coordinate? Currently all agents share `main`.
3. **Branch lifecycle** — who deletes branches after merge? No cleanup code exists.
4. **Base branch drift** — if a feature branch takes 3 cycles, main advances. Rebase strategy not defined.
5. **Planning artifacts on branches** — RESEARCH.md, CONTEXT.md, TEST-PLAN.md are created by PM on main. If skill-lead is on a feature branch, it won't see PM's latest planning artifacts unless it merges/rebases from main.
6. **Working state across branches** — working-state.md is on main. If agent switches to a branch, the working state needs to be on that branch too.
7. **Status bar on branches** — current-state file lives on main. Branch work won't update the main status bar.
8. **Vault writes on branches** — vault-remember runs at end of cycle. If on a feature branch, vault notes go to the branch, not main. Other agents won't see them until merge.

## The Core Question

**When should agents use feature branches vs direct push to main?**

### Option A: Feature branches for features, direct push for bugs
- Features get branches (longer-lived, reviewable)
- Bugs push to main (fast fixes, no branch overhead)
- PM verifies on the PR before merge
- This is what the existing git-commit.md sub-skill describes

### Option B: Everything on feature branches
- Maximum isolation and review
- But bugs become slower to ship (branch → PR → review → merge)
- Overhead for one-line fixes

### Option C: Feature branches only for multi-cycle work
- Single-cycle fixes/features push to main
- Multi-cycle features (spanning 2+ cycles) use branches to avoid partial work on main
- Most practical but harder to determine in advance

### Option D: Human-controlled per feature
- PM or human sets `branch: yes` on specific issues
- Agent checks the flag and branches accordingly
- Maximum flexibility but adds a decision point to every feature

## Problems to Solve

### 1. Agent coordination with branches
Currently all 3 agents (skill, pm, dm) share one clone each, all on `main`. With branches:
- Skill-lead switches to `squidsquad/feat-skill-17` to implement
- PM stays on `main` to run cycles and verify
- DM stays on `main` for delivery

This works IF only one agent branches at a time. If skill-lead has two features in flight, it needs to stash/switch between branches — complex.

### 2. Cross-branch visibility
- PM needs to see skill-lead's code to verify → PM reads the PR diff, not local files
- DM needs to see shipped features for delivery → waits for merge to main
- Vault writes on branches are invisible to other agents until merge

### 3. Branch cleanup
After merge:
```bash
git branch -d squidsquad/feat-skill-17
git push origin --delete squidsquad/feat-skill-17
```
Who does this? The agent that opened the PR? PM after verifying? A cleanup step?

### 4. Rebase strategy
Feature branch falls behind main:
```bash
git checkout squidsquad/feat-skill-17
git rebase main
git push --force-with-lease
```
When does this happen? Every cycle start? Only when conflicts arise?

## Recommendation

**Start with Option A** (features on branches, bugs on main) since the code already exists. Enable `PR Flow: yes` and test it on the marketplace project. The marketplace is the perfect testbed — it's a new repo with no legacy, and any issues found are bugs to fix in SquidSquad.

### Implementation steps:
1. Enable PR Flow on the marketplace repo during setup
2. Test the existing git-commit.md branch/PR code
3. File bugs back to SquidSquad for any gaps found
4. Add branch cleanup to PM's PR monitoring step
5. Add rebase-on-cycle-start logic to dev agent
6. Document the branch strategy in CONTRIBUTING.md

### What connects to this:
- #246 (PR-driven workflow + CI) — the full vision
- #250 (auto-restart) — agent restart must remember which branch it was on
- Phase E (marketplace) — test ground for feature branches
