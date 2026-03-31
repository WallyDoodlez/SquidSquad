# FEAT-SKILL-046 Context — Bug Discussion Flow

## Scope
Change the PM bug filing process so that when a bug is discovered or reported, PM investigates the root cause and possible fixes, presents them to the human, and only files to the dev tracker after the human approves the approach.

## Locked Decisions (human decided)
- PM investigates and presents the fix before filing — not after
- Human gets a chance to discuss and steer the fix approach
- Only after human approval does the bug get filed to dev
- Works for all bug sources: human reports, test failures, QA findings

## Dev Discretion (dev agent can choose)
- How to structure the investigation presentation (bullet points, summary, etc.)
- Whether to use AskUserQuestion or plain text for the discussion
- How to handle cases where the human doesn't respond (non-blocking — PM can note "awaiting human input on fix approach" and continue the loop)

## Side Effect Mitigations (required)
- Bug filing must remain non-blocking for the Ralph Loop — if the human hasn't responded yet, PM continues cycling and revisits next cycle
- The investigation step should not be so heavy that it slows down the PM loop significantly
- Dev agent behavior unchanged — it still picks up Open bugs from its tracker as before

## Upgrade Path (required)
- N/A — PM template-only change. Existing installs get the new behavior when PM agent restarts with updated template.

## Out of Scope
- Changing how dev agents fix bugs (they still pick up Open bugs and fix them)
- Adding a formal "Bug Intake Process" with research subagents (keep it lightweight)
- Changing bug status flow (Open → Fixed → Closed stays the same)
