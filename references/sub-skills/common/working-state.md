---
slot: instructions
ordinal: 10
---

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
- **Clear** when a task is complete — reset Task and Status to `none`. (The event cursor is harness-owned in `.squidsquad/.event-state.json`, not stored here; see [[cursor-management]].)
- **Keep it under ~8KB (#13562)** — this file is a lean snapshot, not a journal. Anything larger is tail-truncated in your cycle input behind a `[TRUNCATED (#13562)]` marker (only the newest 8KB reaches you), and an oversized write draws a warning. History belongs in git and your iteration logs — never append session journals here; rewrite the file down to the lean shape above instead.
- **Read on startup** (Step 1c) to resume mid-task after a context reset.
- Before a **context pressure exit** (Step 1b), compact your current understanding into this file.
