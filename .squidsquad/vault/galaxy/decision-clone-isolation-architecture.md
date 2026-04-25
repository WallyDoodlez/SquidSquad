---
type: decision
tags: [architecture, clones, isolation, security, core-philosophy]
created: 2026-04-25
updated: 2026-04-25
owner: pm-lead
status: active
confidence: high
source: conversation
links:
  - decision-pid-primary-liveness
  - decision-watchdog-supervisor
---

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
- **State branch** (`squid-squad`): shared coordination data — iterations, working state, health. Exists to separate agent state from code when branch workflow is enabled (feature branches for dev work)
- **Feature branches**: when branch workflow is on, dev work happens here before merging to main

## Why

Discovered 2026-04-25: agents with `--dangerously-skip-permissions` and global clone paths (`~/.squidsquad/clones/`) caused:
1. PM read and wrote files in another project's clone (viewfinder)
2. PM killed another project's agent processes
3. PM spawned agents into the wrong project's repo

Global clone paths are fundamentally unsafe for multi-project environments. Project-local paths eliminate cross-project contamination.

## Rules

1. Clone paths are **project-local** (`.squidsquad/.local-config`), never global
2. PM knows sibling locations via relative paths configured during setup
3. Human can override paths for existing clones (not all clones follow the default naming)
4. No agent reads or writes outside its own clone and the configured sibling clones
5. boot_remote.py, health_check.py, reboot_agent.py all resolve from `.local-config`

## Changelog

- 2026-04-25 — Created by pm-lead. Established after cross-project contamination incident. Human confirmed as core philosophy.
