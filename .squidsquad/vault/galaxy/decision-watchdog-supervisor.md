---
type: decision
tags: [architecture, watchdog, lifecycle, agent-management]
created: 2026-04-19
updated: 2026-04-19
owner: skill
status: active
confidence: high
source: conversation
links: []
---

## Context

Human directed (#1550) that all agent self-health logic be replaced by a standalone watchdog supervisor. Previously, each agent managed its own restarts (self-restart sentinel, context pressure watcher in boot script, PM health check + boot remote step).

## Content

Agent lifecycle is now centralized in `references/scripts/watchdog.py`:
- Runs every ~30s independently of any agent
- Checks all agent health via `health_check.py`
- Boots dead/stalled agents via `boot_remote.py`
- Handles context pressure restarts (kills agent between cycles)
- Handles template change restarts (detects CLAUDE.md mtime > session start)

Agents are "dumb workers" — they just run cycles. Boot scripts provide crash recovery only (exponential backoff, .stop sentinel). Agents no longer write .restart sentinels, poll context pressure for restart, or check template mtimes.

## Rationale

Scattered self-health logic across 5+ locations (boot script watcher, agent self-restart step, PM health check, PM boot remote, context pressure handling) was fragile and hard to reason about. Centralizing in one script makes lifecycle management deterministic, observable (single log file), and independent of agent availability.

## Related

_None currently._

---

### Changelog

- 2026-04-19 — Created by skill-lead. Documenting watchdog architecture decision from #1550.
