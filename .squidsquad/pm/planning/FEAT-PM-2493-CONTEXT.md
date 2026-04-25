# FEAT-PM-2493 Context — Per-Agent Working Directories

## Scope

Setup wizard automatically creates per-agent repo clones during installation so multiple agents can operate concurrently without git collisions. Each agent gets its own full clone in a sibling directory.

## Locked Decisions (human decided)

- **Full clones, not worktrees**: Each agent gets its own full `git clone`. Same approach as current manual setup. No worktrees, no shared .git.
- **Sibling directories**: Clones live next to the primary repo (e.g., `../viewfinder-skill/`, `../viewfinder-qa/`). Short paths, easy to find.
- **Each clone is independent**: Each has its own `.squidsquad/` directory. No symlinks or junctions. Agents coordinate via git push/pull to the shared remote, not local filesystem.
- **.local-config stays with relative paths**: Use relative paths (e.g., `../viewfinder-skill`) so the file works across machines. No `~/.squidsquad/clones/` migration needed.
- **PM stays in primary repo**: PM is the coordination hub, runs in the original repo directory.

## Dev Discretion (dev agent can choose)

- Naming convention for sibling dirs (e.g., `<project>-<role>` or `<project>-squid-<role>`)
- How wizard detects the remote URL for cloning
- Whether to run compose.py deploy in each clone or copy from primary
- How to handle the case where sibling dirs already exist (idempotent)

## Side Effect Mitigations (required)

- **Existing installs**: Must not break single-repo setups. If no clones exist, agents fall back to primary repo (current behavior).
- **Git remote**: All clones must use the same remote URL. Wizard must detect and clone from the correct origin.
- **Boot scripts**: Start scripts must cd to the correct clone path (read from .local-config) before any git operations.
- **Health check**: health_check.py reads .local-config to find each agent's clone. Relative paths must resolve correctly from any clone.
- **Windows paths**: Sibling dirs may have spaces. All paths must be quoted in scripts.

## Upgrade Path (required)

- **New behavior**: wizard.py scaffold_install() creates clones for non-PM agents
- **New fields**: .local-config uses relative paths instead of absolute
- **Upgrade steps**: Existing single-repo installs can run a wizard command to create clones retroactively
- **Graceful degradation**: If clones don't exist, agents run in primary repo (current behavior, with collisions)

## Out of Scope

- Git worktrees (decided against — full clones are simpler and match current setup)
- ~/.squidsquad/clones/ migration (keeping .local-config with relative paths)
- Shared .squidsquad/ directory across clones (each clone is independent)
