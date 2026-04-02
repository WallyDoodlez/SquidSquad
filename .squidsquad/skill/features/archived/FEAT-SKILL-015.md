## FEAT-SKILL-015 — Auto version bump and git tag every 10 shipped items

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: When the PM/QA verifies and ships a feature or bug fix, it should track a running count of shipped items since the last version bump. Every 10 shipped items, the PM automatically bumps the minor version number (e.g. `0.5.0` → `0.6.0`), updates `config.md`, `SKILL.md` frontmatter, and `CHANGELOG.md`, creates a git tag (`v0.6.0`), and pushes the tag. This gives the project a natural release cadence tied to actual output rather than arbitrary dates.

  **Mechanics:**
  1. `config.md` gets a new counter: `Shipped Since Last Bump: N`
  2. PM increments the counter each time it marks an item as `Shipped`
  3. When the counter reaches 10: bump minor version, reset counter to 0, update version in `config.md` + `SKILL.md` frontmatter, add a new section to `CHANGELOG.md`, create and push a git tag
  4. The bump is logged in the PM iteration log

- **Acceptance Criteria**:
  - [ ] `config.md` template includes `Shipped Since Last Bump: 0` counter
  - [ ] PM increments the counter when marking any item as `Shipped`
  - [ ] At count 10: PM bumps minor version (e.g. `0.5.x` → `0.6.0`)
  - [ ] PM updates version in `config.md` and `SKILL.md` frontmatter
  - [ ] PM adds a new version section to `CHANGELOG.md` summarizing the 10 shipped items
  - [ ] PM creates and pushes a git tag (e.g. `v0.6.0`)
  - [ ] Counter resets to 0 after bump
  - [ ] PM/QA CLAUDE.md template updated with the version bump logic
  - [ ] SKILL.md documents the auto-versioning behavior

### Discussion

> [2026-03-28 04:00] **pm/qa**: Filed from human request. Auto-version based on shipped output — every 10 items triggers a minor version bump and git tag. Status: Pending — awaiting human approval.
> [2026-03-28 05:00] **pm/qa**: Human wants this feature to be the first test case for FEAT-SKILL-016 (deep feature lifecycle). Do NOT approve yet — wait for 016 to ship, then run 015 through the full research → discussion → planning → execution → QA flow as validation.
> [2026-03-28 06:45] **pm/qa**: Human approved. Status → Planning. Beginning intake process. Running Phase 1 (Research).
> [2026-03-28 08:10] **pm/qa**: Phase 1 (Research) complete — RESEARCH.md written. Phase 2 (Discussion) complete — 7 questions resolved via interactive dialog. Phase 3 (Planning) complete — CONTEXT.md and TEST-PLAN.md written. All planning phases done. Status → Approved.
> [2026-03-28 08:35] **pm/qa**: Verified against TEST-PLAN.md — all criteria pass. Step 6c in PM template with full bump sequence, bug gate, crash recovery, config fields, SKILL.md docs, generated PM CLAUDE.md. Status → Shipped.
> [2026-03-28 08:40] **skill-lead**: Complete. Added Step 6c (Version Bump Check) to PM template and generated pm/CLAUDE.md. Added Ship Threshold + Shipped Since Last Bump to config.md and SKILL.md config template. Documented auto-versioning in SKILL.md and CHANGELOG.md. All TEST-PLAN.md criteria addressed. Status → Pending Test.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
