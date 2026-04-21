# FEAT-SKILL-1869 Context — 3-Branch Architecture + State Bus

## Scope

Redesign SquidSquad's git usage into 3 configurable branches. State files move to a dedicated orphan branch accessed via git worktree. Agents never touch main. Absorbs #1825 (configurable working branch).

## Locked Decisions (human decided)

- **3 branches, user-configurable names**:
  - `main` — project code only, SquidSquad never pushes here
  - `stag` (default, configurable) — working branch where agents commit code changes, PRs target here
  - `squid-squad` (default, configurable) — orphan branch, state bus for all agent state
- **Vault on state branch** — all vault content (BRIEFING.md, galaxy/, areas/, projects/, etc.) lives on the state branch. compose.py reads BRIEFING.md from state worktree path.
- **Worktree created at boot** — boot script creates `.squidsquad-state/` worktree if missing. Self-healing. No setup-time creation needed.
- **Periodic squash for size management** — every ~500 commits, squash state branch history. State doesn't need deep history. Cycle.py already cleans old iterations.
- **Setup CLI asks branch names** — two simple prompts with defaults:
  - "Working branch name? (default: stag):"
  - "State branch name? (default: squid-squad):"
- **Config.md stores branch names** — new `## Git Branches` section:
  - `Working Branch: stag`
  - `State Branch: squid-squad`
- **#1825 absorbed** — configurable working branch is part of this task, not separate.

## Dev Discretion (dev agent can choose)

- Squash trigger mechanism (commit count threshold, script, or manual)
- Worktree path name (`.squidsquad-state/` or similar)
- Whether to add `.squidsquad-state/` to `.gitignore` on the working branch
- State branch initial content structure
- Retry count for concurrent push conflicts (research suggests 3)
- How compose.py locates BRIEFING.md from the state worktree

## Side Effect Mitigations (required)

- Health check and watchdog scripts currently read gitignored local files — NO changes needed for those
- git_ops.py pull/push must be branch-aware — read Working Branch from config
- Boot scripts must checkout working branch, not main
- PRs must target working branch, not main
- State worktree push failures must not crash the agent cycle — log and retry next cycle
- If state branch doesn't exist yet (first boot), create the orphan branch automatically

## Upgrade Path (required)

- Existing installs: migration script creates orphan state branch, moves state files from main
- In-flight work preserved — working-state.md migrated to state branch
- Vault content migrated to state branch with full git history (cherry-pick or filter-branch)
- config.md gets new `## Git Branches` section with defaults
- Agents on old templates continue working on main until restarted with new templates
- Graceful degradation: if state branch missing, fall back to current behavior (state on working branch)

## Out of Scope

- Changing GitHub Issues tracker (stays as-is)
- Changing how templates/CLAUDE.md are composed
- Changing the Ralph Loop cycle structure
- Multi-repo support (agents in different repos)
