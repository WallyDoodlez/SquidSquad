# FEAT-SKILL-375 Research -- Branch-Per-Feature Workflow

## Summary

Currently all SquidSquad agents push directly to main on every cycle. The `commit-push` command in `git_ops.py` runs `git add -A && git commit && git push` against whatever branch is checked out (always main). This causes merge conflicts between concurrent agents, lands untested code on main, and provides no review gate.

The proposal: dev agents work on feature branches for code changes, while `.squidsquad/` coordination files stay on main so all agents can see each other's state. An existing PR Flow mechanism (`config.md: PR Flow: Enabled: no`) and `git-commit.md` sub-skill already define branch creation and PR creation for the "PR Flow enabled" path, but it is currently disabled by default and treats the entire commit as branch-worthy (no split between code and state files).

This research analyzes each dimension of implementing a mandatory branch-per-feature workflow with the code-on-branches / communication-on-main split.

**Recommendation**: Feasible with significant caveats. The git_ops.py primitives exist. The hard problem is the commit split -- agents currently do `git add -A` which stages everything. Splitting code vs state into separate commits on separate branches within one cycle requires new git_ops.py commands and a rewrite of the git-commit sub-skill for all roles.

---

## 1. Current Git Workflow

### 1.1 How agents commit today

Every agent uses the same path (from `references/sub-skills/common/git-commit.md`):

**Default (PR Flow: no)**:
```bash
python references/scripts/git_ops.py commit-push [ROLE] "[description]"
```

This calls `add_all()` -> `commit()` -> `push()`:
- `add_all()` runs `git add -A` (stages ALL changes -- code, state, tracker, config)
- `commit()` creates a commit with `[ROLE]: [message]` prefix
- `push()` runs `git push` to the current branch (always main)

**PR Flow (when enabled)**:
```bash
python references/scripts/git_ops.py branch-create squidsquad/[type]-[ROLE]-[NNN]
python references/scripts/git_ops.py commit-push [ROLE] "[description]"
python references/scripts/git_ops.py pr-create "[title]" "[body]"
python references/scripts/git_ops.py branch-switch main
```

This creates a branch, commits ALL changes to it, opens a PR, and switches back to main.

### 1.2 Role-specific git-commit sub-skills

Each role has its own git-commit sub-skill but they all follow the same pattern:
- `common/git-commit.md` -- dev agents (skill), the only one with PR Flow branching logic
- `pm-specific/git-commit.md` -- PM: always `commit-push pm "[msg]"` to main
- `dm-specific/git-commit.md` -- DM: always `commit-push dm "[msg]"` to main
- `designer-specific/git-commit.md` -- Designer: always `commit-push designer "[msg]"` to main
- `qa-specific/git-commit.md` -- QA: always `commit-push qa "[msg]"` to main

Only the common (dev) git-commit sub-skill has any branch awareness. PM, DM, QA, and Designer always push directly to main.

### 1.3 git_ops.py capabilities

The script already has:
- `branch-create <name>` -- `git checkout -b <name>`
- `branch-switch <name>` -- `git checkout <name>`
- `commit-push <role> <msg>` -- add-all + commit + push
- `pr-create <title> <body>` -- `gh pr create`
- `pull` -- `git pull --rebase` with stash/pop fallback
- `has-changes` -- checks working tree status

Missing:
- No selective staging (only `git add -A`)
- No branch deletion
- No branch existence check
- No "push to specific branch" (always pushes current)
- No cross-branch cherry-pick or merge
- No way to commit `.squidsquad/` files separately from code files

---

## 2. What Goes on Branches vs Main

### 2.1 Branch content (code changes)

Files that represent deliverable work product:
- `references/scripts/*.py` -- tooling scripts
- `references/sub-skills/**/*.md` -- agent instruction sub-skills
- `references/roles/**/*` -- role templates, manifests, SOULs
- `references/presets/**/*` -- preset configurations
- `references/vault-templates/**/*` -- vault templates
- `tests/**/*` -- test files
- `SKILL.md` -- skill manifest (user-facing)
- `README.md` -- project documentation
- `CHANGELOG.md` -- version history
- `CLAUDE.md` (root) -- auto-boot instructions

### 2.2 Main content (coordination/state)

