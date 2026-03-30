# FEAT-SKILL-044 Context — Granular Status Phases With Item Names

## Scope
Expand the `current-state` phase vocabulary for all agent roles so the status bar telegraphs exactly what is happening and on which item. Add distinct phases for Feature Intake sub-steps. Include item IDs/names in every status write.

## Locked Decisions (human decided)
- **All agents**: applies to PM, dev, and future DM/QA — not just PM
- **Distinct phases**: Feature Intake phases get their own phase values (`researching`, `discussing`, `test-planning`), not all lumped under `planning`
- **Uniform styling**: no color-coding by phase category — text itself telegraphs status
- **Per-item updates**: during batch operations (e.g. verifying multiple bugs), status updates per-item, not as a summary

## Dev Discretion (dev agent can choose)
- Exact wording of status descriptions (as long as item ID is included)
- Whether to abbreviate long feature titles with `...` truncation
- How to handle phases that don't have a specific item (e.g. `pulling`, `health`) — keep as-is or add context

## Side Effect Mitigations (required)
- statusline.sh must handle all new phase values without breaking — unknown phases should fall through gracefully
- Existing phase values (`pulling`, `idle`, etc.) remain valid — this is additive

## Upgrade Path (required)
- N/A — template-only change. New installs get updated templates. Existing installs pick up new phases when agents are restarted with updated CLAUDE.md.

## Out of Scope
- Changing statusline.sh display format or colors
- Adding new status bar lines or layout changes
- DM/QA template creation (those are separate features)
