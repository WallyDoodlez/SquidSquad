# FEAT-SKILL-005 Context — Add Agent Role Command

## Scope

New `add_role.py` script that clones the repo, configures a role, updates .local-config across all clones, and optionally boots the agent. Single command to go from "I want a QA agent" to "QA agent is running."

## Locked Decisions

- **New script**: `references/scripts/add_role.py` (separate from wizard.py and compose.py)
- **Git clone --local**: not git worktree. Full isolation, hardlinks for speed. Worktrees share index which conflicts with concurrent main commits.
- **Default target**: sibling directory named `ProjectName-<role>` (e.g., `SquidSquad-qa`, `SquidSquad-skill`). Configurable with `--target`.
- **Cross-clone sync**: after cloning, writes identical .local-config to ALL clones (source + existing + new). Atomic writes.
- **Post-setup only**: not integrated into wizard scaffold. Wizard prints a hint suggesting add_role commands.
- **.local-config format**: unchanged (`- **role**: /absolute/path`)
- **Boot optional**: `--boot` flag spawns agent via boot_remote.py. Default: clone and configure only.
- **Phases**: MVP (clone+configure+sync) → boot integration → PM sub-skill → register-existing/prune

## Dev Discretion

- Clone from local or remote URL (prefer local with --local)
- Lock file implementation for parallel add_role calls
- How to handle compose.py deploy in new clone (run automatically or hint to user)

## Side Effect Mitigations

- Check role exists in config.md before cloning
- Check target directory doesn't exist (error unless --force)
- Atomic .local-config writes (temp file + rename)
- Warning if source has uncommitted changes

## Upgrade Path

- Existing manual clones: `--register-existing <path>` to add to .local-config
- health_check.py and boot_remote.py need zero changes
- PM can call add_role.py when detecting missing agents (Phase 3)

## Out of Scope

- Wizard integration during initial scaffold (future)
- Auto-detection of how many clones to create
- Remote machine cloning (SSH)
