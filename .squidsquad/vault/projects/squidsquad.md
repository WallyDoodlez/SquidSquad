---
type: project
tags: [multi-agent, claude-code, skill, autonomous]
created: 2026-04-02
updated: 2026-04-05
owner: pm
status: active
confidence: medium
links: [decision-sub-skill-architecture, code-conventions]
---

## Overview

SquidSquad is a Claude Code skill that spins up autonomous AI agents -- one per dev role plus PM and QA -- that work on a codebase in parallel and coordinate through a shared `.squidsquad/` folder using markdown files and git. No message queues or orchestration servers. The project is at version 0.10.0 with Architecture Version 1. Tracker is GitHub Issues with structured labels. Repository: github.com/WallyDoodlez/SquidSquad.

Key goals:
- Autonomous multi-agent development via the "Ralph Loop" (pull, triage bugs, implement features, commit, push)
- Human-in-the-loop PM check-ins each cycle (non-blocking)
- Full traceability through git history
- Extensible role system (dev, designer, PM, QA, DM)

## Architecture

- **Tech stack**: Claude Code CLI instances, markdown-based coordination, git, bash/PowerShell boot scripts
- **Agent types**: PM (interactive), QA (autonomous), role leads (autonomous), Designer (optional, autonomous + interactive)
- **Coordination**: Shared `.squidsquad/` directory with per-role working state + GitHub Issues as tracker (bugs/features as labeled Issues)
- **Sub-skill system**: Main skill orchestrates; roles are independent sub-skills with common sub-skills auto-included (tracker protocol, Ralph Loop, context pressure, git protocol)
- **Composition**: Build-time concatenation of sub-skill sources from `references/sub-skills/` into `agent-instructions.md`

## Current Focus

- #67 — Integration test framework (in progress)
- #66 — Deterministic script layer (approved)
- #2 — Public-facing documentation overhaul (pending)
- #3 — Taking SquidSquad public as community-driven skill (pending)
- Multiple pending features: agent management (#5, #29), UX improvements (#7, #8, #10), vault phases (#17-#20)

## Related

- [[decision-sub-skill-architecture]]
- [[code-conventions]]

---

### Changelog

- 2026-04-02 -- Created by QA agent. Initial project note from codebase review during vault-create testing.
- 2026-04-04 -- Updated by skill-lead. Fixed stale version (0.8.0→0.9.0), removed Tracker Schema reference, updated coordination to GitHub Issues (#47).
- 2026-04-05 -- Updated by dm. Fixed version 0.9.0→0.10.0, replaced stale FEAT-SKILL-XXX focus items with current GitHub Issue numbers (#59).
