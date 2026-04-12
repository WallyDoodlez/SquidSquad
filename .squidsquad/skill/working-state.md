# Working State

- **Task**: #442
- **Status**: in-progress
- **Started**: 2026-04-12 10:34
- **Quiet Cycle Counter**: 0

## Completed Steps
- Read CONTEXT.md
- Phase 1: Renamed GitHub labels (type:feature->type:task, type:bug->type:issue)
- Phase 2: Updated tracker.py (TYPE_LABELS, create_issue/create_task, CLI commands with backward-compat aliases)

## Remaining Steps
- Phase 3: Rename sub-skill files (feature-intake->task-intake, bug-filing->issue-filing)
- Phase 4: Update all CLAUDE.md templates and sub-skills prose
- Phase 5: Update SKILL.md, README.md
- Phase 6: Update wizard.py
- Phase 7: Rename open issue titles (FEAT:->TASK:, BUG:->ISSUE:)
- Phase 8: Update tests
- Phase 9: Recompose all agent CLAUDE.md files
- Phase 10: Run tests
- Transition to pending-test

## Key Decisions
- Backward-compat aliases kept (list-bugs->list-issues, create-bug->create-issue, etc.)
- Historical CHANGELOG entries left as-is
- Planning artifact filenames (FEAT-SKILL-XXX) left as-is
