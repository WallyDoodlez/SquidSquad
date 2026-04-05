---
type: area
tags: [conventions, style, architecture]
created: 2026-04-02
updated: 2026-04-05
owner: skill
status: active
confidence: medium
links: [squidsquad, decision-sub-skill-architecture]
---

## Overview

Code conventions and structural patterns used throughout the SquidSquad project. Since SquidSquad is primarily a markdown-and-shell skill (not a traditional codebase), conventions center on file organization, naming, agent communication protocols, and tracker formatting.

## Current State

- **File naming**: kebab-case for all markdown files, UPPER-CASE for index/status files (INDEX.md, CLAUDE.md, SKILL.md)
- **Feature/bug IDs**: `#XX` (GitHub Issue numbers, e.g. `#67`, `#93`)
- **Tracker format**: GitHub Issues with structured labels (type, priority, status, role) — migrated from markdown files in v0.9.0
- **Discussion protocol**: Append-only, timestamped, role-prefixed entries (`> [YYYY-MM-DD HH:MM] **role**: message`)
- **Git protocol**: Always `git pull --rebase` before work; tracker files are append-only; push after every completed work unit
- **Commit messages**: Role-prefixed (`skill: ...`, `pm: ...`, `dm: ...`)
- **Sub-skill sources**: Stored in `references/sub-skills/` organized by scope (common/, pm/, skill/, dm/)
- **Composed artifacts**: Generated with `DO NOT EDIT` headers and section markers
- **Atomic writes**: Write to `.tmp` then `mv` to avoid file locking races on Windows
- **Status bar integration**: Agents write phase and description to `current-state` files
- **PR flow**: Configurable (currently disabled); when enabled, creates branches per item
- **Vault operations**: vault-check Level 1 runs after every vault-create and vault-update; vault-update never deletes content

## History

- Tracker Schema 1-2: Monolithic features.md and bugs.md files
- Tracker Schema 3 (FEAT-SKILL-051): Split into individual files with INDEX.md
- Architecture Version 1 (FEAT-SKILL-030): Sub-skill architecture shipped, breaking monolithic SKILL.md into layered sub-skills
- GitHub Issues migration (#68, v0.9.0): Replaced all markdown tracker files with GitHub Issues; labels encode type/priority/status/role; `gh` CLI for all CRUD

## Related

- [[squidsquad]]
- [[decision-sub-skill-architecture]]

---

### Changelog

- 2026-04-02 -- Created by QA agent. Inferred conventions from codebase review during vault-create testing.
- 2026-04-03 -- Updated by skill-lead. Added vault operations convention (vault-check Level 1 after every write).
- 2026-04-05 -- Updated by dm. Fixed stale tracker references: FEAT-SKILL-NNN→#XX, markdown tracker→GitHub Issues, added GH Issues migration to History (#62).
