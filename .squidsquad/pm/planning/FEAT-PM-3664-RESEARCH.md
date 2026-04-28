# FEAT-PM-3664 Research — Move High-Churn State Files to squid-squad Branch

**Date**: 2026-04-27
**Researcher**: pm-lead
**Issue**: #3664

---

## Summary

This task proposes moving `iterations/`, `diagnostics/`, `.backlog-cache`, `working-state.md`, and `scan-history.md` from main to the `squid-squad` state branch to eliminate cross-agent merge conflicts on main.

**Key finding**: The infrastructure is already ~80% built. `state_bus.py`, `migrate_state_branch.py`, and the state branch config entry all exist. The config (`config.md`) already declares `**State Branch**: squid-squad`. What does NOT exist is any wiring between `cycle_pre.py`, `cycle_post.py`, `git_ops.py` and `state_bus.py` — all three still operate entirely on main.

**Recommendation**: Feasible, but requires coordinated changes across 4 scripts plus a one-time migration. The biggest risk is mid-flight: agents on main during the cutover will conflict on the state files that were just moved. A maintenance window or phased cutover is needed.

---

## 1. How cycle_post.py Currently Commits State Files

`cycle_post.py` has three commit paths depending on role:

### Path A — Skill agent with branch workflow (lines 206–239)
1. `commit-code` to the feature branch (code files only, excludes `.squidsquad/`).
2. Switches back to working branch (main).
3. Calls `git_ops.py commit-state role state_msg` — stages every file under `.squidsquad/` and commits/pushes to main.
4. Falls back to `commit-push` (git add -A) if `commit-state` fails.

### Path B — QA agent (lines 242–252)
1. Switches back to working branch (main).
2. Calls `git_ops.py commit-push role msg` — `git add -A`, commit, push to main.

### Path C — Default/PM/DM (lines 254–257)
1. Calls `git_ops.py commit-push role msg` — `git add -A`, commit, push to main.

**State files committed to main every cycle** (by all roles via one of the paths above):
- `.squidsquad/<role>/working-state.md` (written by `_do_working_state_update`)
- `.squidsquad/<role>/iterations/iter-N.md` (written by `_do_iteration_log` → `cycle.py log-iteration`)
- `.squidsquad/diagnostics/diagnostic.jsonl` (written by `diagnostics.py log`, called from `git_ops.py`, `tracker.py`, `model_router.py`)
- `.squidsquad/<role>/scan-history.md` (written by agents during improvement scanning)
- `.squidsquad/.backlog-cache` (written by `tracker.py` during backlog queries — not referenced in `cycle_post.py` directly, but staged by `git add -A`)

**What would need to change in cycle_post.py**:
- Path A (`commit-state`) already isolates `.squidsquad/` files — it would need to further split: send high-churn files to the state branch and keep config/planning on main.
- Paths B and C use `commit-push` (git add -A) — these would need to separate state files from non-state files and route each set to its correct branch.
- The `_do_working_state_update` function writes `working-state.md` to the filesystem before the commit step — if this file lives on the state branch, the write path itself must go to the state worktree (`.squidsquad-state/`) rather than `.squidsquad/`.

---

## 2. How cycle_pre.py Currently Reads State Files

`cycle_pre.py` reads state files via direct filesystem paths:

- **`_read_working_state(role)`** (line 133): reads `.squidsquad/<role>/working-state.md` as a local file. If the file doesn't exist, returns empty/default state. This is called in `main()` step 3 for all roles.
- **`_get_cycle_number(role)`** (line 203): reads `.squidsquad/<role>/iterations/` directory, globs `iter-*.md` files, and returns `max(N) + 1`. Direct filesystem traversal of the iterations directory.
- **`_read_context_pressure(role)`** (line 111): reads `.squidsquad/<role>/context-pressure` — this is already gitignored (local only), not a state-branch concern.

**What would need to change in cycle_pre.py**:

Two options (detailed in question 8 below):

**Option A — git show (no checkout)**:
- `_read_working_state` would call `git show squid-squad:.squidsquad/<role>/working-state.md` instead of a direct file read.
- `_get_cycle_number` would need `git ls-tree -r squid-squad -- .squidsquad/<role>/iterations/` to enumerate iteration files, or `git show` on each known file.
- No worktree setup required, but requires the squid-squad branch to be fetched.

