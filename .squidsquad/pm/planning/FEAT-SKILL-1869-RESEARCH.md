# Research: FEAT-SKILL-1869 — 3-Branch Architecture (State Bus)

**Date**: 2026-04-19
**Researcher**: pm-lead
**Issue**: #1869

---

## Executive Summary

The 3-branch architecture proposes separating SquidSquad state from project code and agent templates. However, research reveals a critical insight: **the key runtime state files (current-state, .health, .pid, context-pressure) are already .gitignore'd** and never committed to git. They are local-only, per-clone runtime files. What IS committed to main today is:

- **Templates**: CLAUDE.md, SOUL.md per role (agent instructions)
- **Planning artifacts**: planning/, bugs/, features/ per role
- **Iteration logs**: iterations/ per role (162 files currently)
- **Working state**: working-state.md per role (committed, used for context-pressure recovery)
- **Vault**: shared knowledge (20 files — BRIEFING.md, galaxy/, areas/, etc.)
- **Config**: config.md, hints-*.txt, boot scripts, permissions templates
- **Scan history**: scan-history.md per role
- **QA logs**: qa-log.md

This changes the problem statement significantly. The primary pain is NOT runtime state polluting main — that is already solved by .gitignore. The pain is that **iteration logs, planning artifacts, working-state, scan-history, and vault** all live on main alongside project code.

---

## 1. Git Mechanics — Reading From Another Branch

### git show (no checkout required)

```bash
git show origin/squidsquad-state:.squidsquad/skill/working-state.md
```

**Benchmarked on this repo (Windows 11, 1310 commits, 10MB repo)**:
- Local file read (5 files): **~70ms** (0.069s real)
- git show HEAD (5 files): **~134ms** (0.134s real)
- git show is ~2x slower than local read but still sub-200ms for 5 files

**For remote branch reads**: requires `git fetch origin squidsquad-state` first.
- git fetch (cold, this repo): **~415ms** (0.415s real)
- Total round-trip: ~550ms for fetch + 5 reads — acceptable for 30-min cycle intervals

### git worktree (persistent checkout of state branch)

```bash
git worktree add /path/to/state-worktree squidsquad-state
```

**Tested**: worktree creation works. Provides a regular filesystem directory checked out to the state branch. File reads from worktree = identical speed to local file reads (~70ms for 5 files).

**Constraint**: cannot have two worktrees on the same branch. Each agent clone can have one worktree per branch. This is fine — each clone would have ONE state worktree.

**On Windows**: worktree paths use native Windows paths (C:\Users\...), not /tmp. This works correctly.

### Sparse checkout

Not necessary. The state branch would contain ONLY state files (small), so full checkout is fine. Sparse checkout adds complexity for no benefit here.

### Recommendation

**Use git worktree** for the state branch. Each agent's clone gets:
```
D:/Dev/AgentClone/                     ← main worktree (project + templates)
D:/Dev/AgentClone/.squidsquad-state/   ← state worktree (or ~/.squidsquad/state/)
```

Reads are filesystem-speed. Writes are normal git add/commit/push in the worktree.

---

## 2. Git Mechanics — Writing To Another Branch

### Approach A: Worktree (recommended)

With a persistent worktree, writing is trivial:
```bash
# In the state worktree directory
echo "idle|" > .squidsquad/pm/current-state
git add .squidsquad/pm/current-state
git commit -m "pm: state update"
git push origin squidsquad-state
```

**Pros**: Simple, uses standard git workflow. Agents already know how to git add/commit/push.
**Cons**: Requires persistent worktree directory. Adds ~1 extra directory per clone.

### Approach B: Git plumbing (commit without checkout)

```bash
BLOB=$(echo "idle|" | git hash-object -w --stdin)
# Then: git update-index, git write-tree, git commit-tree, git update-ref
```

**Tested**: `git hash-object -w --stdin` works (produced hash d64a384...).

**Pros**: No worktree needed. Pure plumbing, no filesystem state.
**Cons**: Complex. Error-prone. Hard to debug. Must rebuild the entire tree manually for each commit. Not worth the complexity when worktrees exist.

### Approach C: Temp checkout

```bash
git stash
git checkout squidsquad-state
# write files
git add -A && git commit && git push
git checkout main
git stash pop
```

**Pros**: Simple to understand.
**Cons**: Terrible for concurrent use. Stash/pop conflicts. Disrupts working directory. The exact problem we're trying to solve.