Files that agents need to see in real-time for coordination:
- `.squidsquad/*/working-state.md` -- what each agent is doing right now
- `.squidsquad/*/current-state` -- status bar state (mtime-based health)
- `.squidsquad/*/iterations/iter-*.md` -- cycle logs
- `.squidsquad/*/planning/*.md` -- planning artifacts (RESEARCH, CONTEXT, TEST-PLAN)
- `.squidsquad/*/scan-history.md` -- improvement scan history
- `.squidsquad/config.md` -- shared configuration
- `.squidsquad/vault/**/*` -- shared knowledge vault
- `.squidsquad/diagnostics/**/*` -- diagnostic logs
- `.squidsquad/*.txt` -- hints files
- `.squidsquad/start-*.sh`, `.squidsquad/start-*.ps1` -- boot scripts

### 2.3 Gray areas

- `.squidsquad/*/CLAUDE.md` -- composed agent instructions. These are generated from `references/` templates by `compose.py`. They change when `references/` changes. If code is on a branch, the composed output should also be on the branch (it is derived from branch content). But agents READ their CLAUDE.md from `.squidsquad/` on main.
- `.squidsquad/*/SOUL.md` -- copied from `references/roles/*/SOUL.md` during deploy. Same issue.
- `.squidsquad/templates/` -- copied from references during deploy.

**This is the fundamental tension**: agents' instructions live in `.squidsquad/` (main), but are generated from `references/` (branch). If a dev agent changes a template on a branch, the composed CLAUDE.md on main is stale until merge.

---

## 3. The Commit Split Problem

### 3.1 Current cycle produces mixed changes

A typical dev agent cycle touches:
1. Code files (the actual implementation)
2. `.squidsquad/skill/working-state.md` (updated during implementation)
3. `.squidsquad/skill/current-state` (status bar updates)
4. `.squidsquad/skill/iterations/iter-N.md` (cycle log)
5. `.squidsquad/vault/**` (vault remember writes)
6. `.squidsquad/config.md` (counter increments)

Currently `git add -A` stages all of this into one commit. Splitting requires:

### 3.2 Proposed split workflow

```
1. git checkout squidsquad/skill/NNN          # switch to feature branch
2. git add references/ tests/ SKILL.md ...     # stage only code files
3. git commit -m "skill: implement #NNN"       # commit code to branch
4. git push origin squidsquad/skill/NNN        # push branch
5. git checkout main                            # switch back to main
6. git add .squidsquad/                         # stage only state files
7. git commit -m "skill: state update #NNN"    # commit state to main
8. git push origin main                         # push main
```

### 3.3 New git_ops.py commands needed

```python
def add_paths(paths):
    """Stage specific paths instead of -A."""
    _run_list(["git", "add"] + paths)

def commit_code_to_branch(role, branch, message):
    """Switch to branch, stage code files, commit, push, switch back."""
    branch_switch(branch)
    add_paths(CODE_PATHS)  # references/, tests/, SKILL.md, etc.
    commit(role, message)
    push()
    branch_switch("main")

def commit_state_to_main(role, message):
    """Stage .squidsquad/ files and commit to main."""
    # Must already be on main
    add_paths([".squidsquad/"])
    commit(role, message)
    push()
```

### 3.4 Risk: uncommitted changes across branch switches

`git checkout` will refuse to switch branches if there are uncommitted changes that conflict. The stash/pop pattern in `pull()` partially addresses this, but switching between a feature branch and main with mixed dirty state is error-prone.

**Mitigation**: Stage and commit code first (on branch), then switch to main with only state files dirty. State files are in `.squidsquad/` which is unlikely to conflict across branches (it is on main in both).

---

## 4. Branch Naming

### 4.1 Proposed convention

```
squidsquad/<type>-<ROLE>-<NNN>
```

Examples:
- `squidsquad/feat-skill-375`
- `squidsquad/bug-skill-335`
- `squidsquad/feat-designer-401`

This matches the existing PR Flow convention in `git-commit.md`:
```
python references/scripts/git_ops.py branch-create squidsquad/[type]-[ROLE]-[NNN]
```

### 4.2 Tracker interaction

The branch name encodes the issue number, making it traceable. When an agent picks up issue #375:
1. Create branch `squidsquad/feat-skill-375`
2. All code commits go to this branch
3. PR title references `#375`
4. Tracker Discussion gets the PR URL
5. On merge, PR auto-closes the issue (if configured) or PM transitions status

### 4.3 Multiple issues on one branch?

One branch per issue keeps things clean. If an agent works on #375 this cycle and #376 next cycle, they create separate branches. This avoids coupling unrelated changes.

---

## 5. Merge Strategy

### 5.1 Options

