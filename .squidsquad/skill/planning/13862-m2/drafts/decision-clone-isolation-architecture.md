# Clone Isolation — Each Agent in Its Own Repo Clone

## Decision

Every SquidSquad agent runs in its own git clone of the target repository. This is a core architectural principle, not an optimization.

## Architecture

- **PM** runs in the primary repo (e.g., `SquidSquad/`)
- **Each dev agent** runs in a sibling clone (e.g., `SquidSquad-skill/`, `SquidSquad-qa/`, `SquidSquad-dm/`)
- **Clone paths** are configured project-locally in `.squidsquad/.local-config` — never in a global shared directory
- **Relative paths** are resolved against the repo root (e.g., `../SquidSquad-qa`)
- **Naming convention**: `<RepoName>-<suffix>` where suffix may be role name or user-assigned

## Branching

- **Main branch** (or user-configured target): all agents push code here
- **State branch** (`squid-squad`): RETIRED (operator, 2026-09-26, #14113; removal tracked in #14144). It used to hold iterations and working state apart from code. Event mode + harness-owned git made it redundant: agent state lives on main under `.squidsquad/<alias>/`, and `origin/squid-squad` had not moved since 2026-06-12. Do not reintroduce a separate state branch.
- **Feature branches**: when branch workflow is on, dev work happens here before merging to main

## Why

Discovered 2026-04-25: agents with `--dangerously-skip-permissions` and global clone paths (`~/.squidsquad/clones/`) caused:
1. PM read and wrote files in another project's clone (viewfinder)
2. PM killed another project's agent processes
3. PM spawned agents into the wrong project's repo

Global clone paths are fundamentally unsafe for multi-project environments. Project-local paths eliminate cross-project contamination.

## Local config takes priority over the global clone store

`.squidsquad/.local-config` (project-scoped) takes priority over `~/.squidsquad/clones/` (global shared filesystem) when `boot_remote.py`/`health_check.py`'s `_parse_local_config()` resolves agent clone paths — fixed in #2750 after the global store's stale cross-project entries caused cross-project agent boot. `.local-config` is the primary source of truth: the wizard (`wizard.py`) and `compose.py` write to it, while the global store is only populated via manual `shared_fs.py write-clone` CLI calls and has no project-scoping mechanism. Alternatives considered and rejected: namespacing the global store by project (adds complexity, needs migration), validating global paths against the current project (fragile, depends on config matching), and removing the global store entirely (breaks users who rely on it as sole config).

## Rules

1. Clone paths are **project-local** (`.squidsquad/.local-config`), never global
2. PM knows sibling locations via relative paths configured during setup
3. Human can override paths for existing clones (not all clones follow the default naming)
4. No agent reads or writes outside its own clone and the configured sibling clones
5. boot_remote.py, health_check.py, reboot_agent.py all resolve from `.local-config`

## Changelog

- 2026-04-25 — Created by pm-lead. Established after cross-project contamination incident. Human confirmed as core philosophy.
- **2026-09-26** — migrated to vault v2 (#13862).
