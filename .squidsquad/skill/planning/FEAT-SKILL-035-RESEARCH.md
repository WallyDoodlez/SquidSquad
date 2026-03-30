# FEAT-SKILL-035 Research — Delivery Manager (DM) Role

## Summary

This feature introduces a Delivery Manager (DM) as a hardcoded agent role (always present, like PM) responsible for all client-facing, non-code work: README updates, CHANGELOG entries, configuration changes, migration/upgrade steps, and delivery packaging. The DM picks up features at a new "Pending Ship" status (inserted between "Pending Test" and "Shipped") and ensures everything a user needs is ready before marking the feature Shipped. The human's vision is a four-role squad: PM (talks), QA (tests), DM (ships/configures), Dev (builds) — with FEAT-SKILL-043 (QA split) completing the picture.

The feature is feasible but has significant cross-cutting impact. It touches the tracker schema (new status value), every agent template (PM stops shipping, dev workflow unchanged, DM gets its own Ralph Loop), the setup flow (hardcoded DM generation), the upgrade flow (add DM to existing installs), the statusline (new health icon, DM-specific segments), boot scripts, config, and the version bump logic. The primary risk is the schema change: inserting "Pending Ship" between "Pending Test" and "Shipped" means existing features currently at "Pending Test" need a clear transition rule, and all code that checks for "Shipped" status must also be aware of the new intermediate state.

The DM role should be designed with FEAT-SKILL-043 in mind. Currently PM handles both verification (QA) and shipping (DM). After FEAT-035, PM still verifies but DM ships. After FEAT-043, QA verifies and DM ships, with PM only coordinating. The DM template should therefore NOT depend on PM-specific behaviors — it should read tracker statuses directly, same as dev agents do.

## Impact Analysis

- **Files touched**:
  - `SKILL.md` — Schema Changelog (new status value), Feature Format example, status flow line, Feature Lifecycle description, architecture diagram, roles table, file structure diagram, setup Steps 4-5 (generate DM template + bootstrapper + boot scripts), setup Step 6 (seed DM tracker files), setup Step 8 (commit message), setup Step 9 (launch instructions), upgrade flow (add DM agent to upgrade fan-out)
  - `references/agent-instructions.md` — new Template 3: DM Agent
  - `references/statusline.sh` — DM-specific status bar segments (similar to dev but with Pending Ship focus), DM health icon in PM's health row
  - `references/hints-dm.txt` — new hint pool for DM agent
  - `.squidsquad/config.md` — add DM to agents list, add `FEAT-DM` and `BUG-DM` counters
  - `.squidsquad/pm/CLAUDE.md` (template) — PM Step 6 changes: `Pending Test` -> `Pending Ship` instead of `Pending Test` -> `Shipped`
  - `.squidsquad/templates/pm-agent.md` — same PM behavioral change
  - `CHANGELOG.md` — new entry
  - `README.md` — document DM role
  - New files: `.squidsquad/dm/CLAUDE.md`, `.squidsquad/dm/bugs.md`, `.squidsquad/dm/features.md`, `.squidsquad/dm/iterations/`, `.squidsquad/dm/working-state.md`, `.squidsquad/start-dm.sh`, `.squidsquad/start-dm.ps1`, `.squidsquad/templates/dm-agent.md`

- **Behavior changes**:
  - Feature status flow becomes: `Pending` -> `Planning` -> `Approved` -> `In Progress` -> `Pending Test` -> `Pending Ship` -> `Shipped`
  - PM/QA (or future QA) no longer marks features `Shipped` — marks them `Pending Ship` instead
  - DM picks up `Pending Ship` items, does delivery work (docs, config, migration), then marks `Shipped`
  - Version bump counter increment moves from PM's "mark Shipped" to DM's "mark Shipped" (or stays with PM reading the Shipped status — design decision needed)
  - DM can file features (proactively, when it spots client-facing gaps) and bugs (all agents can)
  - DM does NOT approve features — only PM does (with human confirmation)

- **Dependencies**:
  - Schema version bump (Schema 1 -> Schema 2) to add `Pending Ship` status
  - No hard dependency on FEAT-SKILL-043 (QA split), but design must accommodate it
  - Boot script infrastructure (heartbeat, current-state, statusline) already exists and is reusable

## Side Effects

- **Risk 1**: Existing features at `Pending Test` status may stall if PM changes behavior before DM exists — Severity: H — Mitigation: Deploy PM template change and DM simultaneously in a single version bump. Never ship PM-side change without DM agent being available.

