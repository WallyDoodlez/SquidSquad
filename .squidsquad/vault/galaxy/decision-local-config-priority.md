---
type: decision
tags: [config, clone-paths, multi-project, boot-remote, health-check]
created: 2026-04-25
updated: 2026-04-25
owner: skill-lead
status: active
confidence: high
source: code
links: []
---

# Project-Local Config Is Authoritative Over Global Clone Store

## Decision

`.squidsquad/.local-config` (project-scoped) takes priority over `~/.squidsquad/clones/` (global shared filesystem) when resolving agent clone paths.

## Context

`_parse_local_config()` in `boot_remote.py` and `health_check.py` originally checked the global `~/.squidsquad/clones/` directory first. This global store is shared across all SquidSquad-enabled projects on the machine. When a user works on multiple projects, the global store contains stale entries from other projects, causing cross-project agent boot (#2750).

## Rationale

- `.local-config` is inherently project-scoped (lives inside the project's `.squidsquad/` directory)
- The global store has no project-scoping mechanism — all entries are flat files keyed by role name
- The wizard (`wizard.py`) and `compose.py` write to `.local-config`, making it the primary source of truth
- The global store (`shared_fs.py write-clone`) is only populated via manual CLI calls

## Alternatives Considered

1. **Namespace global store by project** — adds complexity, requires migration
2. **Validate global paths against current project** — fragile, depends on config matching
3. **Remove global store entirely** — breaks users who rely on it as sole config

## Changelog

- 2026-04-25 — Created by skill-lead. Decision made in #2750 fix.
