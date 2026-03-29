# FEAT-SKILL-024 Context — Offer to open planning artifacts in VS Code after Phase 3

## Scope
After Phase 3 (test plan) completes, PM prompts user to open TEST-PLAN.md in VS Code. Includes a "Never ask again" option that persists to config.md.

## Locked Decisions (human decided)
- **All planning artifacts**: Prompt after each artifact is created — RESEARCH.md (Phase 1), CONTEXT.md (Phase 2), TEST-PLAN.md (Phase 3). User initially chose TEST-PLAN.md only, then revised to all phases.
- **Light-mode intake**: Trivial feature, no deep research needed.

## Dev Discretion (dev agent can choose)
- Config key name (e.g. `Open Test Plan in Editor: yes/no`)
- Exact AskUserQuestion wording and option labels
- Whether to use `code` command directly or detect the user's editor

## Side Effect Mitigations (required)
- Check config preference before prompting — if disabled, skip silently
- Handle case where `code` command is not available (print path instead)

## Out of Scope
- Editor detection beyond VS Code