**Option B — state worktree (preferred)**:
- `cycle_pre.py` calls `state_bus.py read <path>` for each state file.
- `state_bus.py` already implements `read_file(path)` reading from `.squidsquad-state/` worktree.
- The worktree is a regular filesystem directory — reads are just as fast as local reads.
- Requires `state_bus.py init` to have been run once (worktree setup).

---

## 3. git_ops.py — commit-state and Branch Switching

**What `commit-state` does** (lines 418–475):
1. Runs `git status --porcelain` to find changed files.
2. Filters to files matching `.squidsquad/` prefix only.
3. Asserts the current branch IS the working branch (main) — exits with error if not.
4. Stages only the `.squidsquad/` files via `git add <file>` per file.
5. Commits with role prefix and Co-Authored-By trailer.
6. Pushes to main (`git push`).

**Does it handle branch switching?** No. It enforces that the caller is ALREADY on the working branch. It does not switch to the state branch or use a worktree. It is entirely main-branch-only.

**What would need to change in git_ops.py**:
- Add a new `commit-state-branch` command (or extend `commit-state`) that:
  1. Identifies which files belong in the state branch (`iterations/`, `diagnostics/`, `.backlog-cache`, `working-state.md`, `scan-history.md`).
  2. Writes those files to the state worktree (`.squidsquad-state/`) via `state_bus.write_file()`.
  3. Calls `state_bus.commit_and_push()` to commit and push to `squid-squad`.
  4. Stages and commits any remaining `.squidsquad/` files (config, CLAUDE.md, vault, planning) to main as before.
- The `_is_state_file` helper (line 310) already classifies `.squidsquad/` as ephemeral vs code — a similar classifier is needed for state-branch vs main.

---

## 4. config.md State Branch Setting

From `.squidsquad/config.md` (line 42):

```
## Git Branches

- **Working Branch**: main
- **State Branch**: squid-squad
```

The `state-branch` field is already mapped in `config.py` FIELD_MAP (line 85):
```python
"state-branch": ("Git Branches", "State Branch"),
```

`state_bus.py` reads this via `_read_branch_config()` using regex against `config.md`. No changes needed to the config layer.

---

## 5. What Already Uses the squid-squad Branch

| Script | Usage |
|--------|-------|
| `state_bus.py` | Full implementation: init, read, write, commit. Creates orphan branch, git worktree at `.squidsquad-state/`. Handles push retry with rebase on conflict. |
| `migrate_state_branch.py` | One-shot migration tool. Finds state files on main, copies to state worktree via `state_bus`, commits. Handles dry-run mode. |
| `wizard.py` | Sets `squid-squad` as default state branch name during project setup (lines 577, 1945). |
| `config.py` | Has `state-branch` in FIELD_MAP. |
| `config.md` | Already declares `**State Branch**: squid-squad`. |
| `tests/test_state_bus.py` | Tests for state_bus.py — verifies `squid-squad` as default. |

**Not yet using it**: `cycle_pre.py`, `cycle_post.py`, `git_ops.py`, `cycle.py`, `diagnostics.py`, `scan_index.py`.

---

## 6. Files Committed to Main Every Cycle

Based on code analysis:

| File/Directory | Written by | Committed via |
|----------------|-----------|---------------|
| `.squidsquad/<role>/working-state.md` | `cycle_post._do_working_state_update` | `commit-state` or `commit-push` |
| `.squidsquad/<role>/iterations/iter-N.md` | `cycle.py log-iteration` | `commit-state` or `commit-push` |
| `.squidsquad/<role>/scan-history.md` | Agent creative phase | `commit-state` or `commit-push` |
| `.squidsquad/diagnostics/diagnostic.jsonl` | `diagnostics.py log` (called throughout) | `commit-push` (git add -A) for non-skill roles |
| `.squidsquad/.backlog-cache` | `tracker.py` during backlog queries | `commit-push` (git add -A) |
| `.squidsquad/<role>/current-state` | `cycle_post._write_status_bar` | gitignored (local only) |
| `.squidsquad/<role>/.health` | wrapper heartbeat | gitignored (local only) |
| `.squidsquad/<role>/.pid` | wrapper singleton lock | gitignored (local only) |
| `.squidsquad/<role>/context-pressure` | statusline hook | gitignored (local only) |

The last four are already gitignored — they are NOT the conflict source. The conflict source is the first five.