- **Risk 2**: Version bump logic currently lives in PM Step 6c. PM increments `Shipped Since Last Bump` when marking items Shipped. If DM now marks items Shipped, PM's counter logic breaks or fires at the wrong time — Severity: H — Mitigation: Move the `Shipped Since Last Bump` increment to whoever marks the item Shipped (DM). OR: keep it in PM but have PM scan for newly-Shipped items each cycle (already partially does this). The latter is simpler since PM already reads all trackers. Recommend: PM continues to own version bump logic, scanning for items that transitioned to Shipped since last cycle.

- **Risk 3**: Auto versioning checks for "zero open bugs" across all trackers. DM will have its own `bugs.md`. Open DM bugs would now block version bumps — Severity: M — Mitigation: This is actually correct behavior (DM bugs should block shipping). Document it. Ensure DM's `bugs.md` is included in the "all agent bug trackers" scan.

- **Risk 4**: PR Flow interactions — when PR Flow is enabled, dev agents create PRs. PM monitors PRs and updates status. Adding `Pending Ship` means PM should update merged PRs to `Pending Ship` (not `Shipped`). If PM's PR monitoring logic hardcodes `Shipped`, it will skip the DM step — Severity: M — Mitigation: Update PM's Step 6b to set status to `Pending Ship` instead of `Shipped` when a PR is merged.

- **Risk 5**: GitHub Issues ingestion — PM closes GitHub Issues when items are Shipped. If DM marks Shipped, PM needs to detect that transition (which it already does by scanning trackers). No change needed in the issue-closing logic itself, but PM must scan for DM-shipped items — Severity: L — Mitigation: PM's existing tracker scan in Steps 5-6 should already catch newly-Shipped items regardless of who changed the status.

- **Risk 6**: DM's delivery work (README, CHANGELOG, config changes) overlaps with what dev agents currently do in Step 8 ("Update docs") of their template. Dev agents are instructed to update README and SKILL.md when changes affect user-facing behavior. With DM owning this, devs should stop doing it — Severity: M — Mitigation: Update dev template Step 8 to say "Skip doc updates if DM role is present — DM handles all user-facing documentation." Or remove Step 8 from dev template entirely and always route through DM. Recommend: dev agents stop updating docs; they focus purely on implementation code.

## Edge Cases

- **DM stalls (heartbeat goes stale)**: PM's health check (Step 7) already detects stalled agents via heartbeat branches. PM should log a warning. Features will pile up at `Pending Ship`. No automatic fallback — human must restart DM. Consider: if DM is stalled for >N cycles, PM could escalate with a prominent warning rather than a quiet log entry.

- **No Pending Ship items**: DM's Ralph Loop has nothing to do. This is a quiet cycle — same pattern as dev agents with no approved features. DM skips logging and committing, status bar shows idle hints.

- **Internal-only changes that don't need delivery packaging**: Some features may be purely internal (e.g., refactoring an agent template, fixing an internal bug). These still go through DM for a quick "no delivery work needed" pass. DM should have a fast-track option: if a Pending Ship item has no user-facing impact (e.g., tagged `internal` or dev agent self-determines), DM marks it Shipped immediately with a Discussion note "No delivery work needed." Design decision: who decides if something is internal-only? Recommend: PM tags the feature with a `delivery: none` flag when marking Pending Ship, DM auto-ships those.

- **DM and dev both editing README/CHANGELOG simultaneously**: Git conflicts. DM edits docs, dev edits code, both push. Standard git conflict resolution applies (pull --rebase, resolve). Tracker files already handle this pattern. Recommend: DM should always pull before starting work (already part of Ralph Loop Step 1).

- **Feature has no acceptance criteria for delivery**: DM needs to know what delivery work is expected. If the feature tracker entry doesn't specify delivery requirements, DM has to guess. Recommend: add a `Delivery Criteria` field to features (or have PM include delivery notes when marking Pending Ship).

- **Multiple features at Pending Ship simultaneously**: DM should process them one at a time (highest priority first), same as dev agents process Approved features. Working state file handles crash recovery.

- **DM files a feature that creates circular dependency**: DM spots a client-facing gap, files a feature. PM approves it. Dev implements it. It comes back to DM for delivery. This is the correct flow — no circularity. But if DM files a feature to its own tracker (e.g., "DM needs to update migration docs"), who implements it? DM itself, since it's delivery work. DM should be able to self-assign delivery-only features.

## Integration Risks

- **PM interaction**: PM currently owns the entire Pending Test -> Shipped transition. After this feature, PM owns Pending Test -> Pending Ship, and DM owns Pending Ship -> Shipped. If PM and DM are out of sync (different cycle intervals, different context pressure thresholds), there could be delays. Mitigation: both read from the same tracker files via git, so eventual consistency is guaranteed within one cycle interval.

