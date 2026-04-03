# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- FEAT-SKILL-029: Obsidian memory layer (PARAG vault) -- currently in testing phase (vault-create)
- FEAT-SKILL-063: Self-improvement loop for quiet cycles -- in planning
- FEAT-SKILL-056/055: Public documentation overhaul and open-sourcing prep -- pending approval
- FEAT-SKILL-052/053: Agent role commands and PM auto-boot -- pending approval

## Recent Decisions

- Sub-skill architecture shipped (FEAT-SKILL-030) -- monolithic SKILL.md split into layered sub-skills with build-time composition
- Tracker Schema 3 shipped (FEAT-SKILL-051) -- individual files per bug/feature with INDEX.md
- Boot scripts switched to --dangerously-skip-permissions (recent commit)
- Architecture Version 1 established in config.md

## Human Preferences

- Never ship with failed test cases -- any TC failure sends work back to dev
- PM should not block on human input in Ralph Loop -- note availability and continue
- Always read tracker files fresh -- never answer from memory about pending items
- DM role is optional -- PM auto-activates delivery when DM is absent
- Git is the audit trail for all content

## Constraints & Blockers

- No automated test suite -- validation is manual SKILL.md review
- PR flow currently disabled
- 8 features shipped since last version bump (threshold is 10)
- FEAT-SKILL-050 (urgent cycle trigger) on hold

## Team State

- Active agents: skill-lead, pm/qa (DM optional, activated by PM as needed)
- Current version: 0.8.0
- Feature counter at FEAT-SKILL-063, Bug counter at BUG-SKILL-038
