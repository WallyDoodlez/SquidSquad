## BUG-SKILL-036 — SKILL.md description is a slogan instead of describing what the skill does

- **Severity**: Low
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: The SKILL.md YAML frontmatter `description` field says `"Your AI dev team that coordinates through markdown, not meetings."` — this is a marketing slogan, not a description of what the skill does. It should describe the skill's actual function: orchestrating a multi-agent development team with setup, workflow coordination, and role management.
- **Steps to Reproduce**:
  1. Read SKILL.md line 3
- **Expected**: Description explains what this skill does (e.g. "Orchestrates a multi-agent AI development team — handles setup, workflow coordination, role management, and serves as the foundation for role-specific sub-skills.")
- **Actual**: `"Your AI dev team that coordinates through markdown, not meetings."`

### Discussion

> [2026-03-31 02:30] **pm/qa**: Filed from human report. Human noted the description should describe what the skill actually does, not be a slogan. This is especially important as SquidSquad evolves toward a multi-skill architecture (FEAT-030) where the main skill is the orchestrator and roles become sub-skills.
> [2026-03-31 02:35] **skill-lead**: Fixed — changed SKILL.md description from slogan to functional description: "Orchestrates a multi-agent AI development team — handles setup, workflow coordination, role management, and autonomous dev cycles." Status → Fixed.
> [2026-03-31 03:00] **pm/qa**: Verified — SKILL.md description is now functional, not a slogan. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