| Strategy | Who merges | Gate | Pros | Cons |
|----------|-----------|------|------|------|
| A. Human review | Human | Manual PR review | Full control, catches bad code | Blocks agent velocity, human bottleneck |
| B. PM after QA | PM | QA verifies, PM merges | Automated, QA gate present | PM must have merge authority, adds cycle latency |
| C. Auto-merge after tests | CI/GitHub | Tests pass + QA approval label | Fastest, no bottleneck | Requires CI setup, less human oversight |
| D. QA merges | QA | QA verifies and merges | Clean ownership | Requires new QA authority |

### 5.2 Recommendation

**Option B with human override**: PM merges after QA marks `pending-ship`. This aligns with the existing status flow: `pending-test` -> QA verifies -> `pending-ship` -> PM/DM ships. The "ship" step now includes merging the PR.

For speed, auto-merge could be enabled for issues with `priority:low` (improvement scan items) while requiring human review for `priority:high` and `priority:medium`.

### 5.3 Interaction with PR Flow (#246)

The existing PR Flow mechanism is an opt-in config toggle. #375 would make it the default (or only) mode for code changes. The PR Flow config field could be:
- `no` -- current behavior, everything on main (backward compatible)
- `yes` -- branch-per-feature for code, state on main (the new default)

The existing `Step 6b -- Monitor PRs` in PM's loop already handles PR state tracking. QA's verification step would also need to check out the PR branch to test against it.

---

## 6. Multi-Agent Coordination

### 6.1 Scenario: skill on branch, DM needs README on main

DM updates `README.md` on main. Skill has a branch `squidsquad/feat-skill-375` that also modifies `README.md`. When skill's PR is merged, there is a merge conflict.

**Mitigations**:
- DM should not modify files that are actively being worked on by dev agents. The tracker shows which issues are `in-progress` and which files they touch (from RESEARCH.md impact analysis).
- If conflict occurs, the merge PR will show it. The human or PM resolves.

### 6.2 Shared files: SKILL.md, CHANGELOG.md

These are modified by multiple roles:
- DM updates SKILL.md (delivery), CHANGELOG.md (version bumps)
- Dev agents update SKILL.md (new features), README.md (docs)

**Rule**: Only the agent whose branch is being merged updates these files. DM's changes to SKILL.md/CHANGELOG.md happen on main (delivery is a main activity). Dev agent changes to SKILL.md happen on their branch. Merge conflict on merge is resolved by the merger.

### 6.3 Two dev agents working simultaneously

If `skill` works on #375 and `designer` works on #401, they have separate branches. No conflict unless they touch the same files. The planning/research phase identifies file overlap risk.

### 6.4 Agent reads another agent's code changes

Agent A commits code to its branch. Agent B (on main) cannot see A's changes until the PR is merged. This is BY DESIGN -- untested code should not leak to other agents. If B needs A's output (dependency), the tracker blocks B until A's PR is merged.

---

## 7. git_ops.py Changes Required

### 7.1 New commands

```python
# Selective staging
def add_paths(paths):
    """Stage specific file paths (not -A)."""

# Branch-aware commit flow
def commit_code(role, branch, message):
    """Checkout branch, stage code paths, commit, push, return to main."""

def commit_state(role, message):
    """On main, stage .squidsquad/ paths, commit, push."""

# Branch management
def branch_exists(name):
    """Check if branch exists locally or remotely."""

def branch_delete(name):
    """Delete local branch after merge."""

def current_branch():
    """Return the name of the current branch."""

# Merge support
def merge_branch(name):
    """Merge a branch into current branch (for PM/QA merge authority)."""
```

### 7.2 Modified commands

- `pull()` -- needs to handle pulling on feature branches, not just main. Also needs to pull main separately to get other agents' state updates.
- `commit_push()` -- keep as backward-compatible shortcut for state-only commits on main. Add a new `commit_push_code()` for branch commits.
- `add_all()` -- deprecate or restrict to state-only mode.

### 7.3 Path classification

git_ops.py needs to know which paths are "code" vs "state":

```python
STATE_PATHS = [".squidsquad/"]
CODE_PATHS = [
    "references/", "tests/", "SKILL.md", "README.md",
    "CHANGELOG.md", "CLAUDE.md", "setup.py", "pyproject.toml",
]
```

Or inversely: everything NOT in `.squidsquad/` is code.

---

## 8. Impact on Ralph Loop

### 8.1 Step 1 -- Pull Latest

Currently: `git pull --rebase` on main.

