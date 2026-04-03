# FEAT-SKILL-068 Context — Migrate Tracker to GitHub Issues

## Scope

Replace the internal markdown tracker with GitHub Issues as the default tracker, while maintaining markdown as an opt-out fallback. The tracker protocol sub-skill supports both backends, selected by config during setup.

**In scope:**
- Dual backend tracker protocol (GH Issues default, markdown fallback)
- Setup asks user which tracker (default: GH Issues, opt-out: markdown)
- Label taxonomy (~25 labels across type, priority, status, role, design, severity)
- All agents use `gh` CLI for GH Issues backend
- Migration of existing markdown items to GH Issues via `/squidsquad-upgrade`
- Soft-fail at startup — warn if `gh` unavailable, offer markdown fallback
- Discussion entries become Issue comments (timestamped, role-signed)
- Status transitions via label changes
- Built as tracker-protocol sub-skill under FEAT-SKILL-030 architecture

## Locked Decisions (human decided)

- **Dual backend**: GH Issues is default, markdown tracker is opt-out fallback. Both backends maintained in the tracker protocol sub-skill. Config toggle: `Tracker: github-issues | markdown`.
- **Setup asks user**: During setup, ask which tracker. Default is GH Issues. User can choose markdown if no GitHub remote or preference.
- **Startup check — permission verification**: `gh` CLI is already available (required for git push/pull to GitHub). The check is whether `gh` has **Issues permissions** (authenticated + can create/edit/comment on Issues). During setup: verify with `gh issue list` — if it fails, warn and offer markdown fallback. Post-setup with `Tracker: github-issues`: hard crash if `gh issue list` fails — user must fix permissions (`gh auth refresh`) or switch to markdown in config.
- **Exclude closed issues**: All agent queries filter to open issues only. Shipped/closed items not scanned.
- **Issue numbers in working-state.md**: `Task: #42`. Short, stable, easy to look up.
- **Migration via /squidsquad-upgrade**: Detects markdown tracker, migrates items to GH Issues atomically. Part of the upgrade flow.
- **Skip-and-retry when GitHub unreachable**: Agents continue implementation work, skip tracker operations, catch up next cycle.
- **~25 labels**: type (bug/feature), priority (high/medium/low), status (8 states), role (5 roles), design (3 states), severity (3 levels), plus special labels.
- **Atomic migration**: Existing markdown items migrated with Discussion history as Issue comments. Markdown dirs preserved as archive after migration.

## Dev Discretion (dev agent can choose)

- Exact label names and colors
- How the tracker protocol sub-skill abstracts the backend (interface pattern)
- Migration script implementation details
- How to handle the `squidsquad` label if it already exists on the repo
- Comment format for Discussion entries as Issue comments
- Caching strategy for `gh issue list` results within a cycle

## Side Effect Mitigations (required)

- Every agent template's tracker sections must be rewritten for dual backend
- Planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) stay local in .squidsquad/ — only the tracker moves
- Feature Intake Process references feature IDs — must work with both Issue numbers and FEAT-SKILL-NNN format
- Vault (FEAT-SKILL-029) references are unaffected — vault is separate from tracker
- ID counters in config.md become obsolete for GH Issues backend but kept for markdown backend
- Ship counter stays in config.md for both backends

## Upgrade Path (required)

- `/squidsquad-upgrade` detects markdown tracker dirs
- If GH Issues selected: migrates items to Issues, preserves Discussion as comments, adds labels, archives markdown dirs
- If markdown selected: no change (backward compatible)
- Setup creates label taxonomy on repo for new installs
- `Tracker: github-issues` added to config.md

## Out of Scope

- GitHub Projects board integration (just Issues)
- Webhooks or GitHub Actions integration
- Issue templates (handled by FEAT-SKILL-055)
- Cross-repo issue tracking