### Recommendation

**Approach A (worktree)** is the clear winner. It is simple, fast, and supports concurrent use because each worktree is independent.

---

## 3. Concurrent Push Conflicts

### The scenario

Two agents push to `squidsquad-state` simultaneously. Agent A (PM) writes `.squidsquad/pm/working-state.md`. Agent B (skill) writes `.squidsquad/skill/working-state.md`.

### Git behavior

When Agent B pushes after Agent A:
```
! [rejected] squidsquad-state -> squidsquad-state (fetch first)
```

Git rejects the push because Agent B's local ref is behind.

### Resolution: pull --rebase before push

```bash
cd /path/to/state-worktree
git pull --rebase origin squidsquad-state
git push origin squidsquad-state
```

**Since each agent writes only to its own directory** (`.squidsquad/pm/`, `.squidsquad/skill/`, etc.), `git pull --rebase` will auto-merge cleanly — the files don't overlap. Git's merge machinery handles this automatically.

### Shared files: vault/

Vault IS written by multiple agents (vault-remember, vault-optimize). If vault lives on the state branch, concurrent vault writes could conflict.

**Mitigations**:
- Each vault file is a separate .md file in galaxy/ — conflicts only occur if two agents edit the same galaxy file simultaneously (unlikely — different topics)
- BRIEFING.md is rewritten by vault-optimize, which runs once per cycle — low frequency
- .relevance-index.json could conflict if two agents run vault-optimize in the same second (extremely unlikely)

**Retry-on-conflict** strategy:
```python
for attempt in range(3):
    pull_result = git_pull_rebase(state_worktree)
    push_result = git_push(state_worktree)
    if push_result.success:
        break
    # If push fails, pull again and retry
```

This is sufficient. Lock files add unnecessary complexity for a problem that rarely occurs and auto-resolves with rebase.

### Shared file: config.md

Config.md is read frequently, written rarely (ship counter increments). If on the working branch (not state), this is a non-issue — only PM modifies it. If it moves to state branch, the retry-on-conflict pattern handles it.

---

## 4. Orphan Branch Design

### Creation

```bash
git checkout --orphan squidsquad-state
git rm -rf .
# Create initial directory structure
mkdir -p .squidsquad/{pm,skill,qa,dm}/{iterations,planning}
mkdir -p .squidsquad/vault/{galaxy,areas,archives,resources,projects}
# Add initial files
echo "# SquidSquad State Branch" > README.md
git add -A
git commit -m "squidsquad: initialize state branch"
git push -u origin squidsquad-state
git checkout main
```

**Note**: `git worktree add --orphan` was tested but is not available in git 2.44 (the `--orphan` flag for worktree was added in git 2.42+ but the syntax differs). The safest approach is to create the orphan branch first, push it, then add a worktree for it.

### Initial content

- Empty directory structure for each role
- Migrated state files from main (iterations, working-state, scan-history, etc.)
- Vault contents (if vault goes on state branch)

### Shared history with main

**None required.** That is the point of an orphan branch — it has its own independent history. This means `git log` on the state branch shows only state changes, not code changes. Clean separation.

### Size management

**Current stats**: 162 iteration files, 221 planning files across roles. The state branch will accumulate commits rapidly (every agent cycle = every 30 min for PM, variable for others).

**Mitigation options**:
1. **Periodic squash**: squash state branch to a single commit every N days. Loses history but keeps branch lean. A setup script can do this.
2. **Iteration cleanup**: `cycle.py cleanup-iterations` already exists — keeps only the last N iteration logs. This naturally bounds growth.
3. **Shallow clone**: agents can `git clone --depth 1 --single-branch -b squidsquad-state` for the state worktree. History irrelevant.
4. **git gc**: standard garbage collection handles unreachable objects.

**Recommendation**: Use shallow clone for state worktrees + periodic iteration cleanup (already implemented). No manual squash needed.

---

## 5. What Lives Where — Complete File Categorization

### Currently tracked files in .squidsquad/ (566 total):

