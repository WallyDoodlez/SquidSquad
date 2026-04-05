# SKILL Iteration 101

- **Date**: 2026-04-05 01:08
- **Bugs Fixed**: #71 (dev-agent.md bug fix transition missing --remove-label "status:open")
- **Features Progressed**: none
- **Tests**: passed (grep verified all gh issue edit calls in dev-agent.md, agent-instructions.md, live CLAUDE.md now have --remove-label)
- **Notes**: Only one line was affected (Step 2 bug fix complete). Other role templates don't have inline transitions — they use role-specific sub-skills which were already correct. gh issue close not needed in dev-agent since dev agents hand off to QA/PM for verification and closing.
