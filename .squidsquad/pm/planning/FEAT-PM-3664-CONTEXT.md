# FEAT-PM-3664 Context — Move iterations and diagnostics to state branch

## Scope

Move ALL high-churn state files from main to the squid-squad state branch. Gitignore .backlog-cache. Wire cycle_pre.py, cycle_post.py, git_ops.py, cycle.py, diagnostics.py, model_router.py, and scan_index.py to use the state worktree. Run a stop-all → migrate → restart cutover.

## Locked Decisions (human decided)

- **Scope**: Full migration — iterations/, working-state.md, diagnostics/, scan-history.md all move to state branch
- **.backlog-cache**: Gitignore it (regenerable cache, not worth migrating)
- **Path helper**: Add to state_bus.py (centralize — it already owns the worktree)
- **Migration strategy**: Stop all agents → run migration → auto-delete from main → restart
- **Auto-delete**: Migration script removes state files from main automatically after copying to state branch

## Dev Discretion (dev agent can choose)

- Internal structure of the path-resolution helper in state_bus.py
- How to split state vs non-state files in git_ops.py commit paths
- Whether to add state_bus.init() to wrapper boot scripts or cycle_pre.py
- How to handle the diagnostics write sites (refactor to centralized path or update each caller)

## Side Effect Mitigations (required)

- All scripts that read/write state files must use the path helper — no hardcoded .squidsquad/ paths for state files
- cycle_pre must fall back to direct filesystem reads if worktree is absent (graceful degradation for old installs)
- state_bus.init() must be idempotent and run before first cycle
- Migration must verify all files copied before deleting from main
- Concurrent agent writes to state branch handled by state_bus.commit_and_push() retry loop (already implemented)

## Upgrade Path (required)

- /squidsquad-upgrade must: (1) run state_bus.py init, (2) run migrate_state_branch.py, (3) state files auto-deleted from main
- Old installs without state branch: cycle_pre falls back to main-branch reads
- .backlog-cache added to .gitignore

## Out of Scope

- .backlog-cache migration (gitignored instead)
- Changes to vault/ paths (stays on main)
- Changes to config.md, CLAUDE.md, SOUL.md paths (stay on main)
- Changes to references/ or tests/ paths (stay on main)