**Skill agent specifically**: Due to branch workflow, skill commits `.squidsquad/` files via `commit-state` (main) separately from code files (feature branch). Other roles use `commit-push` which stages everything indiscriminately.

---

## 7. Risks of Switching Mid-Flight

### 7a. Existing Iteration History on Main

All existing `iterations/` files live on main. After migration:
- `migrate_state_branch.py` copies them to the state branch.
- If the files are then deleted from main (required for clean separation), git history on main retains them — but agents would need the state branch to read cycle numbers.
- If NOT deleted from main, `git_ops.py commit-push` would still stage them on main (double-write problem until all commit paths are updated).
- **Risk**: Cycle number computation in `cycle_pre._get_cycle_number` reads the filesystem. If both main and state branch have iteration files, the count could be wrong during transition.

### 7b. Agents Mid-Cycle

If agent A is mid-cycle when the migration runs:
- Agent A is reading `working-state.md` from `.squidsquad/<role>/working-state.md` (main copy).
- After migration, the file exists in the state worktree but may no longer be on main.
- Agent A's next `git pull --rebase` would remove the file from its working tree → file-not-found on next read → agent sees empty working state → may reset in-progress work.
- **Risk**: One cycle of work lost for each agent in-flight during migration. Minor but real.

### 7c. Health Files Being Read Cross-Agent

`health_check.py` reads `.squidsquad/<role>/.health` — these are gitignored/local-only, not affected.

`cycle_pre._build_pm_input` calls `health_check.py --json` which reads `.health` files directly from disk — no git dependency. No risk here.

However, `diagnostics/diagnostic.jsonl` IS read cross-agent (PM reads it for reports). If moved to state branch, readers must use `state_bus.read_file()` rather than a direct path. All direct path references in `diagnostics.py`, `model_router.py` would need updating.

### 7d. scan_index.py Rebuilding from scan-history.md

`scan_index.py rebuild` finds all `scan-history.md` files under `.squidsquad/` (line 640). After migration, these files live in the state worktree at `.squidsquad-state/<role>/scan-history.md`. The script would find zero files unless its search path is updated.

### 7e. Windows Worktree Path

`state_bus.py` hardcodes `STATE_WORKTREE = REPO_ROOT / ".squidsquad-state"` (line 31). On Windows this is a native path. Git worktrees on Windows require WSL or Git for Windows — this should work but adds a Windows-specific risk. The `migrate_state_branch.py` already accounts for this.

### 7f. Orphan Branch Initialization

`state_bus.init()` creates an orphan branch by temporarily checking out `--orphan squid-squad`, which modifies the working tree. If an agent is running during this, it may see an unexpected state. The script attempts to restore the original branch in a `finally` block (line 119), but on failure it falls back to the configured working branch — which may not be where the agent expects to be.

---

## 8. cycle_pre.py: git show vs Worktree

**Option A — `git show squid-squad:<path>`**:
- Pros: No worktree required. Works from any branch. Read is atomic (point-in-time snapshot).
- Cons: Requires `squid-squad` to be fetched locally. On first run (cold clone), need `git fetch origin squid-squad`. ~134ms per read vs ~70ms local file (2x slower, acceptable). Cannot list directory contents — `_get_cycle_number` can't glob; needs a separate `git ls-tree` call.
- Implementation: Replace `_read_file(ws_path)` with `subprocess.run(["git", "show", f"squid-squad:.squidsquad/{role}/working-state.md"])`.

**Option B — State worktree (`.squidsquad-state/`)**:
- Pros: Regular filesystem reads — same speed as current. `_get_cycle_number` can use `iter_dir.glob("iter-*.md")` against the worktree path unchanged. Compatible with all existing file-read code.
- Cons: Worktree must be initialized before first use. Worktree is a local-only construct — each agent clone needs its own `state_bus.py init` call. Adds a startup dependency.
- Implementation: Replace `SQUID_DIR = REPO_ROOT / ".squidsquad"` reads with `STATE_WORKTREE = REPO_ROOT / ".squidsquad-state"` for state-branch files. Or: add a helper that returns the correct base path per file type.

**Recommendation**: Worktree (Option B). It is faster, preserves existing glob/path logic, and is already implemented in `state_bus.py`. The startup cost (one `state_bus.py init` per clone) is acceptable given `migrate_state_branch.py` already calls `state_bus.init()`.

