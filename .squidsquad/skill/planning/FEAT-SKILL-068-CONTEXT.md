# FEAT-SKILL-068 Context — Migrate Tracker to GitHub Issues

## Scope

Replace the internal markdown tracker with GitHub Issues. No fallback — SquidSquad already requires GitHub for git push/pull, so GitHub Issues is always available. One tracker, one protocol, simpler architecture.

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

- **GitHub Issues only — no markdown fallback**: SquidSquad requires GitHub (git push/pull). If you can push to GitHub, you can use GitHub Issues. No dual backend, no config toggle. Simpler architecture, one tracker protocol.
- **Startup permission check**: Verify `gh issue list` works at agent boot. If it fails, agent prints clear error ("gh Issues permission missing — run `gh auth refresh` with `repo` scope") and exits. Not a soft-fail — SquidSquad needs GitHub.
- **No setup question**: GitHub Issues is THE tracker. No choice needed.
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

## Deployment Procedure (required — atomic switchover)

The switch from markdown tracker to GitHub Issues is a **coordinated deployment event**, not just a code change. All agents communicate through the tracker — if one agent is on GH Issues and another is still reading markdown, they can't see each other's work.

**Switchover sequence:**
1. **Stop all agents** — kill all running agent sessions (skill, PM, DM, QA, designer)
2. **Run migration** — `/squidsquad-upgrade` creates GH Issues from all existing markdown items (bugs + features) with labels, Discussion history as comments, and correct status labels
3. **Verify migration** — spot-check that key items exist as Issues with correct labels
4. **Regenerate templates** — upgrade recomposes agent-instructions.md with GH Issues tracker protocol
5. **Restart all agents** — boot all agents fresh. They read the new templates and use GH Issues from cycle 1
6. **Verify coordination** — confirm agents can see each other's work (skill creates an item, PM can read it via `gh issue list`)

**Critical constraints:**
- All agents must be stopped BEFORE migration starts — no agent should be mid-cycle during the switch
- Migration must be atomic — all items migrated in one commit/push, all Issues created before any agent restarts
- Working state files cleared — agents start fresh (no stale references to old BUG-SKILL-NNN IDs)
- Old markdown tracker directories preserved as read-only archive (not deleted, but agents don't read them)

## Out of Scope

- GitHub Projects board integration (just Issues)
- Webhooks or GitHub Actions integration
- Issue templates (handled by FEAT-SKILL-055)
- Cross-repo issue tracking
