# FEAT-SKILL-462 Context — Adaptive Setup Questions

## Scope

During setup, ask 3 adaptive questions (target 3, max 5) to bootstrap project context. Q1 fixed, Q2+Q3 inferred from previous answers. Multi-part questions OK. Answers populate config.md, seed SOUL.md, and trigger capability sub-skill detection.

## Locked Decisions (human decided)

- **Q1 seeded from gh**: use `gh repo view` description as starting prompt ("I see this repo is [X]. Tell me more."). Q1 is never purely redundant.
- **SOUL.md seeding**: new `### Project Context` section. Keeps boundary clear between role identity (static) and project context (per-install).
- **Storage**: processed summary in config.md/SOUL.md + raw answers in install spec JSON for traceability.
- **Designer detection**: adaptive questions should detect design/UI needs and suggest designer agent. Not a separate preset — role selection within existing flow.
- **Setup instructions define WHAT to gather**: tech stack, test commands, external tools, conventions/constraints. Claude bundles related topics based on context.
- **Target 3, max 5 questions**: stop as soon as config.md + SOUL.md can be populated. More if answers are vague.
- **Each question narrows the space**: by Q3, ask about exact remaining blind spots, not generic questions.

## Dev Discretion (dev agent can choose)

- WIZARD.md prose for the adaptive questions step
- How to structure the install spec JSON field for raw answers
- config.md field names for project context
- How Claude detects designer needs from answer keywords

## Side Effect Mitigations (required)

- Skip-if-answered logic to avoid duplicate questions between Step 1b and Step 4
- 5-question hard cap enforced
- Graceful degradation if gh repo view fails (just ask Q1 without seed)
- SOUL.md seeding uses never-overwrite on upgrade (existing project context preserved)

## Upgrade Path (required)

- New WIZARD.md step 1b (prose change ~50 lines)
- wizard.py: extend install spec with project.domain_context, project.conventions
- SOUL.md template gains ### Project Context section (empty stub)
- Existing installs: upgrade doesn't retroactively ask questions. SOUL.md gets the empty section stub.

## Out of Scope

- Multi-preset support (one preset per install)
- Automated capability sub-skill installation (just detection and suggestion)
- Post-setup re-questioning