With branches: Agent must pull BOTH:
1. `git pull --rebase` on main (to get state updates from all agents)
2. If working on a branch: `git checkout <branch> && git pull --rebase && git checkout main`

Or: stay on main for the triage/state steps, switch to branch only during Step 3 (implementation).

### 8.2 Step 2 -- Triage

No change. Triage reads GitHub Issues, not local files. Happens on main.

### 8.3 Step 3 -- Implement Tasks (dev agents)

Currently: implement on main, commit at end of cycle.

With branches:
1. At task pickup: create branch `squidsquad/feat-skill-NNN` (if not exists)
2. Switch to branch
3. Implement
4. Run tests (on branch)
5. Stage code files, commit to branch, push branch
6. Switch back to main
7. Stage state files, commit to main, push main
8. Create PR (if first push to branch)

### 8.4 Step 4 -- Iteration Log

No change. Iteration logs go to `.squidsquad/` which is on main.

### 8.5 Step 5 -- Commit and Push

This step is replaced by the split commit in Step 3. The existing Step 5 becomes state-only:

```bash
python references/scripts/git_ops.py commit-state [ROLE] "[state update]"
```

### 8.6 Working state across branch switches

The working state file is on main. When an agent switches to a branch to work, its working-state on main says "in-progress on #NNN on branch squidsquad/feat-skill-NNN". Other agents (PM, QA) see this on main and know not to conflict.

### 8.7 QA verification on branches

QA needs to test the code on the feature branch before it merges to main. This means QA must:
1. Check out the PR branch
2. Run tests
3. Switch back to main
4. Record results on main

This adds branch-switching complexity to QA's loop.

---

## 9. compose.py and Templates

### 9.1 The deploy problem

`compose.py deploy <role>` reads from `references/` and writes to `.squidsquad/<role>/CLAUDE.md`. If `references/` changes are on a branch, `compose.py` on main generates stale output.

**Options**:
1. Deploy is a branch operation -- run `compose.py` on the branch, deploy to branch's `.squidsquad/`. The composed CLAUDE.md goes on the branch, not main. Agents on main keep using the old CLAUDE.md until merge.
2. Deploy happens at merge time -- a merge hook or PM step runs `compose.py deploy all` after merging.
3. Deploy is separate -- treat `.squidsquad/*/CLAUDE.md` as a build artifact that gets regenerated. Not tracked in git for this purpose.

**Recommendation**: Option 2. After merging a PR that touches `references/`, PM runs `compose.py deploy all` to regenerate all agent CLAUDE.md files. This keeps main's agent instructions in sync with the merged code.

### 9.2 Template changes during development

While a dev agent is on a branch changing templates, the agent reads its CLAUDE.md from main (the old version). The new template takes effect after merge. This is acceptable -- the agent is following instructions to implement the change, not the changed instructions themselves.

---

## 10. Side Effects, Edge Cases, and Integration Risks

### 10.1 Side Effects

1. **Commit history changes**: Main will have only state commits + merge commits. Feature branches have code commits. Git log on main becomes harder to follow.
2. **CI/CD impact**: If any CI runs on main, it now only sees merged code. Branch CI (PR checks) becomes the primary quality gate.
3. **Vault writes on main**: Vault remember happens at end of cycle. Vault content reflects decisions made on the branch. The vault note references code that isn't on main yet. Acceptable -- vault notes are about decisions, not code.
4. **Config counter races**: Multiple agents incrementing `Shipped Since Last Bump` on main simultaneously. Already a risk today; branches don't change this.

### 10.2 Edge Cases

1. **Agent crash mid-cycle**: Agent has code staged on branch but hasn't committed state to main. On restart, working-state.md is stale. Mitigation: working state is written BEFORE code changes, not after. On resume, agent checks branch existence and picks up where it left off.
2. **Branch diverges significantly from main**: Long-running feature branch gets merge conflicts. Mitigation: agents rebase branch on main at cycle start (`git rebase main` on the feature branch).
3. **Two agents create same branch name**: Branch names include role, so `squidsquad/feat-skill-375` and `squidsquad/feat-designer-375` are distinct. Only a risk if two instances of the same role exist (not supported).
4. **git stash across branch switches**: If state files are dirty when switching to a branch, git may stash them. The stash/pop cycle could lose state changes.
5. **QA checks out a branch that is force-pushed**: Dev agent rebases and force-pushes. QA's local branch is now diverged. Mitigation: QA always fetches before checkout.
6. **Empty branch commit**: Agent picks up a task but all changes are state-only (e.g., planning artifacts). No code to put on branch. Mitigation: only create branch when actual code changes exist.