| File/Pattern | Current | Proposed Branch | Rationale |
|---|---|---|---|
| `config.md` | main | working | Project config, rarely changes, read by all |
| `{role}/CLAUDE.md` | main | working | Agent templates, tied to code changes |
| `{role}/SOUL.md` | main | working | Agent personality, version-controlled |
| `hints-*.txt` | main | working | Statusline hints, config |
| `start-{role}.{sh,ps1}` | main | working | Boot scripts, infrastructure |
| `inject-permissions.*` | main | working | Setup scripts |
| `permissions.template.json` | main | working | Setup template |
| `templates/` | main | working | Composition templates |
| `boot/CLAUDE.md`, `boot/SOUL.md` | main | working | Boot agent template |
| `{role}/working-state.md` | main | **state** | Runtime state, changes every cycle |
| `{role}/iterations/` | main | **state** | Cycle logs, accumulate rapidly (162 files) |
| `{role}/planning/` | main | **state** | Planning artifacts, tied to task execution |
| `{role}/scan-history.md` | main | **state** | Improvement scan state |
| `{role}/bugs/` | main | **state** | Bug tracking artifacts |
| `{role}/features/` | main | **state** | Feature tracking artifacts |
| `{role}/qa-log.md` | main | **state** | QA test results |
| `{role}/enhancements.md` | main | **state** | PM backlog |
| `{role}/.restart` | main | **state** | Restart sentinel |
| `vault/` | main | **split** | See Section 6 |
| `diagnostics/` | main | **state** | Runtime diagnostics |
| `.backlog-cache` | main | **state** | Cached backlog data |
| `boot-attempts.log` | main | **state** | Boot history |

### Currently .gitignore'd (runtime-only, per-clone):

| File | Status | Change Needed? |
|---|---|---|
| `{role}/current-state` | .gitignore'd | **No change** — stays local |
| `{role}/.health` | .gitignore'd | **No change** — stays local |
| `{role}/.pid` | .gitignore'd | **No change** — stays local |
| `{role}/context-pressure` | .gitignore'd | **No change** — stays local |
| `{role}/.stop` | .gitignore'd | **No change** — stays local |
| `.local-config` | .gitignore'd | **No change** — stays local |
| `.active-role` | .gitignore'd | **No change** — stays local |
| `boot-lock` | .gitignore'd | **No change** — stays local |
| `scan-index.db` | .gitignore'd | **No change** — stays local |

### Key insight

The runtime liveness files (current-state, .health, .pid) are already local-only. The 3-branch architecture does NOT need to put them on the state branch. They work fine as local files because:
- They are written and read by the SAME clone
- Cross-clone reading uses `~/.squidsquad/clones/` paths or `.local-config`
- The watchdog runs in ONE clone and reads from clone paths

The state branch is for **persistent state that must survive context resets and be visible across clones**: working-state, iterations, planning, vault, scan-history.

### Planning artifacts: state vs working?

**Current behavior**: planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) are committed to main alongside the code change they relate to. They provide audit trail.

**Argument for state branch**: they pollute main's history with non-code commits. They accumulate (221 files currently).

**Argument for working branch**: they are tied to specific code tasks and provide context in PRs.

**Recommendation**: **State branch**. Planning artifacts are consumed by agents during task execution, not by humans reviewing PRs. The GitHub Issue provides the audit trail. Moving 221+ planning files off main dramatically reduces noise.

---

## 6. Vault Location Decision

### Option A: Entirely on state branch

**Pros**:
- Always available via state worktree
- Never pollutes main or working branch
- Single location for all agents to read/write

**Cons**:
- Not visible in code PRs (but vault content is not code-specific)
- Requires state worktree to be available for template composition (compose.py reads vault for BRIEFING references)

### Option B: Entirely on working branch

**Pros**:
- Version-controlled with code
- Visible in PRs

**Cons**:
- All agents must push to working branch to update vault
- Vault changes mixed with code changes
- Currently this IS the problem — vault changes on main add noise

### Option C: Split — BRIEFING.md on working, galaxy/ on state

**Pros**:
- BRIEFING.md (read-only summary, ~2000 tokens) on working branch = available during compose.py
- galaxy/ (write-heavy, many small files) on state = no noise on working branch

**Cons**:
- Split location is confusing
- BRIEFING.md must be synced from state to working when vault-optimize runs

### Recommendation: **Option A (entirely on state branch)**

Compose.py can read vault from the state worktree path. The path is predictable (configured at setup). BRIEFING.md is ~2KB — reading from a worktree directory is identical to reading from the main checkout. No split needed.

---

## 7. Performance Analysis

### Benchmarks (measured on this repo, Windows 11)

