# FEAT-PM-1328 Context — Skip blocked:human-action items in verification

## Scope

PM (Steps 5-6) and QA verification steps should check for `blocked:human-action` label before attempting verification. If present, skip silently with a one-line log note.

## Locked Decisions

- **Check label before verification**: If item has `blocked:human-action` label, skip verification entirely
- **Log but don't act**: Print one-line note `[🦑 HH:MM:SS] Skipping #N — blocked:human-action` and move on
- **No status change**: Don't bounce back to in-progress, don't create noise. Item stays at pending-test until human removes the label.
- **Both PM and QA**: Both verification sub-skills need the check

## Dev Discretion

- Where exactly to insert the check in the verification sub-skills (testing-and-verification.md for PM, QA equivalent)
- Whether to use `gh issue view` label check or `tracker.py get-labels`

## Out of Scope

- Creating the `blocked:human-action` label itself (already exists)
- Defining when to add/remove the label (that's a PM/human workflow decision)
