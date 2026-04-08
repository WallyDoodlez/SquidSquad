# FEAT-309 Context — tracker.py pre-transition guard

## Scope
Add an unread-feedback guard to tracker.py's `transition()` function. Before allowing `in-progress → pending-test` or `pending-test → pending-ship`, check if there are unread PM/QA/human comments newer than the transitioning role's last comment. If yes, block the transition.

## Locked Decisions (human decided)
- Guard applies to both `in-progress → pending-test` AND `pending-test → pending-ship`
- Override is a bare `--force` flag (no reason string required)
- Detection logic: fetch issue comments, find last comment by the transitioning role, check if any PM/QA/human comments exist after it

## Dev Discretion
- How to determine the "transitioning role" (parse from CLI args, or require a `--role` param)
- How to identify PM/QA/human comments vs agent comments (parse the `**role**:` prefix, or use GitHub author metadata)
- Error message wording
- Whether to cache the comment fetch or always hit the API

## Side Effect Mitigations
- Must not slow down transitions that don't need the guard (all other transitions are unaffected)
- `--force` must be a simple flag, not a positional arg change
- Guard must handle edge case: issue with zero comments (no feedback = allow transition)

## Out of Scope
- Guarding other transitions (only the two specified)
- Changing the comment format or role identification system
- Notification system for unread comments