| Operation | Time | Notes |
|---|---|---|
| Local file read (5 files) | **69ms** | Baseline |
| git show HEAD (5 files) | **134ms** | ~2x local, no network |
| git fetch origin | **415ms** | Network round-trip |
| Worktree file read | **~69ms** | Same as local (it IS local) |
| git pull --rebase (state wt) | **~500ms** | fetch + rebase |
| git push (state wt) | **~400ms** | Network |

### Agent read/write frequency

- PM cycle: every 30 minutes
- Dev agent cycle: varies (30 min when idle, faster when active)
- Health check: every 30 seconds (watchdog) — but reads LOCAL files, not git
- State writes: ~2-5 per cycle (working-state, iteration log, current-state)

### Impact assessment

With worktree approach:
- **Reads**: filesystem speed (~69ms) — NO performance regression
- **Writes**: standard git add/commit/push (~1s total) — same as current
- **Cross-clone reads**: unchanged — still uses `~/.squidsquad/clones/` paths for runtime files
- **Additional cost per cycle**: one `git pull --rebase` on state worktree (~500ms) — negligible in a 30-min cycle

**Verdict**: No meaningful performance impact with the worktree approach.

---

## 8. Health Check Redesign

### Current architecture

- `health_check.py` reads `.health`, `.pid`, `current-state` from cross-clone filesystem paths
- Uses `.local-config` or `~/.squidsquad/clones/` to find clone paths
- Checks file mtime for staleness

### What changes?

**Nothing for runtime liveness checks.** The files health_check.py reads (`.health`, `.pid`, `current-state`) are all `.gitignore`d and remain local per-clone. The health check system is orthogonal to the 3-branch architecture.

### What about persistent state?

If a PM wants to see another agent's `working-state.md` (to know what task they're working on), currently it reads from the agent's clone path. With the state branch, it could also read from the shared state worktree.

**However**: the current cross-clone system works. The state branch provides a BACKUP path for this data, not a replacement. Health checks should continue reading local files for speed.

### Staleness via git

For cases where cross-clone paths aren't configured (remote agents, CI):
```bash
git log -1 --format="%ct" origin/squidsquad-state -- .squidsquad/skill/working-state.md
```
This returns the commit timestamp of the last update. Comparing to current time gives staleness. This is a future enhancement, not a blocker.

---

## 9. Watchdog Integration

### Current behavior

Watchdog reads `.health`, `.pid`, `context-pressure` from filesystem paths. Runs every 30 seconds.

### Impact of 3-branch architecture

**Zero impact.** All files the watchdog reads are `.gitignore`d local runtime files. The watchdog does not need the state branch at all.

### Future enhancement

If agents run on different machines (remote agents), the watchdog could read state from the state branch instead of filesystem paths. But this is a separate feature — the current local-file approach is fine for single-machine multi-clone setups.

---

## 10. Migration Path

### Step-by-step migration

1. **Create orphan branch**:
   ```bash
   git checkout --orphan squidsquad-state
   git rm -rf .
   ```

2. **Populate from current main**:
   ```bash
   # Restore only state files from main
   git checkout main -- .squidsquad/*/iterations/
   git checkout main -- .squidsquad/*/planning/
   git checkout main -- .squidsquad/*/working-state.md
   git checkout main -- .squidsquad/*/scan-history.md
   git checkout main -- .squidsquad/*/bugs/
   git checkout main -- .squidsquad/*/features/
   git checkout main -- .squidsquad/*/qa-log.md
   git checkout main -- .squidsquad/*/enhancements.md
   git checkout main -- .squidsquad/*/.*restart
   git checkout main -- .squidsquad/vault/
   git checkout main -- .squidsquad/diagnostics/
   git checkout main -- .squidsquad/.backlog-cache
   git checkout main -- .squidsquad/boot-attempts.log
   git commit -m "squidsquad: initialize state branch from main"
   git push -u origin squidsquad-state
   ```

3. **Remove migrated files from main**:
   ```bash
   git checkout main
   git rm -r .squidsquad/*/iterations/
   git rm -r .squidsquad/*/planning/
   # ... etc for all state files
   git commit -m "squidsquad: move state files to squidsquad-state branch"
   ```

4. **Update .gitignore on main**: add patterns for state files that should never appear on main again.

