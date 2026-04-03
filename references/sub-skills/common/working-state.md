## Working State File

Maintain `.squidsquad/[ROLE]/working-state.md` to persist context across context window resets:

```markdown
# Working State

- **Task**: [#NUMBER, or "none"]
- **Status**: [in-progress / blocked / none]
- **Started**: [YYYY-MM-DD HH:MM]

## Completed Steps
- [what has been done so far]

## Remaining Steps
- [what still needs to be done]

## Key Decisions
- [important choices made during this task, with rationale]
```

- **Create/update** when starting a bug fix or feature implementation.
- **Update** as you complete sub-steps — this is your safety net if context resets.
- **Clear** (reset to `# Working State\n\n- **Task**: none\n- **Status**: none`) when a task is complete.
- **Read on startup** (Step 1c) to resume mid-task after a context reset.
- Before a **context pressure exit** (Step 1b), compact your current understanding into this file.
