# FEAT-SKILL-039 Context — Slash command to change loop interval on the fly

## Locked Decisions

### D1: Scope
**Decision**: All agents immediately. Not just the current agent.
**Decided by**: Human
**How**: Current agent updates config.md + recreates its own cron immediately. Other agents pick up the change via a file-based signal (`.squidsquad/interval-override` or by re-reading config.md interval at cycle start). Each agent checks at the start of every cycle if the interval has changed, and re-schedules if so.

### D2: Bounds
**Decision**: Minimum 5 minutes. No explicit maximum (trust the user).
**Decided by**: Human
**Why**: Intervals under 5m risk git conflicts between agents pushing concurrently.

## Dev Discretion Areas

- Signal mechanism: could be a dedicated file, or agents just re-read config.md interval at cycle start and compare to their current cron interval
- Where the interval-check logic lives: Step 1 of Ralph Loop, or a separate pre-step
- Exact slash command syntax and help text
- Whether to support seconds/hours or just minutes

## Key Constraints

- Must work as a SKILL.md-defined slash command
- Must update config.md so the change persists across restarts
- Must use CronDelete + CronCreate to change the current agent's cron
- Minimum interval is 5 minutes
- Other agents must pick up the change within one cycle (no restart needed)