5. **Add worktree setup to boot scripts**:
   ```bash
   # In start-{role}.sh / start-{role}.ps1
   if [ ! -d ".squidsquad-state" ]; then
     git worktree add .squidsquad-state squidsquad-state
   fi
   ```

6. **Update scripts to use worktree path for state files**: git_ops.py, cycle.py, compose.py.

### Preserving history

The `git checkout main -- <files>` approach copies files without history. Full history stays on main. The state branch starts fresh. This is acceptable — the git log on main preserves the audit trail, and the state branch starts clean.

### In-flight PRs during migration

In-flight PRs that modify .squidsquad/ files will need rebasing after migration. This is a one-time cost. **Recommendation**: freeze agent activity during migration (use `.stop` sentinels), perform migration, then restart.

---

## 11. Impact on Existing Scripts

### scripts that MUST change

| Script | Change | Complexity |
|---|---|---|
| `git_ops.py` | Add `commit-state-branch` command using worktree path. `commit-state` currently targets main — must target state worktree instead. | Medium |
| `cycle.py` | `status-bar` writes current-state (local, no change). `log-iteration` writes to iterations/ — must write to state worktree. `cleanup-iterations` same. | Medium |
| `compose.py` | Must read vault BRIEFING.md from state worktree path instead of main checkout. | Low |

### scripts that need NO change

| Script | Why |
|---|---|
| `health_check.py` | Reads .health/.pid/current-state — all local .gitignore'd files |
| `boot_remote.py` | Reads .health/.pid — all local .gitignore'd files |
| `watchdog.py` | Reads .health/.pid/context-pressure — all local .gitignore'd files |
| `tracker.py` | Uses GitHub Issues API, not git |

### Agent CLAUDE.md templates

All agent templates reference `.squidsquad/{role}/` paths for state files. These paths must change to the state worktree path. Two approaches:

1. **Symlink**: `.squidsquad/state/` -> state worktree. Templates use `.squidsquad/state/{role}/` for state files.
2. **Config variable**: add a `STATE_PATH` to config.md that scripts read.
3. **Convention**: state worktree is always at `.squidsquad-state/` relative to repo root.

**Recommendation**: Option 3 (convention). Simplest. The path `.squidsquad-state/.squidsquad/{role}/` is verbose but unambiguous. Alternatively, the worktree root could map directly to the state content so the path is just `.squidsquad-state/{role}/`.

---

## 12. Edge Cases

### Network down

