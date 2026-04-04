---
type: project
tags: [multi-agent, claude-code, skill, autonomous]
created: 2026-04-02
updated: 2026-04-02
owner: pm
status: active
confidence: medium
links: [decision-sub-skill-architecture, code-conventions]
---

## Overview

SquidSquad is a Claude Code skill that spins up autonomous AI agents -- one per dev role plus PM and QA -- that work on a codebase in parallel and coordinate through a shared `.squidsquad/` folder using markdown files and git. No message queues or orchestration servers. The project is at version 0.8.0 with Tracker Schema 3 and Architecture Version 1. Repository: github.com/WallyDoodlez/SquidSquad.

Key goals:
- Autonomous multi-agent development via the "Ralph Loop" (pull, triage bugs, implement features, commit, push)
- Human-in-the-loop PM check-ins each cycle (non-blocking)
- Full traceability through git history
- Extensible role system (dev, designer, PM, QA, DM)

## Architecture

- **Tech stack**: Claude Code CLI instances, markdown-based coordination, git, bash/PowerShell boot scripts
- **Agent types**: PM (interactive), QA (autonomous), role leads (autonomous), Designer (optional, autonomous + interactive)
- **Coordination**: Shared `.squidsquad/` directory with per-role tracker files (bugs/, features/, working-state.md)
- **Sub-skill system**: Main skill orchestrates; roles are independent sub-skills with common sub-skills auto-included (tracker protocol, Ralph Loop, context pressure, git protocol)
- **Composition**: Build-time concatenation of sub-skill sources from `references/sub-skills/` into `agent-instructions.md`

## Current Focus

- FEAT-SKILL-029: Obsidian memory layer (PARAG vault with COG retrieval) -- Pending Test
- FEAT-SKILL-063: Self-improvement loop for quiet cycles -- Planning
- FEAT-SKILL-056: Public-facing documentation overhaul -- Pending
- FEAT-SKILL-055: Taking SquidSquad public as community-driven skill -- Pending
- Multiple pending features around agent management (052, 053, 061) and UX improvements (057, 060)

## Related

- [[decision-sub-skill-architecture]]
- [[code-conventions]]

---

### Changelog

- 2026-04-02 -- Created by QA agent. Initial project note from codebase review during vault-create testing.
