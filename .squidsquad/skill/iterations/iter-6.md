# Skill Iteration 6

- **Date**: 2026-03-28 00:40
- **Bugs Fixed**: BUG-SKILL-003 (PS1 Unicode encoding), BUG-SKILL-004 (status line missing context window)
- **Features Progressed**: FEAT-SKILL-004 (PM no-code constraint) → Pending Test
- **Files Changed**: `.squidsquad/statusline.sh`, `.squidsquad/start-skill.ps1`, `.squidsquad/start-pm.ps1`, `SKILL.md`, `references/agent-instructions.md`, `.squidsquad/pm/CLAUDE.md`, `.squidsquad/skill/bugs.md`, `.squidsquad/skill/features.md`
- **Notes**: Fixed statusline to parse JSON stdin for context window %. Added UTF-8 encoding to all PS1 scripts and templates. Enforced PM no-code constraint across all PM instruction files.