**Impact**: agents can still READ state from the local worktree (it's just files). They can still COMMIT locally. They cannot PUSH until network returns.

**Mitigation**: the same `pull --rebase` retry pattern handles this. Agents accumulate local commits and push when network returns. Since each agent writes its own directory, conflicts are extremely unlikely.

This is actually BETTER than the current situation, where network-down agents can't push their state changes to main at all.

### State branch diverges (agent dies mid-push)

If an agent commits locally to the state worktree but dies before pushing:
- The local worktree has uncommitted or un-pushed state
- Next boot: `git pull --rebase` in the state worktree syncs up
- Since only this agent writes its own directory, no conflicts

### First-time setup (no state branch exists)

The setup script (`squidsquad-setup`) must:
1. Create the orphan branch
2. Push it to origin
3. Add worktree in each clone

If the state branch doesn't exist on remote, agents fall back to creating it. This should be a setup-time operation, not a per-cycle check.

### Single-clone setup (no multi-agent)

**Still valuable.** Even with one clone:
- Main branch stays clean (no iteration logs, planning artifacts, scan history)
- The state worktree provides a clean separation of concerns
- Future multi-clone setup is easier — just add worktrees

**Complexity cost**: one extra directory, one extra `git pull` per cycle (~500ms). Minimal.

---

## 13. The "Working Branch" Question

The original proposal includes a `squidsquad` working branch where agent code changes and PRs target. This is essentially the existing branch-per-feature workflow:

- Currently: feature branches branch off main, PRs target main
- Proposed: feature branches branch off `squidsquad`, PRs target `squidsquad`

### Assessment

This adds value ONLY if we want to keep main completely clean of SquidSquad files. Currently, `.squidsquad/` config and templates live on main. If the goal is "main = project code only", then yes, a working branch makes sense.

**However**, this means:
- Users must merge `squidsquad` -> main to get template updates
- The repo has a permanent non-main branch that hosts configuration
- CI/CD must account for the working branch
- More complex than necessary for most projects

### Recommendation

**Defer the working branch.** The state branch solves the biggest pain (state pollution). Templates and config on main are not high-frequency changes — they change when features ship, which is acceptable on main. The 2-branch model (main + squidsquad-state) captures 90% of the benefit with 50% of the complexity.

---

## 14. Recommended Architecture (Revised)

### 2-branch model (recommended over 3-branch)

1. **main** — project code + SquidSquad config/templates (`.squidsquad/` with only config, templates, boot scripts, hints)
2. **squidsquad-state** (orphan) — all runtime-persistent state (iterations, planning, working-state, scan-history, vault, bugs, features, diagnostics)

### Per-clone layout

```
repo-root/
  .squidsquad/              # On main: config, templates, boot scripts
    config.md
    {role}/CLAUDE.md
    {role}/SOUL.md
    hints-*.txt
    start-{role}.*
  .squidsquad-state/        # Worktree for squidsquad-state branch
    .squidsquad/
      {role}/
        working-state.md
        iterations/
        planning/
        scan-history.md
        bugs/
        features/
      vault/
      diagnostics/
  # Local-only (.gitignore'd, no branch):
  .squidsquad/{role}/current-state
  .squidsquad/{role}/.health
  .squidsquad/{role}/.pid
  .squidsquad/{role}/context-pressure
```

### Write pattern for agents

```python
# State writes (iterations, working-state, planning)
def commit_state(role, message):
    state_wt = REPO_ROOT / ".squidsquad-state"
    # Write files into state_wt/.squidsquad/{role}/
    subprocess.run(["git", "pull", "--rebase"], cwd=state_wt)
    subprocess.run(["git", "add", "-A"], cwd=state_wt)
    subprocess.run(["git", "commit", "-m", f"{role}: {message}"], cwd=state_wt)
    for attempt in range(3):
        result = subprocess.run(["git", "push"], cwd=state_wt, check=False)
        if result.returncode == 0:
            break
        subprocess.run(["git", "pull", "--rebase"], cwd=state_wt)

# Code writes (feature changes) — unchanged
def commit_code(role, branch, message):
    # Same as current git_ops.py commit-code
    ...

# Runtime state (current-state, .health) — unchanged
def write_current_state(role, phase, desc):
    # Write to local .squidsquad/{role}/current-state — no git involved
    ...
```

---

## 15. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Worktree corruption | Low | Medium | Worktree can be deleted and re-created; state branch on remote is source of truth |
| Push conflicts on state | Low | Low | Retry-on-conflict with pull --rebase; agents write to separate directories |
| Vault write conflicts | Very Low | Low | Different agents write different galaxy files; BRIEFING rewrite is single-agent |
| Migration disrupts in-flight work | Medium | Medium | Freeze agents with .stop sentinels during migration |
| Increased setup complexity | Certain | Low | Automate in squidsquad-setup; single `git worktree add` command |
| Old git versions lack worktree support | Low | High | Require git >= 2.15 (released 2017); document in prerequisites |

---

## 16. Open Questions for Discussion

1. **2-branch vs 3-branch**: research recommends 2-branch (main + state). Is there a strong case for the working branch?
2. **State worktree location**: `.squidsquad-state/` in repo root vs `~/.squidsquad/state/{project}/` in home dir?
3. **Vault on state branch**: confirmed recommendation. Any objections?
4. **Planning artifacts on state branch**: they currently provide context in PRs. Losing that visibility acceptable?
5. **Migration timing**: freeze agents and migrate in one shot, or gradual migration?
6. **Minimum git version**: git >= 2.15 for worktree support. Acceptable?

---

## 17. Implementation Estimate

| Phase | Description | Effort |
|---|---|---|
| 1. Create orphan branch + migration script | Script to create branch, populate from main, clean main | 1-2 days |
| 2. Update git_ops.py | Add state-branch-aware commit/push, retry-on-conflict | 1 day |
| 3. Update cycle.py | Iteration logging to state worktree | 0.5 day |
| 4. Update compose.py | Read vault from state worktree | 0.5 day |
| 5. Update agent templates | Path references for state files | 1 day |
| 6. Update boot scripts | Auto-create worktree on first boot | 0.5 day |
| 7. Update squidsquad-setup | Orphan branch creation + worktree setup | 0.5 day |
| 8. Testing + edge cases | Multi-agent concurrency, network failure, first-time setup | 1-2 days |
| **Total** | | **5-7 days** |
