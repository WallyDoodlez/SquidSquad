# FEAT-SKILL-035 Context — Delivery Manager (DM) Role

## Scope
Introduce a Delivery Manager (DM) as a hardcoded agent role. DM owns the full delivery pipeline: picks up features at `Pending Ship`, writes user-facing docs, CHANGELOG entries, performs version bumps, creates git tags/releases, then marks `Shipped`. PM is completely uninvolved in delivery — it only detects Shipped status and moves on.

## Locked Decisions (human decided)
- **Single shared tracker**: DM reads from the same `features.md`/`bugs.md` as dev and PM. No separate `dm/` tracker directory.
- **Audience-based doc split**: Dev writes technical docs (API docs, code comments, architecture notes). DM writes user-story docs (user guides, product descriptions, CHANGELOG, "what's new", getting-started — things that help people understand and use the product, not in-depth technical details).
- **PM scans for Shipped, does nothing**: PM detects Shipped status but has zero delivery responsibilities. No aggregating, no version bumps, no CHANGELOG work.
- **DM owns full delivery pipeline**: CHANGELOG entries, version bump, git tag, release creation — everything currently in PM's Step 6c moves to DM.
- **delivery:skip tag**: PM can tag features `delivery: skip` when marking Pending Ship. DM auto-ships those with a "no delivery work needed" note.
- **Same loop interval**: DM uses the shared interval from config.md (currently 30m). Quiet cycle optimization handles idle periods.
- **Sequential implementation**: FEAT-035 (DM) ships first, then FEAT-043 (QA split).

## Dev Discretion (dev agent can choose)
- DM Ralph Loop step ordering and structure (modeled after existing dev/PM templates)
- DM statusline layout details (following existing patterns)
- Boot script implementation details
- How DM discovers `delivery:skip` tagged items (Discussion note format, field, etc.)
- DM working-state.md structure

## Side Effect Mitigations (required)
- PM and DM templates must ship simultaneously — partial rollout breaks the lifecycle
- PM's version bump logic (Step 6c) must be fully removed and transferred to DM
- PM's PR Flow handling (Step 6b) must set `Pending Ship` instead of `Shipped` for merged PRs
- Dev template Step 8 updated: dev writes tech docs only, adds delivery notes to Discussion for DM
- statusline.sh must include DM health icon in PM's health row
- Fallback: if DM doesn't exist (non-upgraded install), PM should treat `Pending Ship` as `Shipped` to avoid stalled features

## Upgrade Path (required)
- Create `.squidsquad/dm/` directory with CLAUDE.md bootstrapper, working-state.md
- Generate DM template in `.squidsquad/templates/dm-agent.md`
- Generate boot scripts (`start-dm.sh`, `start-dm.ps1`)
- Copy `references/hints-dm.txt` to `.squidsquad/`
- Add DM to agents section in config.md (hardcoded like PM, not a dev agent)
- Regenerate PM template (remove version bump logic, update Pending Test → Pending Ship flow)
- Regenerate dev template (tech docs only, delivery notes in Discussion)
- Regenerate statusline.sh (DM health icon)
- Schema migration: Schema 1 → 2, add `Pending Ship` status. No data migration needed.

## Out of Scope
- FEAT-SKILL-043 (QA split) — ships after DM
- DM filing features to its own separate tracker (uses shared tracker)
- DM creating PRs (pushes directly to main like PM)
- GitHub Issues routing to DM (future enhancement)