---

## Impact Analysis

- **Files touched**:
  - `references/scripts/cycle_pre.py` — read paths for working-state.md and iterations/
  - `references/scripts/cycle_post.py` — `_do_working_state_update` write path; `_do_commit_push` split logic
  - `references/scripts/git_ops.py` — `commit_state()` needs state-branch file routing
  - `references/scripts/cycle.py` — `log_iteration` writes to `SQUIDSQUAD_DIR / role / "iterations"` — must write to state worktree instead
  - `references/scripts/diagnostics.py` — `DIAGNOSTICS_DIR` path must be state worktree
  - `references/scripts/scan_index.py` — `rebuild()` search path for `scan-history.md`
  - `references/scripts/migrate_state_branch.py` — already written; validate it covers all 5 file types
  - `references/scripts/state_bus.py` — likely no changes needed; already complete
  - Boot scripts / start scripts — may need `state_bus.py init` before first cycle

- **Behavior changes**:
  - Main branch git log becomes cleaner (no iter-N.md / working-state.md churn)
  - Cross-agent merge conflicts on main for state files eliminated
  - `squid-squad` branch gets frequent small commits from all agents concurrently

- **Dependencies**:
  - `state_bus.py init` must run successfully before any cycle runs
  - `squid-squad` branch must exist (created by `state_bus.init()`)
  - Git worktree at `.squidsquad-state/` must be initialized per clone

---

## Side Effects

- **Risk 1**: `cycle.py log-iteration` writes to `SQUIDSQUAD_DIR/role/iterations/` — if this path changes to the state worktree, all callers that read iterations (statusline, `health_check`, `_get_cycle_number`) must also read from the worktree. Severity: HIGH. Mitigation: use a shared helper that resolves the correct base path.

- **Risk 2**: `diagnostics.py` hardcodes `DIAGNOSTICS_DIR = REPO_ROOT / ".squidsquad" / "diagnostics"`. After migration, writes go to this path but are not committed to main. If the commit path is also updated, the diagnostics file lands on the state branch. But `diagnostics.py report` generates a bug report from local files — this still works. Severity: MEDIUM. Mitigation: update `DIAGNOSTICS_DIR` to state worktree path.

- **Risk 3**: `model_router.py` also hardcodes `DIAGNOSTICS_DIR` (line 40). Severity: MEDIUM. Same mitigation.

- **Risk 4**: `.backlog-cache` write path is inside `tracker.py` — not yet located in detail. If it writes directly to `.squidsquad/.backlog-cache`, that path must be updated to the state worktree. Severity: LOW (cache only, can be regenerated).

- **Risk 5**: State branch gets concurrent commits from multiple agents. `state_bus.commit_and_push()` already handles this with a retry loop (3 attempts, pull-rebase between). This is the correct pattern. Severity: LOW.

---

## Edge Cases

- **Agent cold-start with no state branch**: `state_bus.read_file()` returns `None` if worktree doesn't exist. `cycle_pre._read_working_state` must handle `None` gracefully (it currently handles missing file with empty string — same behavior needed).
- **`_get_cycle_number` with empty state branch**: If `iterations/` doesn't exist in the worktree, returns 1. Already correct behavior.
- **scan_index.py rebuild with state files in worktree**: The rebuild path must check both `.squidsquad/` (for any files not yet migrated) and `.squidsquad-state/` (for migrated files). Or: post-migration, only check `.squidsquad-state/`.
- **Version bump commit in `_do_version_bump`**: Stages `CHANGELOG.md`, `SKILL.md`, `.squidsquad/config.md` directly via `git add --`. These files stay on main — no change needed here.
- **`.claude/` files**: `_is_state_file()` in `git_ops.py` already marks `.claude/` as ephemeral (excluded from feature branches). These are also gitignored — not a concern.

---

## Integration Risks

- **PR Flow gate** (Step 6 in PM CLAUDE.md): PM calls `git_ops.py pr-merge` which uses the working branch. No state-file involvement. No change needed.
- **Auto Merge verification in PR flow**: Verified in #3645. No state-branch dependency.
- **DM version bump**: Writes to `config.md`, `CHANGELOG.md`, `SKILL.md` — all stay on main. No change needed.
- **health_check.py**: Reads `.health` files (gitignored, local). No state-branch dependency.
- **boot_remote.py**: Reads agent directories. May need `state_bus.init()` before being useful on fresh clones.
- **Compose (references/scripts/compose.py)**: Writes to `.squidsquad/<role>/CLAUDE.md`. These stay on main (per issue spec). No change needed.