- **FEAT-SKILL-043 (QA split)**: When QA becomes its own agent, QA will own the Pending Test -> Pending Ship transition (instead of PM). The DM template should not reference "PM" specifically in its logic — it should just look for `Pending Ship` items in any agent's features.md. This makes the DM template QA-agnostic. The transition responsibility chain becomes: QA verifies -> marks Pending Ship -> DM packages -> marks Shipped.

- **Version bump (auto versioning)**: The bump is triggered by `Shipped Since Last Bump >= Ship Threshold` with zero open bugs. Currently PM increments the counter in Step 6c when it marks items Shipped. Options: (A) DM increments the counter when it marks Shipped, (B) PM scans for newly-Shipped items each cycle and increments. Option B is simpler and doesn't require DM to know about version bump logic. Option B also survives the QA split cleanly — PM always owns version bumps. Recommend Option B.

- **PR Flow**: When PR Flow is enabled, merged PRs currently trigger `Shipped` status. This needs to change to `Pending Ship` so DM can do delivery work even for PR-merged features. DM may need to create its own PRs for delivery work (doc changes) — or DM pushes directly to main like PM does (since delivery work is non-code). Recommend: DM pushes directly to main (like PM), only dev agents use PR flow.

- **Statusline**: DM needs its own status bar display. When running as DM, the statusline should show: DM role label, Pending Ship count (like dev's backlog pulse), active task, context/timer. The PM statusline's health icons row needs to include DM (currently iterates over `pm $AGENTS` — DM would need to be added to this list, either as a hardcoded addition or by reading a "hardcoded roles" config value).

- **GitHub Issues ingestion**: No direct impact on DM. PM ingests issues and routes to dev agents. DM only picks up work at Pending Ship stage. However, if a GitHub Issue is purely a documentation request, PM could route it as a DM feature rather than a dev feature. This is a future enhancement, not required for initial DM implementation.

## Upgrade & Migration

- **New config values**:
  - `Dev Agents` line unchanged (DM is not a dev agent — it's hardcoded like PM)
  - New `Hardcoded Roles` entry or expand `PM/QA` line to `PM/QA, DM` — OR: add a `## Delivery Manager` section. Recommend: add `- **DM**: always present` under the Agents section, mirroring the PM/QA line.
  - New ID counters: `BUG-DM: 0`, `FEAT-DM: 0`

- **New files**:
  - `.squidsquad/dm/CLAUDE.md` — bootstrapper (same pattern as dev/pm)
  - `.squidsquad/dm/bugs.md` — empty tracker
  - `.squidsquad/dm/features.md` — empty tracker
  - `.squidsquad/dm/iterations/` — empty directory
  - `.squidsquad/dm/working-state.md` — empty
  - `.squidsquad/templates/dm-agent.md` — full DM Ralph Loop template
  - `.squidsquad/start-dm.sh` — boot script
  - `.squidsquad/start-dm.ps1` — boot script
  - `references/hints-dm.txt` — DM hint pool

- **Template changes**:
  - `references/agent-instructions.md` — new Template 3: DM Agent added
  - PM template (Template 2) — Step 6 updated: `Pending Test` -> `Pending Ship` instead of `Shipped`. Step 6b (PR monitoring) updated: merged PRs -> `Pending Ship`.
  - Dev template (Template 1) — Step 8 (Update docs) removed or conditioned on DM presence. Step 3 acceptance criteria note: "DM handles user-facing docs after your implementation."
  - Schema Changelog — Schema 2 documented with `Pending Ship` addition and migration instructions.

- **Upgrade steps** (`/squidsquad-upgrade` must):
  1. Detect missing DM role (no `.squidsquad/dm/` directory).
  2. Create `.squidsquad/dm/` directory with CLAUDE.md bootstrapper, empty trackers, iterations dir.
  3. Generate `.squidsquad/templates/dm-agent.md` from Template 3.
  4. Generate `.squidsquad/start-dm.sh` and `.squidsquad/start-dm.ps1`.
  5. Copy `references/hints-dm.txt` to `.squidsquad/hints-dm.txt`.
  6. Add `BUG-DM: 0` and `FEAT-DM: 0` to config.md counters.
  7. Add DM to agents section in config.md.
  8. Regenerate PM template with updated Step 6 behavior.
  9. Regenerate dev template with updated Step 8 behavior (if applicable).
  10. Regenerate statusline.sh.
  11. Schema migration: update status flow documentation. No data migration needed — existing `Shipped` items stay Shipped, existing `Pending Test` items continue through the new flow naturally.
  12. Bump schema version to 2.

- **Graceful degradation**: If a user doesn't upgrade, they have no DM. PM continues to mark features Shipped directly (old behavior). No breakage. Features work exactly as before. The only issue is if they pull code from a repo where someone else has already implemented FEAT-035 and features are stuck at `Pending Ship` with no DM to process them — in that case, PM's verification step would see `Pending Ship` as an unknown status and ignore it. Recommend: PM template should have a fallback: if it encounters `Pending Ship` items and DM doesn't exist (no `dm/` directory), treat them as `Pending Test` items that PM can ship directly.

## Open Questions

- **Q1**: Should DM have its own tracker directory (`dm/bugs.md`, `dm/features.md`) or should it work exclusively off dev agents' trackers (scanning for `Pending Ship` status)? — **Why**: If DM has its own trackers, features filed TO DM (e.g., "update README") live separately from dev features. But DM's primary job is processing dev agent features at Pending Ship. Having two places to look (own tracker + all dev trackers) adds complexity. Recommend: DM scans dev agent trackers for Pending Ship items (primary workflow) AND has its own tracker for DM-originated work (doc requests, config changes filed directly to DM).

- **Q2**: Should the dev agent template's Step 8 ("Update docs") be removed, made conditional, or left as-is? — **Why**: If dev agents continue updating docs AND DM also updates docs, there will be redundant or conflicting doc changes. If dev agents stop updating docs entirely, features that ship to Pending Test without doc notes will require DM to figure out what changed. Recommend: Dev agents stop doing doc updates. Instead, they append a "Delivery notes" section to the Discussion when marking Pending Test, describing what user-facing changes were made.

- **Q3**: Who increments `Shipped Since Last Bump`? — **Why**: If DM increments it, DM needs to understand auto-versioning. If PM scans for newly-Shipped items, PM keeps all version logic. Getting this wrong means version bumps fire at wrong times or not at all. Recommend: PM scans for Shipped transitions each cycle (Option B from Integration Risks).

- **Q4**: Should `Pending Ship` be skippable for internal-only features? — **Why**: Features like "refactor agent template internals" don't need delivery packaging. Forcing DM to process them wastes cycles. But adding a skip mechanism adds complexity. Recommend: PM can add a `delivery: skip` tag when marking Pending Ship. DM auto-ships those with a "no delivery work needed" Discussion note.

- **Q5**: What is DM's Ralph Loop interval? Same as dev agents, same as PM, or independent? — **Why**: DM's work is bursty (nothing until features reach Pending Ship, then potentially heavy). A long interval is fine for quiet times but delays shipping when work arrives. Recommend: same interval as other agents (from config.md), since the quiet cycle optimization already handles idle periods efficiently.

- **Q6**: How does DM interact with the CHANGELOG? Currently PM adds CHANGELOG entries during version bumps. DM is supposed to own CHANGELOG entries as part of delivery packaging. Should DM write per-feature CHANGELOG entries and PM aggregates them at bump time? Or should DM write the full CHANGELOG section? — **Why**: If both PM and DM write CHANGELOG, there will be conflicts. Recommend: DM writes per-feature CHANGELOG entries as Discussion notes or a dedicated section. PM's version bump collects them into the formal CHANGELOG section. This keeps PM as the version-bump orchestrator.

- **Q7**: Should FEAT-SKILL-035 and FEAT-SKILL-043 be implemented together or sequentially? — **Why**: They are complementary (PM splits into PM+QA, PM+DM emerges). Implementing them together risks a very large change set. Implementing 035 first is simpler: PM keeps QA duties but gains DM handoff. Then 043 splits QA out. Sequential is safer. Recommend: implement 035 first, then 043.

## Recommendation

**Feasible with caveats.** The feature is well-scoped and the acceptance criteria are clear. The main caveats are:

1. **Schema migration**: Adding `Pending Ship` is a schema-level change (Schema 1 -> 2). This is the first schema migration in SquidSquad's history. The migration itself is simple (no data rewrite needed — just documentation of the new status), but the upgrade machinery must handle it correctly.

2. **Cross-template coordination**: PM, dev, and DM templates all need to be updated simultaneously. A partial rollout (PM changes without DM) would break the feature lifecycle.

3. **Version bump logic**: The PM -> DM handoff for shipping means the version bump trigger point shifts. This must be carefully tested.

4. **Design decisions needed**: The 7 open questions above should be resolved in Phase 2 before implementation begins. Q1 (DM tracker structure) and Q2 (dev doc updates) are the most architecturally significant.

The feature is a natural evolution of SquidSquad's role specialization and will meaningfully reduce PM context pressure. Recommend proceeding to Phase 2 (Discussion) after resolving the open questions with the human.
