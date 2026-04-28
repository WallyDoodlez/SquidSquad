# FEAT-PM-3664 Test Plan — Move iterations and diagnostics to state branch

## Test Cases

### TC-1: Path helper resolves state files to worktree
- **Precondition**: state_bus.init() has been run, worktree exists at .squidsquad-state/
- **Steps**: Call the path helper with state-file paths (iterations/, working-state.md, diagnostics/, scan-history.md)
- **Expected**: Returns paths under .squidsquad-state/ for state files, .squidsquad/ for non-state files (config.md, CLAUDE.md, vault/)
- **Verification**: Unit test asserting correct path resolution for each file type

### TC-2: cycle_post.py writes state files to state branch
- **Precondition**: Agent completes a cycle with state branch configured
- **Steps**: Run cycle_post.py for a role
- **Expected**: working-state.md and iter-N.md are committed to squid-squad branch, NOT to main
- **Verification**: `git log squid-squad --oneline -1` shows the iteration commit; `git log main --oneline -1` does NOT contain iteration files

### TC-3: cycle_pre.py reads state files from state worktree
- **Precondition**: State files exist on squid-squad branch, worktree initialized
- **Steps**: Run cycle_pre.py for a role
- **Expected**: cycle-input.json contains correct cycle number (from state branch iterations) and working state
- **Verification**: Cycle number matches max iter-N on squid-squad branch

### TC-4: diagnostics writes to state worktree
- **Precondition**: State branch configured, worktree exists
- **Steps**: Trigger a diagnostics.py log call (via model_router or tracker)
- **Expected**: diagnostic.jsonl written to .squidsquad-state/diagnostics/, not .squidsquad/diagnostics/
- **Verification**: File exists in state worktree, not in main worktree

### TC-5: scan-history.md writes to state worktree
- **Precondition**: Improvement scan runs
- **Steps**: Agent completes a scan cycle
- **Expected**: scan-history.md updated in state worktree
- **Verification**: `state_bus.read_file("<role>/scan-history.md")` returns updated content

### TC-6: scan_index.py rebuild finds files in state worktree
- **Precondition**: scan-history.md files exist in state worktree
- **Steps**: Run `python references/scripts/scan_index.py rebuild`
- **Expected**: Rebuilds index from state worktree paths
- **Verification**: Index contains entries from state-worktree scan-history.md files

### TC-7: .backlog-cache is gitignored
- **Precondition**: .gitignore updated
- **Steps**: Run `git status` after a tracker query that generates .backlog-cache
- **Expected**: .backlog-cache does not appear in git status
- **Verification**: `git check-ignore .squidsquad/.backlog-cache` returns 0

### TC-8: Migration copies all state files to state branch
- **Precondition**: State files exist on main, state branch configured
- **Steps**: Run `python references/scripts/migrate_state_branch.py`
- **Expected**: All state files (iterations/, working-state.md, diagnostics/, scan-history.md) copied to state branch
- **Verification**: `git show squid-squad:.squidsquad/<role>/iterations/` contains expected files

### TC-9: Migration auto-deletes state files from main
- **Precondition**: TC-8 completed successfully
- **Steps**: Check main branch after migration
- **Expected**: State files removed from main, committed, pushed
- **Verification**: `git ls-tree main .squidsquad/pm/iterations/` returns empty

### TC-10: Graceful degradation without worktree
- **Precondition**: State worktree does NOT exist (.squidsquad-state/ missing)
- **Steps**: Run cycle_pre.py
- **Expected**: Falls back to direct filesystem reads from .squidsquad/ (existing behavior), does not crash
- **Verification**: cycle-input.json generated successfully with fallback data

### TC-11: Main branch commits no longer contain state files
- **Precondition**: Full migration complete, agent runs a cycle
- **Steps**: Check git log on main after a cycle
- **Expected**: No iteration logs, working-state, diagnostics, or scan-history in the commit
- **Verification**: `git diff --name-only HEAD~1` contains no state file paths

### TC-12: Concurrent agent writes to state branch
- **Precondition**: Multiple agents configured, state branch active
- **Steps**: Two agents complete cycles simultaneously
- **Expected**: Both commits land on squid-squad branch (state_bus retry handles conflicts)
- **Verification**: Both agents' iteration logs exist on squid-squad branch

### TC-13: state_bus.init() is idempotent
- **Precondition**: Worktree already exists
- **Steps**: Run state_bus.py init again
- **Expected**: No error, no duplicate worktree, existing data preserved
- **Verification**: Exit code 0, worktree still functional

## Smoke Tests

- [ ] `python tests/run_tests.py` passes after migration
- [ ] All agents boot and complete one cycle successfully
- [ ] `git log main --oneline -5` shows no state file commits
- [ ] `git log squid-squad --oneline -5` shows iteration commits from all agents
- [ ] `.backlog-cache` not tracked by git

## Regression Risks

- State files disappearing during cutover — mitigated by stop-all strategy
- Cycle number regression (double-counting from both branches) — mitigated by deleting from main
- diagnostics.py callers using hardcoded paths — must all be updated
- scan_index.py rebuild failing — search path must be updated