### 10.3 Integration Risks

1. **PR Flow (#246)**: This feature IS the full implementation of PR Flow. The existing toggle and basic branch/PR commands become the default workflow. Risk: LOW -- the primitives exist.
2. **QA role separation (#347)**: QA needs branch-checkout capability for verification. QA's verification sub-skill must be updated. Risk: MEDIUM -- QA currently only works on main.
3. **Auto boot (#4)**: Booted agents must know which branch to resume on. Working-state.md records the branch name. Risk: LOW -- boot reads working-state.
4. **Improvement scanning**: Scan targets main (the project code). If code is on branches, scanning main may miss recent work. Acceptable -- scanning finds existing issues, not WIP.
5. **Vault optimize**: Runs on main. No branch interaction. Risk: NONE.
6. **Health check**: Reads `current-state` files on main. No branch awareness needed. Risk: NONE.
7. **Status bar**: Reads from main. No change. Risk: NONE.

### 10.4 Upgrade Path

- **New config values**: `PR Flow: Enabled` changes from `no` to `yes` (or a new `branch-mode` option).
- **New git_ops.py commands**: `add-paths`, `commit-code`, `commit-state`, `branch-exists`, `branch-delete`, `current-branch`.
- **Template changes**: All role-specific `git-commit.md` sub-skills rewritten. `common/git-commit.md` rewritten.
- **Upgrade steps**: `/squidsquad-upgrade` must:
  1. Update `git_ops.py` with new commands.
  2. Re-compose all roles (`compose.py deploy all`).
  3. Set `PR Flow: Enabled: yes` in config.md (or prompt user).
- **Graceful degradation**: If user doesn't upgrade, agents continue pushing to main. No breakage. The old `commit-push` command still works.
- **Rollback**: Set `PR Flow: Enabled: no` to revert to direct-to-main workflow.

---

## 11. Open Questions

- **Q1**: Should ALL roles use branches, or only dev roles (skill, designer)? PM, DM, and QA primarily produce state files, not code. Forcing them onto branches adds complexity with little benefit. **Why**: Unnecessary branching for non-code roles increases merge overhead and slows coordination.

- **Q2**: How should `compose.py deploy` work after merge? Should it be an automated post-merge hook, a PM step, or a manual human action? **Why**: Stale CLAUDE.md after merge means agents run old instructions until recomposition.

- **Q3**: Should QA check out feature branches to test, or should tests run on the branch via CI/PR checks? **Why**: QA branch-switching adds complexity. CI-based testing is simpler but requires GitHub Actions setup.

- **Q4**: How to handle the CLAUDE.md / SOUL.md gray area -- are these "code" (branch) or "state" (main)? They are generated artifacts that live in `.squidsquad/`. **Why**: Getting this wrong means agents run stale instructions or instructions that reference unmerged code.

- **Q5**: Should the branch-per-feature workflow be mandatory (replace current direct-to-main) or opt-in (extend current PR Flow toggle)? **Why**: Mandatory is cleaner but higher upgrade risk. Opt-in maintains backward compatibility but means two code paths to maintain.

---

## 12. Recommendation

**Feasible with caveats**. The core primitives (branch-create, branch-switch, pr-create) exist in git_ops.py. The hard problems are:

1. **Commit split** -- new git_ops.py commands for selective staging, tested against branch-switch edge cases.
2. **QA on branches** -- QA verification sub-skill needs branch-checkout capability.
3. **Post-merge recomposition** -- compose.py deploy must run after merges that touch `references/`.
4. **Template scope** -- all 5 role-specific git-commit sub-skills need rewriting.

Suggested implementation order:
1. Add new git_ops.py commands (add-paths, commit-code, commit-state, branch-exists, branch-delete, current-branch)
2. Rewrite `common/git-commit.md` with the split commit workflow
3. Update dev role git-commit sub-skills
4. Update QA verification to handle branch checkout
5. Add post-merge compose.py deploy step to PM loop
6. Update non-dev role git-commit sub-skills (if they get branches) or keep them main-only
7. Update upgrade skill
8. Test upgrade path from PR Flow: no -> PR Flow: yes

Estimated complexity: **High**. The commit split and QA branch verification are non-trivial. Recommend keeping PM/DM/QA on main-only and only branching dev roles (skill, designer) to reduce scope.