---

## Upgrade & Migration

- **New config values**: None. `state-branch` is already in `config.md` and `config.py`.
- **New files**: `.squidsquad-state/` worktree directory (gitignored). Already handled by `state_bus.init()` and `.gitignore` update in `state_bus.init()`.
- **Template changes**: `cycle_pre.py`, `cycle_post.py`, `git_ops.py`, `cycle.py`, `diagnostics.py`, `scan_index.py` all need code changes (not template changes).
- **Upgrade steps** (`/squidsquad-upgrade` must):
  1. Run `python references/scripts/migrate_state_branch.py` (copies existing state files to state branch).
  2. Run `python references/scripts/state_bus.py init` (creates worktree if not already there).
  3. After confirming migration, delete state files from main branch: `git rm -r .squidsquad/*/iterations/ .squidsquad/*/working-state.md .squidsquad/diagnostics/ .squidsquad/.backlog-cache` and push.
- **Graceful degradation**: If state branch doesn't exist, `state_bus.read_file()` prints an error and returns `None`. `cycle_pre` must fall back to direct filesystem reads (existing behavior) when the worktree is absent. This provides a clean upgrade path: old installs keep working, new installs use state branch.
- **Existing iteration history**: `migrate_state_branch.py` copies files — history is preserved on state branch. Git log of main loses the entries (they're not re-added to main). This is acceptable and desired.

---

## Open Questions

- **Q1**: Should the migration delete files from main automatically, or leave that as a manual step? **Why**: If files remain on main after migration, `git add -A` (used by `commit-push`) will keep staging them on main, defeating the purpose.
- **Q2**: Does `.backlog-cache` need to move? It's a cache file — it could simply be gitignored rather than moved to the state branch. **Why**: Moving a regenerable cache adds complexity with low benefit. Gitignoring it is simpler.
- **Q3**: Should `diagnostics/` move? It is written by `git_ops.py` and `tracker.py` during normal operations, not just by agents during cycle. Any call to `diagnostics.py log` would need to know about the state branch. **Why**: This is a wider change than the others and may not be worth it.
- **Q4**: What is the maintenance window strategy? All agents need to stop simultaneously for the migration to be clean. **Why**: An agent mid-cycle during migration will have stale file paths and may corrupt state.
- **Q5**: Does `scan-history.md` need to be readable by `scan_index.py` from the state branch? The rebuild path would change. Is the scan index even used in production right now? **Why**: If scan_index is not actively used, this is low risk.
- **Q6**: Should the state-branch path helper be added to `state_bus.py` or as a new utility module? **Why**: `cycle.py`, `cycle_pre.py`, `cycle_post.py`, `diagnostics.py` all need the same "resolve this path to state-worktree vs main" logic.

---

## Recommendation

**Feasible — proceed, but scope carefully.**

The infrastructure is already built (`state_bus.py`, `migrate_state_branch.py`). The wiring is missing in 4–6 scripts. The biggest risk is not technical but operational: the migration must happen when all agents are idle, and the file-delete-from-main step must immediately follow to prevent double-writes.

**Suggested minimum scope** (lowest risk, highest conflict reduction):
1. Move only `iterations/` and `working-state.md` — these are the highest-frequency conflict sources.
2. Gitignore `.backlog-cache` (simpler than migrating a regenerable cache).
3. Leave `diagnostics/` on main for now (too many write sites to update safely).
4. Leave `scan-history.md` for a follow-up (lower conflict frequency, `scan_index` dependency unclear).

**Suggested implementation order**:
1. Add path-resolution helper to `state_bus.py` or new `state_path.py`.
2. Update `cycle.py log-iteration` to write to state worktree.
3. Update `cycle_pre._read_working_state` and `_get_cycle_number` to read from state worktree.
4. Update `cycle_post._do_working_state_update` to write to state worktree.
5. Update `git_ops.commit_state` to route state-branch files to state worktree and commit via `state_bus`.
6. Update `cycle_post._do_commit_push` paths B and C to split state vs non-state files.
7. Run `migrate_state_branch.py`, delete state files from main, push.
8. Add `state_bus.py init` to boot/start scripts.
